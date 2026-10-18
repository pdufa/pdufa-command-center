"""Trial screening facts must not invent readouts or transfer issuer financings."""
from copy import deepcopy
from datetime import date

from app.trial_qualification import attach_trial_filter_facts

TODAY = date(2026, 10, 18)
EVENT = "AAA|DRUG_A"
KEY = "APPLICATION|" + EVENT


def sources():
    return {
        "TRIAL|NCT00000001": {"ticker": "AAA", "nct_id": "NCT00000001", "registeredPhase": "Phase 3",
                                "stage": "Phase 3 Results", "status": "COMPLETED", "results_posted": "2026-01-02",
                                "source_url": "https://clinicaltrials.gov/study/NCT00000001", "checked_at": "2026-10-18"},
        "TRIAL|NCT00000002": {"ticker": "AAA", "nct_id": "NCT00000002", "registeredPhase": "Phase 2/3",
                                "stage": "Phase 3 Results", "status": "COMPLETED", "results_posted": "2026-01-02",
                                "source_url": "https://clinicaltrials.gov/study/NCT00000002", "checked_at": "2026-10-18"},
        KEY: {"event_key": EVENT, "ticker": "AAA", "nct_id": "NCT00000001", "registeredPhase": "",
              "stage": "PDUFA Decision", "phase3_date": "2026-01-02", "phase3_status": "PRIMARY_MET_VERIFIED",
              "trial_evidence_url": "https://example.org/issuer-results", "checked_at": "2026-10-18",
              "stageTags": ["NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision"]},
    }


def finance():
    return {EVENT: {"event_key": EVENT, "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                    "first_financing_date": "2026-02-01", "second_financing_date": "2026-04-01",
                    "first_financing_source": "https://www.sec.gov/Archives/edgar/data/123/first.htm",
                    "second_financing_source": "https://www.sec.gov/Archives/edgar/data/123/second.htm",
                    "second_financing_status": "CLOSED", "second_financing_closed": "YES", "verified_as_of": "2026-10-04"}}


def facts(originals=None, funding=None, ledger=None):
    original = originals if originals is not None else sources()
    rows = [{"id": key, "ticker": item.get("ticker", "")} for key, item in original.items()]
    before = deepcopy(original)
    attach_trial_filter_facts(rows, original, funding if funding is not None else finance(), {}, {}, ledger or {}, TODAY)
    assert original == before
    return {row["id"]: row["trialFilters"] for row in rows}


def test_registered_phase_survives_advancement_and_combined_phase_stays_separate():
    values = facts()
    assert values[KEY]["registeredPhase"] == "Phase 3"
    assert values[KEY]["milestones"] == ["FDA Acceptance", "NDA/BLA Submission", "PDUFA Decision"]
    assert values["TRIAL|NCT00000002"]["registeredPhase"] == "Phase 2/3"
    assert values["TRIAL|NCT00000002"]["resultsReleased"] is False


def test_registry_posting_is_release_evidence_but_never_proof_of_success():
    values = facts()
    assert values["TRIAL|NCT00000001"]["resultsReleased"] is True
    assert values["TRIAL|NCT00000001"]["primaryOutcome"] == "UNKNOWN"
    assert values[KEY]["primaryOutcome"] == "SUCCESS"


def test_financings_remain_on_exact_application_and_old_review_stays_visible():
    values = facts()
    assert values[KEY]["secondFinancingClosed"] is True
    assert "STALE" in values[KEY]["evidence"]
    for trial in ("TRIAL|NCT00000001", "TRIAL|NCT00000002"):
        assert values[trial]["firstFinancingClosed"] is False
        assert values[trial]["secondFinancingClosed"] is False
        assert values[trial]["independentFinancings"] == "UNKNOWN"


def test_announced_pending_same_document_pre_readout_or_future_closes_do_not_pass():
    for change in (
        {"second_financing_status": "ANNOUNCED"}, {"second_financing_closed": "REVIEW"},
        {"second_financing_audit_status": "SECOND_CLOSE_PENDING"},
        {"second_financing_source": finance()[EVENT]["first_financing_source"]},
        {"first_financing_date": "2025-12-01"}, {"second_financing_date": "2026-12-01"},
        {"verified_as_of": "2026-12-01"},
        {"second_financing_source": "https://www.sec.gov/Archives/edgar/data/999/second.htm"},
        {"second_financing_source": "https://www.sec.gov.evil.example/Archives/edgar/data/123/second.htm"},
    ):
        funding = finance()
        funding[EVENT].update(change)
        assert facts(funding=funding)[KEY]["secondFinancingClosed"] is False, change


def test_missing_negative_conflicting_or_future_readout_never_means_success():
    for change in (
        {"trial_evidence_url": ""}, {"phase3_date": "2026-12-01"},
        {"phase3_status": "RESULTS_VERIFIED"}, {"phase3_status": "PRIMARY_FAILED_VERIFIED"},
        {"conflict_flag": "YES"},
    ):
        original = sources()
        original[KEY].update(change)
        assert facts(originals=original)[KEY]["primaryOutcome"] != "SUCCESS", change


def test_generic_unknown_or_review_risk_flag_does_not_erase_a_verified_endpoint():
    for value in ("REVIEW", "UNKNOWN", ""):
        original = sources()
        original[KEY]["conflict_flag"] = value
        assert facts(originals=original)[KEY]["primaryOutcome"] == "SUCCESS"


def test_phase_mapping_never_borrows_another_issuer_or_ambiguous_registry_phase():
    original = sources()
    original[KEY]["ticker"] = "BBB"
    assert facts(originals=original)[KEY]["registeredPhase"] == "Unknown"
    assert facts(originals=original)[KEY]["secondFinancingClosed"] is False


def test_unknown_risk_is_not_cleared_and_stage_membership_uses_exact_id():
    ledger = {"stages": {"GEM": {"entries": {KEY: {"pipeline_id": KEY, "status": "ACTIVE"}}}}}
    values = facts(ledger=ledger)
    assert values[KEY]["safety"] == values[KEY]["dilution"] == "UNKNOWN"
    assert values[KEY]["runwayMonths"] is None
    assert values[KEY]["lists"] == ["GEM", "PIPELINE"]
    assert values["TRIAL|NCT00000001"]["lists"] == ["PIPELINE"]
