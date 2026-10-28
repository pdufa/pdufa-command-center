"""Real FDA-source audit-index regressions; no model-eligible FDA outcomes."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import pytest

from app.hop_fda_candidate_source_audit_index import (
    audit_fda_action_candidate_replay_summary,
    load_fda_action_candidate_replay_summary,
    _unique_json,
)

BASE = Path(__file__).resolve().parents[1]/"app"/"research_sources"
ASOF = date(2026, 10, 28)


def source():
    return json.loads((BASE/"hop_fda_action_candidate_2024_2025_audit_index.json").read_text())


def bench():
    return json.loads((BASE/"hop_fda_pdufa_filing_benchmarks.json").read_text())


def audit(index=None, b=None):
    return audit_fda_action_candidate_replay_summary(
        source() if index is None else index,
        bench() if b is None else b,
        as_of=ASOF)


def test_real_original_source_replay_412_nontraining_action_candidates():
    r = load_fda_action_candidate_replay_summary(as_of=ASOF)
    assert r["researchCandidateRows"] == 412
    assert r["status"] == "SOURCE_SELECTED_FDA_ACTION_CANDIDATES_RESEARCH_ONLY"
    assert r["sourceRecordsInspected"] == {
        "drugsfdaApprovedRegistry": 29416,
        "selectivelyPublishedLetterRecords": 458,
    }
    assert r["sourceArchivesCapturedAndFingerprintPinned"] is True
    assert r["queueSha256"] == "b3642cb6a5bdc563b9274a157505bdeec758f2faf0c69cee624ed829dc39c187"
    assert r["replayArtifactUrl"].endswith("/12831901791")
    assert r["completeFilingCohortVerified"] is False
    assert r["exactReviewCycleIndependentVerification"] is False
    assert r["historicalIndependentBacktests"] == 0
    assert r["independentlyMeasuredAccuracy"] is None
    assert r["fdaApprovalProbability"] is None
    assert r["trainingAuthorized"] is False
    assert r["tradeAuthorized"] is False
    years = {x["fiscalActionYear"]: x for x in r["sourceFiscalActionSummaries"]}
    assert set(years) == {2024, 2025}
    assert years[2024]["originalApplicationsFiledInFiscalYearReferenceOnly"] == 129
    assert years[2025]["originalApplicationsFiledInFiscalYearReferenceOnly"] == 157
    assert years[2024]["originalApprovalActionCandidatesFromApprovedRegistry"] == 137
    assert years[2025]["originalApprovalActionCandidatesFromApprovedRegistry"] == 155
    assert years[2024]["nonbinaryTentativeApprovalCandidates"] == 5
    assert years[2025]["nonbinaryTentativeApprovalCandidates"] == 5
    assert years[2024]["selectedPublishedCrlParentOnly"] == 45
    assert years[2025]["selectedPublishedCrlParentOnly"] == 52
    assert years[2024]["selectedPublishedCrlExplicitOriginal"] == 2
    assert years[2025]["selectedPublishedCrlMultipleMissing"] == 1
    assert years[2024]["overlappingParentApplicationsSameFiscalActionYear"] == 1
    assert years[2025]["overlappingParentApplicationsSameFiscalActionYear"] == 4
    for year in years.values():
        assert year["filingDenominatorCoverage"] is None
        assert year["approvalRate"] is None
        assert year["independentModelEligibleCycles"] == 0


def test_original_candidate_review_did_not_automatically_certify_fda_outcomes():
    from app.hop_fda_public_disclosure_clock import load_historical_fda_public_outcome_packet
    r = load_historical_fda_public_outcome_packet(as_of=ASOF)
    sample = r["historicalFdaSourceCandidateResearch"]
    assert sample["researchCandidateRows"] == 412
    assert r["actionLetterResearch"]["sourceLettersInspected"] == 2
    assert r["originalPdfCaptureResearch"]["capturedPdfRecords"] == 2
    assert r["independentModelEligibleCycles"] == 0
    assert r["independentHistoricalBacktests"] == 0
    assert r["approvalProbability"] is None
    assert r["trainingAuthorized"] is False
    assert r["tradeAuthorized"] is False


def test_capture_date_cutoff_prevents_research_2026_hindsight():
    for cutoff in [date(2020, 5, 15), date(2024, 12, 31),
                   date(2025, 12, 31), date(2026, 10, 27)]:
        result = load_fda_action_candidate_replay_summary(as_of=cutoff)
        assert result["status"] == "ACTION_SOURCE_REPLAY_NOT_YET_OBSERVED_AS_OF"
        assert result["researchCandidateRows"] == 0
        assert result["sourceFiscalActionSummaries"] == []
        assert result["approvalProbability"] is None
        assert result["trainingAuthorized"] is False


@pytest.mark.parametrize("change", [
    lambda x: x.update(status="VERIFIED_COMPLETE_COHORT"),
    lambda x: x.update(verified_original_filing_denominator=True),
    lambda x: x.update(all_original_filing_application_ids_known=True),
    lambda x: x.update(every_review_cycle_decision_verified=True),
    lambda x: x.update(every_predecision_feature_snapshot_verified=True),
    lambda x: x.update(training_authorized=True),
    lambda x: x.update(trade_authorized=True),
    lambda x: x.update(model_eligible_cycles=412),
    lambda x: x.update(independent_real_backtests=412),
    lambda x: x.update(measured_accuracy=0.9),
    lambda x: x.update(approval_probability=0.8),
    lambda x: x.update(source_candidate_rows=410),
    lambda x: x["replay"].update(source_replay_commit="fake"),
    lambda x: x["replay"].update(run_id=0),
    lambda x: x["replay"].update(artifact_id=0),
    lambda x: x["replay"].update(queue_durable_archived=True),
    lambda x: x["replay"].update(queue_sha256="fake"),
    lambda x: x["sources"]["drugsfda"].update(records=10),
    lambda x: x["sources"]["crl"].update(sha256="fake"),
    lambda x: x["fiscal_action_years"][0].update(year=2025),
    lambda x: x["fiscal_action_years"][1].update(original_filing_year_reported_count=155),
    lambda x: x["fiscal_action_years"][0].update(original_ap_registry_action_candidates=123),
    lambda x: x["fiscal_action_years"][0].update(distinct_apps_original_ap=900),
    lambda x: x["fiscal_action_years"][1].update(source_overlap_same_action_fy=900),
    lambda x: x.update(caution=""),
])
def test_self_attested_cohort_verification_or_edited_source_counts_blocked(change):
    data = source()
    change(data)
    with pytest.raises(ValueError):
        audit(index=data)


def test_benchmark_source_totals_must_remain_exact():
    b = bench()
    b["latest_reported_original_filings_by_fy"]["2025"] = 155
    with pytest.raises(ValueError):
        audit(b=b)


def test_source_duplicate_json_field_fails_closed():
    with pytest.raises(ValueError, match="Duplicate"):
        json.loads('{"status":"foo","status":"verified"}',
                   object_pairs_hook=_unique_json)


def test_research_summary_requires_exact_date_type():
    with pytest.raises(ValueError):
        audit_fda_action_candidate_replay_summary(source(), bench(), as_of="2026-10-28")
