"""Exercise live-review auth/identity boundaries without remote credentials."""
import copy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.market_evidence_review import market_evidence_review
from app.readiness_smoke import check_deployed_program, check_program, verify_payload

PID = "PDUFA-000001"
EXACT = "TRIAL|NCT01234567|ABC"
PATH = f"/api/review/program-decision-readiness/{PID}"
HEADERS = {"x-pdufa-internal-key": "unit-test-only"}


@pytest.fixture
def review_client(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", HEADERS["x-pdufa-internal-key"])
    monkeypatch.setenv("PDUFA_ALPACA_REVIEW_SMOKE", "1")
    session = MagicMock()
    session.__enter__.return_value.get.return_value = SimpleNamespace(source_key=EXACT, ticker="ABC")
    market = market_evidence_review(PID, EXACT, {"status": "OK", "return20Pct": 4, "volumeRatio20": 1.2})
    record = {"programId": PID, "id": EXACT,
              "data": {"candidate": {"id": EXACT, "programId": PID}},
              "models": {stage: {"score": 80, "coverage": 100, "status": "COMPLETE"}
                         for stage in ("GEM_JR", "GEM")}}
    with (patch("app.main.Session", return_value=session),
          patch("app.main._DB_STATE", {"available": True, "reason": "READY"}),
          patch("app.program_market_enrichment.enrich_program_market", return_value={"marketEvidenceReview": market}),
          patch("app.assessment_service.exact_detail", return_value=record)):
        # No lifespan: never bootstrap storage or source downloads in this test.
        yield TestClient(app), session


@pytest.mark.parametrize("stage", ["GEM_JR", "GEM"])
def test_authenticated_exact_program_keeps_missing_reviews_blocked(review_client, stage):
    client, session = review_client
    response = client.get(PATH, params={"stage": stage}, headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    verify_payload(payload, PID, stage, EXACT)
    assert payload["assessmentEvidence"]["status"] == "COMPLETE"
    assert payload["decisionReadiness"]["missingRequirements"] == [
        "verified catalyst", "financing and dilution risk review"]
    session.__enter__.return_value.get.assert_called_once()
    session.__enter__.return_value.commit.assert_not_called()


def test_review_rejects_missing_key_and_disabled_review(review_client, monkeypatch):
    client, session = review_client
    assert client.get(PATH).status_code == 401
    monkeypatch.delenv("PDUFA_ALPACA_REVIEW_SMOKE")
    assert client.get(PATH, headers=HEADERS).status_code == 404
    session.__enter__.return_value.get.assert_not_called()


@pytest.mark.parametrize("stage", ["PIPELINE", "bad"])
def test_review_rejects_other_stages_before_storage(review_client, stage):
    client, session = review_client
    assert client.get(PATH, params={"stage": stage}, headers=HEADERS).status_code == 422
    session.__enter__.return_value.get.assert_not_called()


@pytest.mark.parametrize("section,field,value", [
    (None, "programId", "PDUFA-000002"),
    (None, "ordersEnabled", True),
    (None, "fsFaChanges", True),
    ("marketEvidenceReview", "exactKey", "OTHER_TRIAL"),
    ("marketEvidenceReview", "assessmentScoreChange", True),
    ("marketEvidenceReview", "status", "INSUFFICIENT_EVIDENCE"),
    ("riskEvidenceReview", "catalystVerified", True),
    ("riskEvidenceReview", "financingRiskReviewed", True),
    ("riskEvidenceReview", "fsFaChange", True),
    ("assessmentEvidence", "status", "IDENTITY_MISMATCH"),
    ("decisionReadiness", "tradeCall", "BUY"),
    ("decisionReadiness", "entryPrice", 10),
    ("decisionReadiness", "missingRequirements", []),
])
def test_smoke_detects_cross_program_or_trading_boundary_regressions(review_client, section, field, value):
    client, _ = review_client
    payload = copy.deepcopy(client.get(PATH, headers=HEADERS).json())
    (payload if section is None else payload[section])[field] = value
    with pytest.raises(ValueError):
        verify_payload(payload, PID, "GEM_JR", EXACT)


def test_smoke_cannot_target_staging_or_run_without_isolated_opt_in(monkeypatch):
    with patch("app.readiness_smoke.build_opener") as opener:
        with pytest.raises(ValueError):
            check_program("https://pdufa-new-api-staging.onrender.com", "unit-test-only", PID)
        monkeypatch.delenv("PDUFA_ALPACA_REVIEW_SMOKE", raising=False)
        check_deployed_program(PID, EXACT)
        opener.assert_not_called()


def test_market_data_unavailable_reports_diagnostics_and_does_not_pass(review_client):
    client, _ = review_client
    payload = copy.deepcopy(client.get(PATH, headers=HEADERS).json())
    payload["marketEvidenceReview"]["status"] = "INSUFFICIENT_EVIDENCE"
    payload["marketDataStatus"] = "RATE_LIMITED"
    payload["marketSignalStatus"] = "INSUFFICIENT_BARS"
    payload["marketBarsAvailable"] = 0
    payload["marketDataFeed"] = "IEX"
    with pytest.raises(ValueError, match="market_data_status='RATE_LIMITED'") as exc:
        verify_payload(payload, PID, "GEM_JR", EXACT)
    assert "market_bars=0" in str(exc.value)
    assert "research readiness remains NOT_READY" in str(exc.value)
