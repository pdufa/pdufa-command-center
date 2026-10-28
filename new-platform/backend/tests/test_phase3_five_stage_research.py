from app.phase3_five_stage_research import (
    clinical_evidence_audit, historical_cohort_audit, efficacy_safety_audit,
    regulatory_precedent_audit, validation_readiness,
)

SOURCE = {"source_url": "https://example.org/primary",
          "published_at": "2025-01-01", "review_status": "VERIFIED"}

def test_clinical_missing_does_not_pass():
    r = clinical_evidence_audit("NCT123|drug", {"primary_endpoint": SOURCE}, "2026-10-27")
    assert r["verified"] == 1 and r["required"] == 7
    assert r["clinicalPass"] is None

def test_cohort_excludes_future_and_incomplete_denominator():
    base = {**SOURCE, "application_id": "NDA1", "review_cycle": 1,
            "features_as_of": "2025-01-01", "decision_date": "2025-08-01",
            "outcome": "APPROVED", "ascertainment_source": "COMPLETE_APPLICATION_COHORT",
            "cohort_complete_verified": True}
    r = historical_cohort_audit([base, {**base, "application_id": "NDA2",
                                       "cohort_complete_verified": False}], "2026-10-27")
    assert r["eligible"] == 1 and r["excluded"] == 1

def test_safety_rejects_impossible_counts():
    r = efficacy_safety_audit("NCT123", [
        {**SOURCE, "exact_key": "NCT123", "denominator": 100,
         "events": 120, "endpoint": "AE", "arm": "active"}], "2026-10-27")
    assert not r["validatedObservations"] and r["issues"][0]["issue"] == "INVALID_ARM_COUNTS"

def test_precedent_excludes_future_decision():
    target = {"exactKey": "NCT123", "indication": "GIST"}
    rows = [{**SOURCE, "application_id": "NDA2", "indication": "GIST",
             "outcome": "APPROVED", "decision_date": "2027-01-01"}]
    r = regulatory_precedent_audit(target, rows, "2026-10-27")
    assert r["knownPrecedents"] == 0 and r["regulatoryProbability"] is None

def test_no_validation_means_no_confidence():
    r = validation_readiness({"eligible": 0}, [])
    assert r["status"] == "INSUFFICIENT_VALIDATION"
    assert r["predictionConfidencePercent"] is None
