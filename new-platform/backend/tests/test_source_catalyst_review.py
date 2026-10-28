"""Real source dates must stay exact-program facts, separate from numeric grades."""
from copy import deepcopy
from datetime import date, datetime
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.candidate_assessments import score_candidate
from app.main import app
from app.market_evidence_review import market_evidence_review
from app.readiness_smoke import REVIEW_URL, check_all, check_source_catalog, verify_payload, verify_source_link
from app.risk_evidence_review import risk_evidence_from_assessment
from app.source_catalyst_review import catalog, primary_catalyst_review, apply_primary_catalyst

TODAY = date(2026, 10, 23)
KEY = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
PID = "PDUFA-000038"


def source_review(key=KEY, **kwargs):
    item = catalog()["programs"][key]
    return primary_catalyst_review(PID, key, item["ticker"], item["eventDate"], today=TODAY, **kwargs)


def test_catalog_covers_every_saved_active_gem_program_with_primary_source_metadata():
    membership = json.loads((Path(__file__).resolve().parents[3] / "data/gem_stage_membership.json").read_text())
    active = {k for group in membership["stages"].values() for k, row in group["entries"].items() if row["status"] == "ACTIVE"}
    # The dated primary-source catalog retains older reviewed programs even
    # after stage membership becomes inactive. Do not delete their provenance
    # or reactivate them just to satisfy a stale fixed-size test.
    assert active.issubset(set(catalog()["programs"]))
    records = [source_review(k) for k in active]
    assert len(records) == len(active)
    assert sum(r["status"] == "CONFIRMED" for r in records) + sum(
        r["status"] == "READOUT_ALREADY_REPORTED" for r in records
    ) == len(records)
    assert all(r["source"].startswith("https://") and r["checkedAt"] == TODAY.isoformat() for r in records)
    assert all(r["ordersEnabled"] is False and r["assessmentScoreChange"] is False for r in records)


def test_same_issuer_applications_do_not_borrow_each_others_dates():
    first = source_review("APPLICATION|BBIO|BBP418_LGMD2IR9_20261127")
    second = source_review("APPLICATION|BBIO|ENCALERET_ADH1")
    assert first["eventDate"] == "2026-11-27"
    assert second["eventDate"] == "2027-05-08"
    assert first["source"] != second["source"]
    bad = primary_catalyst_review(PID, first["exactKey"], "BBIO", second["eventDate"], today=TODAY)
    assert bad["status"] == "CONFLICTING_DATE" and not bad["catalystVerified"]


@pytest.mark.parametrize("field,value,expected", [
    ("exactKey", "OTHER_PROGRAM", "IDENTITY_MISMATCH"),
    ("ticker", "OTHER", "IDENTITY_MISMATCH"),
    ("reviewedOn", "2026-10-15", "STALE"),
    ("reviewedOn", "2026-10-24", "INVALID_SOURCE_REVIEW"),
    ("sourcePublishedOn", "2026-10-24", "INVALID_SOURCE_REVIEW"),
    ("sourceUrl", "http://investors.cogentbio.com/review", "INVALID_SOURCE_REVIEW"),
    ("sourceUrl", "https://unverified.example/review", "INVALID_SOURCE_REVIEW"),
    ("sourceUrl", "https://user:password@investors.cogentbio.com/review", "INVALID_SOURCE_REVIEW"),
    ("eventDate", "2026-10-22", "PAST_EVENT"),
    ("eventDate", "2026-11-30 estimated", "INVALID_SOURCE_REVIEW"),
    ("dateConfirmed", "true", "INVALID_SOURCE_REVIEW"),
    ("sourceKind", "REGISTRY_COMPLETION", "INVALID_SOURCE_REVIEW"),
])
def test_future_stale_mismatched_and_unsupported_evidence_cannot_confirm_dates(field, value, expected):
    data = deepcopy(catalog())
    data["programs"][KEY][field] = value
    result = source_review(data=data)
    assert result["status"] == expected
    assert result["catalystVerified"] is False


def test_past_trial_results_and_future_registry_completion_are_not_upcoming_public_readouts():
    for key in ("TRIAL|NCT06445023", "TRIAL|NCT06455202", "TRIAL|NCT06641076"):
        result = source_review(key)
        assert result["status"] == "READOUT_ALREADY_REPORTED"
        assert result["eventDate"] is None and result["catalystVerified"] is False
        assert date.fromisoformat(result["historicalReadoutDate"]) < TODAY
    assert catalog()["programs"]["TRIAL|NCT06641076"]["trialName"] == "IZAR-1"


def test_missing_or_historical_program_cannot_satisfy_source_readiness():
    assert primary_catalyst_review(PID, "TRIAL|NCT00000000", "COGT", None, today=TODAY)["status"] == "NO_SOURCE_REVIEW"
    result = source_review(current=False)
    assert result["status"] == "PROGRAM_NOT_CURRENT" and result["catalystVerified"] is False


def test_issuer_equity_transaction_is_retained_as_an_observation_not_dilution_clearance():
    result = source_review("APPLICATION|SMMT|IVONESCIMAB_20261114")
    observation = result["issuerFinancingObservations"][0]
    assert observation["eventDate"] == "2026-10-05" and observation["amountUsd"] == 2_000_000_000
    assert observation["scope"] == "ISSUER_ONLY"
    assert "financingRiskReviewed" not in result


def test_primary_date_does_not_change_scores_or_clear_financing_and_cannot_cross_programs():
    row = {"id": KEY, "programId": PID, "ticker": "COGT", "pdufaDate": "2026-11-30"}
    record = score_candidate(row, today=TODAY)
    before = deepcopy(record)
    risk = risk_evidence_from_assessment(record, program_id=PID, exact_key=KEY, today=TODAY)
    primary = source_review()
    combined = apply_primary_catalyst(risk, primary)
    assert combined["catalystVerified"] is True and combined["financingRiskReviewed"] is False
    assert len(combined["missingEvidence"]) == 2
    assert record == before and risk["catalystVerified"] is False
    primary["programId"] = "PDUFA-000039"
    assert apply_primary_catalyst(risk, primary) == risk


@pytest.mark.parametrize("stage", ["GEM_JR", "GEM"])
@pytest.mark.parametrize("market_available", [True, False])
def test_http_source_date_reaches_readiness_while_incomplete_assessments_stay_blocked(stage, market_available):
    row = {"id": KEY, "programId": PID, "ticker": "COGT", "pdufaDate": "2026-11-30"}
    record = score_candidate(row, today=TODAY)
    original = deepcopy(record)
    market = market_evidence_review(PID, KEY, {"status": "OK", "return20Pct": 4, "volumeRatio20": 1.2}
                                    if market_available else {"status": "INSUFFICIENT_BARS"})
    session = MagicMock()
    session.__enter__.return_value.get.return_value = SimpleNamespace(source_key=KEY, ticker="COGT")
    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only", "PDUFA_ALPACA_REVIEW_SMOKE": "1"}),
          patch("app.main.Session", return_value=session),
          patch("app.main._DB_STATE", {"available": True, "reason": "READY"}),
          patch("app.program_market_enrichment.enrich_program_market", return_value={"marketEvidenceReview": market}),
          patch("app.assessment_service.exact_detail", return_value=record),
          patch("app.source_catalyst_review.datetime") as clock):
        clock.now.return_value = datetime(2026, 10, 23)
        response = TestClient(app).get(f"/api/review/program-decision-readiness/{PID}", params={"stage": stage},
                                      headers={"x-pdufa-internal-key": "test-only"})
    assert response.status_code == 200
    result = response.json()
    verify_source_link(result, source_review(), stage)
    if market_available:
        verify_payload(result, PID, stage, KEY)
    else:
        with pytest.raises(ValueError, match="Live Alpaca market observations unavailable"):
            verify_payload(result, PID, stage, KEY)
    assert result["primaryCatalystReview"]["status"] == "CONFIRMED"
    assert result["riskEvidenceReview"]["catalystVerified"] is True
    assert result["decisionReadiness"]["status"] == "NOT_READY"
    assert result["decisionReadiness"]["missingRequirements"] == (
        ["complete verified assessment"]
        + ([] if market_available else ["exact-program market evidence"])
        + ["financing and dilution risk review"])
    for field, value in (("source", "https://other.example/review"),
                         ("programId", "PDUFA-000039"), ("eventDate", "2027-05-08"),
                         ("ordersEnabled", True), ("assessmentScoreChange", True)):
        incorrect = deepcopy(result)
        incorrect["primaryCatalystReview"][field] = value
        with pytest.raises(ValueError):
            verify_source_link(incorrect, source_review(), stage)
    if not market_available:
        incorrect = deepcopy(result)
        incorrect["decisionReadiness"]["missingRequirements"].remove("exact-program market evidence")
        with pytest.raises(ValueError, match="Decision readiness"):
            verify_source_link(incorrect, source_review(), stage)
    assert record == original
    session.__enter__.return_value.commit.assert_not_called()


def test_http_batch_reconciles_all_17_immutable_registry_identities_and_requires_auth():
    rows = []
    identities = []
    for i, (key, item) in enumerate(catalog()["programs"].items(), 1):
        rows.append({"id": key, "ticker": item["ticker"], "pdufaDate": item["eventDate"]})
        identities.append(SimpleNamespace(id=i, source_key=key, ticker=item["ticker"]))
    session = MagicMock()
    session.__enter__.return_value.scalars.return_value.all.return_value = identities
    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only", "PDUFA_ALPACA_REVIEW_SMOKE": "1"}),
          patch("app.main.Session", return_value=session),
          patch("app.main._DB_STATE", {"available": True, "reason": "READY"}),
          patch("app.source_workspace.workspace", return_value={"pipeline": rows}),
          patch("app.source_catalyst_review.datetime") as clock):
        clock.now.return_value = datetime(2026, 10, 23)
        client = TestClient(app)
        assert client.get("/api/review/catalyst-evidence").status_code == 401
        response = client.get("/api/review/catalyst-evidence", headers={"x-pdufa-internal-key": "test-only"})
    assert response.status_code == 200
    result = response.json()
    assert (result["total"], result["confirmedTargets"], result["reportedReadouts"]) == (17, 14, 3)
    assert len({r["programId"] for r in result["records"]}) == 17
    assert result["ordersEnabled"] is result["fsFaChanges"] is False
    session.__enter__.return_value.commit.assert_not_called()


def test_all_34_live_source_links_are_checked_when_alpaca_auth_fails(caplog):
    rows, identities, details = [], {}, {}
    for i, (key, item) in enumerate(catalog()["programs"].items(), 1):
        pid = f"PDUFA-{i:06d}"
        row = {"id": key, "programId": pid, "ticker": item["ticker"], "pdufaDate": item["eventDate"]}
        rows.append(row)
        identities[i] = SimpleNamespace(id=i, source_key=key, ticker=item["ticker"])
        details[key] = score_candidate(row, today=TODAY)
    before = deepcopy(details)
    session = MagicMock()
    session.__enter__.return_value.get.side_effect = lambda model, number: identities[number]
    session.__enter__.return_value.scalars.return_value.all.return_value = list(identities.values())

    def unavailable_market(pid, key, ticker, range_label):
        return {"status": "ALPACA_AUTH_FAILED", "feed": "IEX", "barsAvailable": 0,
                "marketEvidenceReview": market_evidence_review(pid, key, {"status": "INSUFFICIENT_BARS"})}

    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only", "PDUFA_ALPACA_REVIEW_SMOKE": "1"}),
          patch("app.main.Session", return_value=session),
          patch("app.main._DB_STATE", {"available": True, "reason": "READY"}),
          patch("app.source_workspace.workspace", return_value={"pipeline": rows}),
          patch("app.assessment_service.exact_detail", side_effect=lambda key: details[key]),
          patch("app.program_market_enrichment.enrich_program_market", side_effect=unavailable_market),
          patch("app.source_catalyst_review.datetime") as clock,
          patch("app.readiness_smoke.build_opener") as opener):
        clock.now.return_value = datetime(2026, 10, 23)
        client = TestClient(app)
        visited = []

        def http_response(request, timeout):
            url = urlsplit(request.full_url)
            visited.append(url.path + "?" + url.query)
            response = client.get(url.path + "?" + url.query, headers=dict(request.header_items()))
            assert response.status_code == 200
            return StringIO(response.text)

        opener.return_value.open.side_effect = http_response
        check_source_catalog(REVIEW_URL, "test-only")
        links = [path for path in visited if "/program-decision-readiness/" in path]
        assert len(links) == len(set(links)) == 34
        assert "program_stages=34" in caplog.text
        assert "status=PASS decision=NOT_READY market=INSUFFICIENT_EVIDENCE" in caplog.text
        # Completing all source links must never turn the aggregate check green
        # while the real market check has no observations.
        with pytest.raises(ValueError, match="market_data_status='ALPACA_AUTH_FAILED'"):
            check_all(REVIEW_URL, "test-only", "PDUFA-000001")
    assert "status=PASS checks=2" not in caplog.text
    assert "test-only" not in caplog.text
    assert details == before
    session.__enter__.return_value.commit.assert_not_called()
