"""Synthetic-only Level 12 cross-study and cohort integrity checks."""
from copy import deepcopy
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import intake, reviewed_record, NCT

def target():
    return {"population": "ITT adults", "endpoint": "Endpoint A", "timeFrame": "12 weeks"}

def study(nct="NCT00000002", cohort="cohort1"):
    return {
        "nctId": nct, "registryUrl": "https://clinicaltrials.gov/study/" + nct,
        "registryRecordDate": "2026-01-01", "sourceRetrievedAt": "2026-01-05",
        "cohortKey": cohort, **target(),
    }

def assess(studies, **record_mutation):
    record = reviewed_record()
    record["measurements"] = {"target": target(), "studies": studies}
    record.update(record_mutation)
    return assess_levels_nine_to_twenty(
        intake(), trial_id=NCT, evidence={"12.independentStudyIdentity": record}
    )["12"]["replicationCandidates"]

def test_two_distinct_ncts_are_not_a_replication_claim():
    result = assess([study(), study("NCT00000003", "cohort2")])
    assert result["status"] == "SOURCE_CANDIDATE_INVENTORY_ONLY"
    assert len(result["candidateStudies"]) == 2
    assert result["replicationEstablished"] is False
    assert result["independentCohortsEstablished"] is False
    assert result["score"] is None
    assert result["fdaPrediction"] == "ABSTAIN"

def test_duplicate_cohort_across_distinct_ncts_is_flagged():
    result = assess([study(), study("NCT00000003", "COHORT1")])
    assert result["status"] == "COHORT_OVERLAP_REQUIRES_REVIEW"
    assert result["declaredCohortCollisions"] == [["NCT00000002", "NCT00000003"]]
    assert result["replicationEstablished"] is False

def test_endpoint_population_mismatch_stays_visible():
    changed = study()
    changed["population"] = "Per protocol"
    changed["endpoint"] = "Different endpoint"
    result = assess([changed])
    assert result["candidateStudies"][0]["contextDifferences"] == ["population", "endpoint"]
    assert result["candidateStudies"][0]["structuralContextMatch"] is False

def test_bad_source_identity_or_chronology_rejects_entire_screen():
    bad = [
        {**study(), "nctId": NCT},
        {**study(), "registryUrl": "https://clinicaltrials.gov/study/NCT00000099"},
        {**study(), "registryUrl": "https://external.example/study/NCT00000002"},
        {**study(), "sourceRetrievedAt": "2026-02-02"},
        {**study(), "nctId": "NCT0000000X"},
        {**study(), "registryRecordDate": "2026-02-03"},
        {**study(), "cohortKey": ""},
    ]
    for case in bad:
        result = assess([case])
        assert result["status"] == "REJECTED_MEASUREMENTS"
        assert "candidateStudies" not in result
    assert assess([study(), study()])["status"] == "REJECTED_MEASUREMENTS"

def test_rejected_target_record_never_yields_cross_study_screen():
    for mutation in (
        {"nctId": "NCT00000004"},
        {"sourceRetrievedAt": "2026-03-01"},
        {"sourceVerifiedBy": ""},
    ):
        result = assess([study()], **mutation)
        assert result["status"] == "NOT_ASSESSED"
        assert "candidateStudies" not in result

def test_empty_candidates_is_not_evidence_of_absence():
    result = assess([])
    assert result["status"] == "NO_REVIEWED_CANDIDATE_STUDIES"
    assert result["replicationEstablished"] is False

def test_unreviewed_trial_does_not_reclassify_replication():
    result = assess_levels_nine_to_twenty(
        intake(phase="PHASE1", status="RECRUITING"), trial_id=NCT)["12"]["replicationCandidates"]
    assert result["status"] == "NOT_ASSESSED"
    assert result["fdaPrediction"] == "ABSTAIN"
