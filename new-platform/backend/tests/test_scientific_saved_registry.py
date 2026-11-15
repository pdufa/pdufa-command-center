"""Saved-record timestamp and inventory integration; no fabricated approvals."""
from datetime import date, datetime, timezone
from copy import deepcopy
import pytest
from app.candidate_assessments import score_candidate, compact, fingerprint
from app.phase_first_intake import registry_retrieved_day

NCT = "NCT04576949"

def registry():
    # Synthetic structural fixture using a real NCT; not a clinical finding.
    return {"nct_id": NCT, "phases": ["PHASE3"], "status": "COMPLETED",
            "last_update_posted": {"date": "2026-01-15"},
            "study_design": {"designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "QUADRUPLE"}}},
            "enrollment": {"count": 810, "type": "ACTUAL"},
            "conditions": ["Smoking Cessation"], "eligibility": {"minimumAge": "18 Years"},
            "primary_outcomes": [{"measure": "Continuous abstinence", "timeFrame": "Weeks 3–6"}]}


def assess(value=None, checked="2026-11-14T09:25:31.123456+00:00", cutoff=date(2026, 11, 14)):
    return score_candidate({"id": "TRIAL|"+NCT, "nctId": NCT}, value or registry(),
                           registry_checked=checked, today=cutoff)


@pytest.mark.parametrize("checked", ["2026-11-14T09:25:31+00:00", "2026-11-14T09:25:31.123456Z", "2026-11-14"])
def test_database_retrieval_dates_enable_intake_but_never_validation(checked):
    result = assess(checked=checked)
    assert result["levelOneIntake"]["executionStatus"] == "INTAKE_ONLY"
    for level in result["levelsTwoToSix"].values():
        assert level["score"] is None
        assert level["scientificValidation"] == "NOT_VERIFIED"
        assert level["fdaPrediction"] == "ABSTAIN"
        assert "registryEvidenceInventory" in level
    item = result["levelsTwoToSix"]["2"]["registryEvidenceInventory"]["randomizationAndControl"]
    assert item["state"] == "AVAILABLE_NOT_REVIEWED"
    assert item["provenance"]["retrievedAt"] == checked
    assert item["provenance"]["reviewerId"] is None
    assert result["levelsTwoToSix"]["2"]["reviewedCount"] == 0


@pytest.mark.parametrize("checked", ["2026-11-14forged", "2026-11-14T99:00:00Z", "2026-11-14T01:00:00", "2026-11-14T01:00:00Zjunk", None, datetime(2026,11,14,tzinfo=timezone.utc)])
def test_invalid_retrieval_is_not_valid_by_slicing(checked):
    result = assess(checked=checked)
    assert result["levelOneIntake"]["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"
    assert all("registryEvidenceInventory" not in x for x in result["levelsTwoToSix"].values())


def test_utc_day_protects_historical_cutoff():
    assert registry_retrieved_day("2026-11-14T23:30:00-02:00") == date(2026,11,15)
    assert assess(checked="2026-11-14T23:30:00-02:00")["levelOneIntake"]["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"
    assert assess(cutoff=date(2026,1,1))["levelOneIntake"]["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"


def test_source_change_versions_history_without_overwriting():
    before = assess(); frozen = deepcopy(before)
    amended = registry(); amended["eligibility"]["minimumAge"] = "21 Years"
    after = assess(amended)
    assert fingerprint(before) != fingerprint(after)
    assert before == frozen
    assert compact(after)["levelsTwoToSix"] == after["levelsTwoToSix"]
    assert assess()["levelsTwoToSix"] == before["levelsTwoToSix"]


def test_early_phase_dossier_and_no_invented_safety():
    value = registry(); value["phases"] = ["PHASE1"]
    result = assess(value)
    assert result["levelsTwoToSix"]["6"]["registryEvidenceInventory"]["applicationDossier"]["state"] == "NOT_YET_EXPECTED"
    assert all(x["observation"] is None for x in result["levelsTwoToSix"]["4"]["registryEvidenceInventory"].values())


@pytest.mark.parametrize("wrong", ["NCT00000001", "NCT０４５７６９４９"])
def test_wrong_trial_cannot_attach_inventory(wrong):
    value = registry(); value["nct_id"] = wrong
    with pytest.raises(ValueError, match="identity mismatch"):
        assess(value)


@pytest.mark.parametrize("module_name", ["app.phase_first_intake", "app.scientific_levels_two_to_six"])
def test_official_source_url_bindings_include_api_and_original_pdfs(module_name):
    from importlib import import_module
    match = import_module(module_name)._source_matches_trial
    assert match("https://clinicaltrials.gov/api/v2/studies/"+NCT, NCT)
    assert match("https://cdn.clinicaltrials.gov/large-docs/49/"+NCT+"/Prot_SAP_000.pdf", NCT)
    assert not match("https://cdn.clinicaltrials.gov/large-docs/01/NCT00000001/Prot_000.pdf", NCT)
    assert not match("https://cdn.clinicaltrials.gov/large-docs/00/"+NCT+"/Prot_000.pdf", NCT)
    assert not match("https://clinicaltrials.gov/api/v2/studies/NCT00000001", NCT)


@pytest.mark.parametrize("value", ["2026-11-14T23:00:00+00:99", "2026-11-14T00:00:00-01:60"])
def test_invalid_timezone_components_are_not_normalized_into_valid_receipts(value):
    assert registry_retrieved_day(value) is None
