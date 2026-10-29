"""Read-only acquisition queue coverage tests."""
from research.official_acquisition_queue_audit import build_queue_audit


def test_queue_audit_covers_six_cases():
    result = build_queue_audit()
    assert result["case_count"] == 6
    assert sum(row["requirements"] for row in result["cases"].values()) == result["requirement_count"]
    assert sum(result["priority_counts"].values()) == result["requirement_count"]
    assert sum(result["family_counts"].values()) == result["requirement_count"]


def test_queue_audit_case_breakdown_consistent():
    result = build_queue_audit()
    for case in result["cases"].values():
        assert case["known_leads"] + case["derived_leads"] + case["unresolved_locators"] == case["requirements"]


def test_queue_audit_is_fail_closed():
    result = build_queue_audit()
    assert result["source_documents_acquired"] == 0
    assert result["independently_verified_decisions"] == 0
    assert result["prediction_readiness"] == "NOT_READY"
    assert result["prediction_action"] == "ABSTAIN"
