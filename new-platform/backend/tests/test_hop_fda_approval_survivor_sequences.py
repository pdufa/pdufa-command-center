"""FDA FY2023 approved-only appendix histories must never become unbiased labels."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from app.hop_fda_approval_survivor_sequences import (
    audit_approved_survivor_sequences,
    load_approved_survivor_sequences,
)

PATH = (Path(__file__).resolve().parents[1] / "app" /
        "research_sources" / "hop_fda_approval_survivor_sequences.json")
ASOF = date(2026, 10, 28)


def fixture():
    return json.loads(PATH.read_text(encoding="utf-8"))


def audit(data=None, as_of=ASOF):
    return audit_approved_survivor_sequences(fixture() if data is None else data, as_of=as_of)


def test_real_approved_survivor_report_trajectories_not_approval_rate():
    actual = load_approved_survivor_sequences(as_of=ASOF)
    assert actual["status"] == "FDA_APPROVED_SURVIVOR_SEQUENCES_RESEARCH_ONLY"
    assert actual["sourceReportedCoverDate"] == "2024-04-18"
    assert actual["reportedSequenceCases"] == 4
    assert actual["observedReviewCycleRows"] == 11
    assert actual["priorCRLActionsInEventuallyApprovedCases"] == 7
    assert actual["finalApprovalsInEventuallyApprovedCases"] == 4
    assert actual["approvedSurvivorSampling"] is True
    assert actual["completeNdaBlaFilingDenominatorKnown"] is False
    assert actual["historicalNonapprovalDenominatorKnown"] is False
    assert actual["independentlyVerifiedActionDates"] == 0
    assert actual["verifiedExactApplicationReviewCycles"] == 0
    assert actual["modelEligibleHistoricalCycles"] == 0
    assert actual["independentlyBacktestedCases"] == 0
    assert actual["trainingAuthorized"] is False
    assert actual["approvalProbability"] is None
    assert len(actual["cases"]) == 4
    by_product = {x["product"]: x for x in actual["cases"]}
    assert set(by_product) == {"NGENLA", "LANTIDRA", "RYKINDO", "YCANTH"}
    assert [c["actionCode"] for c in by_product["NGENLA"]["reportedFDAReviewCycles"]] == ["CR", "AP"]
    assert [c["actionCode"] for c in by_product["LANTIDRA"]["reportedFDAReviewCycles"]] == ["CR", "AP"]
    assert [c["actionCode"] for c in by_product["RYKINDO"]["reportedFDAReviewCycles"]] == ["CR", "CR", "AP"]
    assert [c["actionCode"] for c in by_product["YCANTH"]["reportedFDAReviewCycles"]] == ["CR", "CR", "CR", "AP"]
    assert by_product["NGENLA"]["sourcePdfPageZeroIndexed"] == 82
    assert by_product["YCANTH"]["sourcePdfPageZeroIndexed"] == 83
    for record in actual["cases"]:
        assert record["sourceCoverageClass"] == "APPROVED_IN_FY2023_ONLY_SURVIVOR_BIASED"
        assert record["eligibleForTraining"] is False
        assert record["applicationNumberVerified"] is False
        assert record["eachActionDateVerified"] is False
        assert record["cycleMatchedToExactNdaBlaIdentity"] is False
        assert record["firstPublicSourcePublicationDateVerified"] is False
        assert record["eventuallyApprovedInFY2023"] is True


def test_retrospective_snapshot_cannot_see_2026_manual_research():
    for cutoff in [date(2019, 1, 1), date(2023, 12, 31),
                   date(2024, 4, 18), date(2026, 10, 27)]:
        r = audit(as_of=cutoff)
        assert r["status"] == "RESEARCH_SOURCE_NOT_AVAILABLE_AT_AS_OF"
        assert r["reportedSequenceCases"] == 0
        assert r["observedReviewCycleRows"] == 0
        assert r["trainingAuthorized"] is False
        assert r["modelEligibleHistoricalCycles"] == 0
        assert r["approvalProbability"] is None


@pytest.mark.parametrize("mutator", [
    lambda a: a.update(denominator="ALL_FDA_FILINGS"),
    lambda a: a.update(model_eligible_cycles=11),
    lambda a: a.update(verified_application_ids=4),
    lambda a: a.update(adjudicated_fda_action_dates=11),
    lambda a: a.update(independent_real_backtests=1),
    lambda a: a.update(approval_probability=0.64),
    lambda a: a.update(source_first_publication_verified="2024-04-18"),
    lambda a: a.update(source_report_url="https://govinfo.gov.evil.test/some.pdf"),
    lambda a: a["cases"].pop(),
    lambda a: a["cases"][0].update(case_id="FDA_FY2023_APPROVAL_OTHER"),
    lambda a: a["cases"][0].update(product="UNREVIEWED"),
    lambda a: a["cases"][0].update(source_pdf_zero_indexed_page=83),
    lambda a: a["cases"][0].update(source_appendix_page="A-70"),
    lambda a: a["cases"][0].update(application_id="NDA999999"),
    lambda a: a["cases"][0].update(total_approval_time_months=10),
    lambda a: a["cases"][0]["review_cycles"][0].update(action_code="AP"),
    lambda a: a["cases"][0]["review_cycles"][0].update(cycle_ordinal=2),
    lambda a: a["cases"][0]["review_cycles"][1].update(action_code="CR"),
    lambda a: a["cases"][0]["review_cycles"][1].update(review_time_months=-1),
    lambda a: a["cases"][0]["review_cycles"][1].update(review_time_months=True),
    lambda a: a["cases"][0]["review_cycles"].append(deepcopy(a["cases"][0]["review_cycles"][-1])),
    lambda a: a["cases"][0]["sponsor_intervals_months"].clear(),
    lambda a: a["cases"][1].update(product=a["cases"][0]["product"]),
    lambda a: a["cases"][1].update(case_id=a["cases"][0]["case_id"]),
])
def test_unreviewed_or_selection_biased_history_cannot_promote_model(mutator):
    data = fixture()
    mutator(data)
    with pytest.raises(ValueError):
        audit(data)
