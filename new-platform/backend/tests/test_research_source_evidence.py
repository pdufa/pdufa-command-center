from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.research_source_evidence import source_evidence, sources

TODAY = date(2026, 10, 23)
PID = "PDUFA-000001"
TRIAL = "TRIAL|NCT06445023"
APPLICATION = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"


def test_all_saved_programs_have_company_facts_and_only_exact_trials_have_registry_facts():
    data = sources()
    before = deepcopy(data)
    programs = data[1]["programs"]
    reviews = [source_evidence(PID, key, item["ticker"], today=TODAY) for key, item in programs.items()]
    assert len(reviews) == 17
    assert sum(r["clinical"]["status"] == "OBSERVED" for r in reviews) == 3
    assert sum(r["financial"]["status"] == "OBSERVED" for r in reviews) == 17
    assert all(r["financial"]["facts"] for r in reviews)
    assert all(not r["ordersEnabled"] and not r["assessmentScoreChange"]
               and not r["fsFaChanges"] and not r["financingRiskReviewed"] for r in reviews)
    assert sources() == before


def test_registry_receipt_keeps_exact_enrollment_and_does_not_infer_posted_results_or_success():
    first = source_evidence(PID, TRIAL, "CLDX", today=TODAY)
    second = source_evidence("PDUFA-000002", "TRIAL|NCT06455202", "CLDX", today=TODAY)
    assert any(f["value"] == "963 (ACTUAL)" for f in first["clinical"]["facts"])
    assert any(f["value"] == "976 (ACTUAL)" for f in second["clinical"]["facts"])
    assert any(f["label"] == "Registry results" and f["value"].startswith("Not posted") for f in first["clinical"]["facts"])
    assert not first["financingRiskReviewed"]
    assert source_evidence(PID, TRIAL, "MLTX", today=TODAY)["clinical"]["facts"] == []
    assert source_evidence(PID, APPLICATION, "COGT", today=TODAY)["clinical"]["status"] == "NO_EXACT_TRIAL_LINK"
    assert source_evidence(PID, TRIAL, "CLDX", current=False, today=TODAY)["clinical"]["facts"] == []


@pytest.mark.parametrize("change", ["wrong_id", "changed_body", "future_receipt", "wrong_host"])
def test_corrupt_or_mismatched_registry_evidence_is_withheld(change):
    data = deepcopy(sources())
    item = data[0]["records"]["NCT06445023"]
    if change == "wrong_id": item["study"]["protocolSection"]["identificationModule"]["nctId"] = "NCT06455202"
    elif change == "changed_body": item["study"]["hasResults"] = True
    elif change == "future_receipt": item["retrievedAt"] = "2026-10-25T12:00:00+00:00"
    else: item["source"] = "https://example.com/study/NCT06445023"
    result = source_evidence(PID, TRIAL, "CLDX", today=TODAY, data=data)
    assert result["clinical"]["facts"] == []


def test_cash_runway_requires_matching_periods_and_does_not_use_net_income_or_securities_as_cash():
    cogt = source_evidence(PID, APPLICATION, "COGT", today=TODAY)
    assert any(f["label"].startswith("Cash-only runway") and f["value"] == "7.03" for f in cogt["financial"]["facts"])
    data = deepcopy(sources())
    data[1]["issuers"]["COGT"]["evidence"]["operating_cash_flow"]["period_end"] = "2026-03-31"
    mismatch = source_evidence(PID, APPLICATION, "COGT", today=TODAY, data=data)
    assert not any(f["label"].startswith("Cash-only runway") for f in mismatch["financial"]["facts"])
    moon = source_evidence(PID, "TRIAL|NCT06641076", "MLTX", today=TODAY)
    assert any(f["label"] == "Cash and cash equivalents (USD)" and f["value"] == "477,905,000" for f in moon["financial"]["facts"])
    assert not any(f["status"] == "CALCULATED" for f in moon["financial"]["facts"])
    assert not moon["financingRiskReviewed"]


def test_stale_or_wrong_issuer_financials_cannot_supply_a_current_runway():
    stale = source_evidence(PID, APPLICATION, "COGT", today=date(2026, 11, 5))
    assert not any(f["status"] == "CALCULATED" for f in stale["financial"]["facts"])
    assert any(f["status"] == "STALE" for f in stale["financial"]["facts"])
    data = deepcopy(sources())
    data[1]["issuers"]["COGT"]["cik"] = "0001933414"
    assert source_evidence(PID, APPLICATION, "COGT", today=TODAY, data=data)["financial"]["facts"] == []
    data = deepcopy(sources())
    data[1]["issuerObservations"]["CLDX"]["source"] = data[1]["issuerObservations"]["MLTX"]["source"]
    assert source_evidence(PID, TRIAL, "CLDX", today=TODAY, data=data)["financial"]["facts"] == []


def test_financial_group_summary_does_not_mask_stale_or_review_only_facts():
    stale_sec = source_evidence(PID, APPLICATION, "COGT", today=date(2026, 11, 5))
    assert stale_sec["financial"]["status"] == "STALE"
    assert any(item["status"] == "STALE" for item in stale_sec["financial"]["facts"])
    assert all(item["status"] not in {"OBSERVED", "CALCULATED"} for item in stale_sec["financial"]["facts"])
    assert any(item["status"] == "REVIEW" for item in stale_sec["financial"]["facts"])

    stale_issuer = source_evidence(PID, TRIAL, "CLDX", today=date(2026, 11, 5))
    assert stale_issuer["financial"]["status"] == "STALE"
    assert all(item["status"] == "STALE" for item in stale_issuer["financial"]["facts"])

    data = deepcopy(sources())
    review_only = data[1]["issuers"]["COGT"]
    review_only["cash_usd"] = None
    review_only["operating_cash_flow_usd"] = None
    review_only["review_flags"] = ["Financial statement requires reconciliation."]
    result = source_evidence(PID, APPLICATION, "COGT", today=TODAY, data=data)
    assert result["financial"]["status"] == "REVIEW_REQUIRED"
    assert result["financial"]["facts"]
    assert all(item["status"] == "REVIEW" for item in result["financial"]["facts"])
    assert result["financingRiskReviewed"] is False
    assert result["ordersEnabled"] is False


def test_http_readiness_adds_source_facts_without_clearing_missing_reviews_or_modifying_scores():
    from app.candidate_assessments import score_candidate
    from app.main import review_program_decision_readiness
    from app.market_evidence_review import market_evidence_review
    record = score_candidate({"id": TRIAL, "programId": PID, "ticker": "CLDX"}, today=TODAY)
    before = deepcopy(record)
    session = MagicMock()
    session.__enter__.return_value.get.return_value = SimpleNamespace(source_key=TRIAL, ticker="CLDX")
    market = market_evidence_review(PID, TRIAL, {"status": "OK", "return20Pct": 1, "volumeRatio20": 1})
    with (patch.dict("os.environ", {"PDUFA_ALPACA_REVIEW_SMOKE": "1"}),
          patch("app.main.Session", return_value=session),
          patch("app.assessment_service.exact_detail", return_value=record),
          patch("app.program_market_enrichment.enrich_program_market", return_value={"marketEvidenceReview": market}),
          # This fixture is explicitly as-of October 23. Keep the HTTP-readiness
          # integration test independent of the actual wall clock; production
          # source_evidence() still applies its seven-day freshness gate.
          patch("app.research_source_evidence.source_evidence",
                side_effect=lambda pid, key, ticker, **kwargs: source_evidence(
                    pid, key, ticker, today=TODAY, **kwargs))):
        result = review_program_decision_readiness(PID)
    assert result["sourceEvidence"]["programId"] == PID
    assert result["sourceEvidence"]["clinical"]["facts"]
    assert result["decisionReadiness"]["status"] == "NOT_READY"
    assert not result["riskEvidenceReview"]["financingRiskReviewed"]
    assert record == before
    session.__enter__.return_value.commit.assert_not_called()
