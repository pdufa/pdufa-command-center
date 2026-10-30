import json
import pytest
from app.prediction_events import field_events, sse_lines


def test_incremental_leaf_order_and_abstain():
    events = list(field_events("NCT01234567", {"nct_id": "NCT01234567", "sponsor": {"name": "Example"}}))
    assert [e["type"] for e in events[:6]] == ["started", "leaf", "leaf", "leaf", "leaf", "progress"]
    assert events[-1]["type"] == "complete"
    assert [e["section"] for e in events if e["type"] == "progress"] == ["trial_identity", "trial_design", "clinical_results", "regulatory", "science"]
    assert events[1]["status"] == "AVAILABLE"
    assert events[2]["status"] == "UNAVAILABLE"
    assert events[5]["available"] == 1
    assert events[5]["total"] == 4
    assert events[-1]["decision"] == "ABSTAIN"
    assert not any(e.get("spinner") for e in events)


def test_sse_format_and_identity():
    stream = "".join(sse_lines("NCT01234567", {"nct_id": "NCT01234567"}))
    assert "event: started\n" in stream
    assert "event: complete\n" in stream
    assert len([x for x in stream.splitlines() if x.startswith("data: ")]) == 62
    with pytest.raises(ValueError):
        list(field_events("NCT01234567", {"nct_id": "NCT87654321"}))


def test_unverified_regulatory_placeholder_does_not_count_as_available():
    dossier = {
        "nct_id": "NCT01234567",
        "pdufa_date": {"status": "NOT_ATTEMPTED", "value": "2026-12-01"},
        "special_designations": {"status": "VERIFIED", "value": ["FAST_TRACK"]},
    }
    events = list(field_events("NCT01234567", dossier))
    regulatory = [e for e in events if e["type"] == "progress" and e["section"] == "regulatory"][0]
    assert regulatory["available"] == 0
    assert regulatory["total"] == 4
    assert all(e["status"] == "UNAVAILABLE" for e in events if e["type"] == "leaf" and e.get("section") == "regulatory")


def test_science_assessments_remain_unassessed_without_scientific_execution():
    events = list(field_events("NCT01234567", {"nct_id": "NCT01234567"}))
    assessments = [e for e in events if e["type"] == "assessment"]
    assert len(assessments) == 40
    assert [e["assessment_id"] for e in assessments] == [f"S{i:02d}" for i in range(1, 41)]
    assert all(e["status"] == "NOT_ASSESSED" and not e["spinner"] for e in assessments)
    science = [e for e in events if e["type"] == "progress" and e["section"] == "science"][0]
    assert (science["available"], science["total"]) == (0, 40)


def test_empty_and_unadjudicated_science_does_not_count_as_evidence():
    dossier = {
        "nct_id": "NCT01234567",
        "primary_endpoint_results": [],
        "statistical_significance": {"reported_primary_analyses": [], "interpretation": "NOT_INFERRED"},
        "clinical_effect_size": {"reported_comparative_estimates": [], "clinical_meaningfulness": "NOT_ADJUDICATED"},
        "safety_findings": {},
    }
    events = list(field_events("NCT01234567", dossier))
    clinical = [e for e in events if e["type"] == "progress" and e["section"] == "clinical_results"][0]
    assert clinical["available"] == 0


def test_readiness_inventory_reports_missing_fields_without_claiming_assessment():
    events = list(field_events("NCT01234567", {"nct_id": "NCT01234567"}))
    readiness = [e for e in events if e["type"] == "readiness"]
    assert len(readiness) == 1
    assert readiness[0]["status"] == "EVIDENCE_INCOMPLETE"
    assert readiness[0]["evidence_fields_present"] == 0
    assert readiness[0]["evidence_fields_total"] == 10
    assert len(readiness[0]["missing_fields"]) == 10
    assert readiness[0]["assessments_completed"] == 0
    assert readiness[0]["decision"] == "ABSTAIN"


def test_invalid_nct_is_rejected_before_streaming():
    with pytest.raises(ValueError, match="Invalid NCT"):
        list(field_events("NCT123", {"nct_id": "NCT123"}))


def test_complete_evidence_inventory_does_not_authorize_prediction():
    verified = {"status": "VERIFIED", "source_url": "https://example.org/source",
                "source_document_sha256": "a" * 64, "value": "documented"}
    keys = (
        "primary_endpoints", "primary_endpoint_results", "statistical_significance",
        "clinical_effect_size", "safety_findings", "serious_adverse_events",
        "study_completion_status", "fda_regulatory_pathway",
        "regulatory_submission_evidence", "pdufa_date",
    )
    dossier = {"nct_id": "NCT01234567", **{key: verified for key in keys}}
    events = list(field_events("NCT01234567", dossier))
    readiness = next(e for e in events if e["type"] == "readiness")
    assert readiness["status"] == "EVIDENCE_PRESENT_NOT_ADJUDICATED"
    assert readiness["evidence_fields_present"] == 10
    assert readiness["missing_fields"] == []
    assert readiness["assessments_completed"] == 0
    assert events[-1]["decision"] == "ABSTAIN"
