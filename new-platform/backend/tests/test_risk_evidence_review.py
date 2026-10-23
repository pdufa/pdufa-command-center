"""Source-based readiness must not borrow a company's other trial or invent facts."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.risk_evidence_review import risk_evidence_from_assessment

TODAY = date(2026, 10, 23)
PID = "PDUFA-000001"
EXACT = "APPLICATION|EXACT_PROGRAM"


def evidence_record():
    def metric(key, value, source="https://www.sec.gov/Archives/edgar/data/123/filing.htm"):
        return {"id": key, "status": "OBSERVED", "maximum": 5, "coverage": 5, "points": 5,
                "source": source, "sourceDate": "2026-10-21", "checkedAt": "2026-10-22",
                "note": "Exact-program source and measurements reviewed.", "value": value}
    timing = metric("catalystTiming", {"reviewedMeasurements": {
        "reviewGrade": 4, "measurements": {"eventType": "PDUFA", "eventDate": "2026-11-10", "dateConfirmed": True}}},
        "https://issuer.example/investors/exact-program-pdufa")
    runway = metric("cashRunway", 18)
    dilution = metric("dilutionRisk", {"reviewGrade": 4, "measurements": {"review": "Financing and dilution evidence retained"}})
    model = {"status": "COMPLETE", "score": 80, "coverage": 100,
             "categories": [{"metrics": [timing]}, {"metrics": [runway, dilution]}]}
    return {"id": EXACT, "programId": PID,
            "data": {"candidate": {"id": EXACT, "programId": PID, "ticker": "SAME", "pdufaDate": "2026-11-10"}},
            "models": {stage: deepcopy(model) for stage in ("GEM_JR", "GEM")}, "riskFlags": []}


def review(record, stage="GEM_JR", **kwargs):
    return risk_evidence_from_assessment(record, program_id=PID, exact_key=EXACT,
                                         stage=stage, today=TODAY, **kwargs)


@pytest.mark.parametrize("stage", ["GEM_JR", "GEM"])
def test_fresh_exact_program_reviews_are_reused_without_mutating_scores(stage):
    record = evidence_record()
    original = deepcopy(record)
    result = review(record, stage)
    assert result["status"] == "REVIEWED"
    assert result["catalystVerified"] is result["financingRiskReviewed"] is True
    assert result["missingEvidence"] == []
    assert result["ordersEnabled"] is result["assessmentScoreChange"] is result["fsFaChange"] is False
    assert record == original


def test_unavailable_or_wrong_program_reuses_no_company_evidence():
    result = review(None)
    assert result["identityStatus"] == "ASSESSMENT_UNAVAILABLE"
    assert len(result["missingEvidence"]) == 3
    for change in ("programId", "id"):
        record = evidence_record()
        record[change] = "OTHER_PROGRAM"
        result = review(record)
        assert result["identityStatus"] == "IDENTITY_MISMATCH"
        assert result["catalystVerified"] is result["financingRiskReviewed"] is False
        assert all(not c["source"] for c in result["checks"])


@pytest.mark.parametrize("measurements,expected", [
    ({"primaryCompletionDate": "2026-11-10"}, "UNCONFIRMED_EVENT_DATE"),
    ({"eventType": "PDUFA", "eventDate": "2026-11-10"}, "UNCONFIRMED_EVENT_DATE"),
    ({"eventType": "REGISTRY_COMPLETION", "eventDate": "2026-11-10", "dateConfirmed": True}, "UNCONFIRMED_EVENT_DATE"),
    ({"eventType": [], "eventDate": "2026-11-10", "dateConfirmed": True}, "UNCONFIRMED_EVENT_DATE"),
    ({"eventType": "PDUFA", "eventDate": "2026-11-10 (estimate)", "dateConfirmed": True}, "UNCONFIRMED_EVENT_DATE"),
    ({"eventType": "PDUFA", "eventDate": "2026-10-01", "dateConfirmed": True}, "PAST_EVENT"),
    ({"eventType": "PDUFA", "eventDate": "2026-11-11", "dateConfirmed": True}, "CONFLICTING"),
])
def test_registry_dates_unconfirmed_dates_past_dates_and_conflicts_do_not_verify_a_catalyst(measurements, expected):
    record = evidence_record()
    record["models"]["GEM_JR"]["categories"][0]["metrics"][0]["value"]["reviewedMeasurements"]["measurements"] = measurements
    result = review(record)
    assert result["catalystVerified"] is False
    assert result["financingRiskReviewed"] is True
    assert result["checks"][0]["status"] == expected


@pytest.mark.parametrize("change,expected", [
    ({"checkedAt": "2026-10-15"}, "STALE"),
    ({"checkedAt": "2026-10-24"}, "INVALID_EVIDENCE"),
    ({"sourceDate": "2026-10-24"}, "INVALID_EVIDENCE"),
    ({"source": "http://issuer.example/review"}, "INVALID_EVIDENCE"),
    ({"source": "https://issuer.example/review with spaces"}, "INVALID_EVIDENCE"),
    ({"source": "https://username:password@issuer.example/review"}, "INVALID_EVIDENCE"),
    ({"coverage": 4}, "INVALID_EVIDENCE"),
    ({"points": True}, "INVALID_EVIDENCE"),
    ({"status": "CONFLICTING"}, "CONFLICTING"),
])
def test_freshness_sources_and_partial_reviews_fail_closed(change, expected):
    record = evidence_record()
    # Keep source older than the checked date for the stale-review case.
    metric = record["models"]["GEM_JR"]["categories"][1]["metrics"][1]
    metric["sourceDate"] = "2026-10-01"
    metric.update(change)
    result = review(record)
    assert result["financingRiskReviewed"] is False
    assert result["checks"][2]["status"] == expected


def test_cash_runway_requires_sec_and_does_not_imply_dilution_review():
    record = evidence_record()
    funding = record["models"]["GEM_JR"]["categories"][1]["metrics"]
    funding[0]["source"] = "https://other.example/cash-estimate"
    assert review(record)["financingRiskReviewed"] is False
    funding[0]["source"] = "https://www.sec.gov/Archives/edgar/data/123/filing.htm"
    funding.pop()
    assert review(record)["checks"][1]["status"] == "REVIEWED"
    assert review(record)["financingRiskReviewed"] is False


def test_reviews_from_another_stage_or_duplicate_metrics_are_not_used():
    record = evidence_record()
    record["models"]["GEM_JR"]["categories"] = []
    assert not review(record)["catalystVerified"]
    assert review(record, "GEM")["catalystVerified"]
    record = evidence_record()
    metrics = record["models"]["GEM_JR"]["categories"][1]["metrics"]
    metrics.append(deepcopy(metrics[1]))
    assert not review(record)["financingRiskReviewed"]


def test_adverse_review_is_retained_as_a_review_without_regrading_or_hiding_risk():
    record = evidence_record()
    metric = record["models"]["GEM_JR"]["categories"][1]["metrics"][1]
    metric["value"]["reviewGrade"] = metric["points"] = 0
    record["riskFlags"] = ["New dilution flag"]
    result = review(record)
    assert result["financingRiskReviewed"] is True
    assert result["checks"][2]["value"]["reviewGrade"] == 0
    assert result["riskFlags"] == ["New dilution flag"]
    assert result["ordersEnabled"] is False


def test_existing_review_windows_have_inclusive_boundaries():
    record = evidence_record()
    for category in record["models"]["GEM_JR"]["categories"]:
        for metric in category["metrics"]:
            age = 120 if metric["id"] == "cashRunway" else 7
            stamp = (TODAY - timedelta(days=age)).isoformat()
            metric.update(sourceDate=stamp, checkedAt=stamp)
    assert review(record)["status"] == "REVIEWED"


@pytest.mark.parametrize("stage", ["GEM_JR", "GEM"])
@pytest.mark.parametrize("clinical_complete", [True, False])
def test_http_readiness_uses_risk_reviews_but_never_bypasses_assessments_or_enables_orders(stage, clinical_complete):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.market_evidence_review import market_evidence_review
    from app.readiness_smoke import verify_payload

    record = evidence_record()
    if not clinical_complete:
        record["models"][stage].update(status="PARTIAL", coverage=60, score=None)
    original = deepcopy(record)
    market = market_evidence_review(PID, EXACT, {"status": "OK", "return20Pct": 4, "volumeRatio20": 1.2})
    session = MagicMock()
    session.__enter__.return_value.get.return_value = SimpleNamespace(source_key=EXACT, ticker="SAME")
    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only", "PDUFA_ALPACA_REVIEW_SMOKE": "1"}),
          patch("app.main.Session", return_value=session),
          patch("app.main._DB_STATE", {"available": True, "reason": "READY"}),
          patch("app.program_market_enrichment.enrich_program_market", return_value={"marketEvidenceReview": market}),
          patch("app.assessment_service.exact_detail", return_value=record),
          patch("app.risk_evidence_review.datetime") as clock):
        clock.now.return_value = datetime(2026, 10, 23)
        response = TestClient(app).get(f"/api/review/program-decision-readiness/{PID}",
                                      params={"stage": stage}, headers={"x-pdufa-internal-key": "test-only"})
    assert response.status_code == 200
    payload = response.json()
    verify_payload(payload, PID, stage, EXACT)
    assert payload["riskEvidenceReview"]["status"] == "REVIEWED"
    assert payload["decisionReadiness"]["status"] == (
        "READY_FOR_HUMAN_RESEARCH_REVIEW" if clinical_complete else "NOT_READY")
    assert payload["decisionReadiness"]["missingRequirements"] == ([] if clinical_complete else ["complete verified assessment"])
    assert payload["decisionReadiness"]["ordersEnabled"] is False
    assert payload["decisionReadiness"]["tradeCall"] is None
    assert record == original
    session.__enter__.return_value.commit.assert_not_called()
