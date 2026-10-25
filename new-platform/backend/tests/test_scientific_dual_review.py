import pytest

from app.scientific_dual_review import audit_digest, dual_review_preflight


def record(subject):
    return {
        "nctId": "NCT02142738", "questionId": "safety_endpoint_taxonomy",
        "sourceSha256": "a" * 64, "decision": "requires_review",
        "googleSubject": subject, "identityVerified": True,
        "roleAuthorized": True, "credentialsVerified": True,
        "sourceIndependentlyVerified": True, "auditPersisted": True,
        "source_content_inspected": True, "clinical_method_reconciled": True,
        "conflicts_disclosed": True, "qualifications_checked": True,
    }


def test_distinct_reviewers_never_promote_scores():
    result = dual_review_preflight(record("google-a"), record("google-b"))
    assert result["preflightPassed"] is True
    assert result["mayAutoPromoteReadiness"] is False
    assert result["scientificScore"] is None
    assert result["fdaApprovalProbability"] is None


def test_same_google_identity_cannot_self_approve():
    with pytest.raises(ValueError, match="Distinct"):
        dual_review_preflight(record("google-a"), record("google-a"))


@pytest.mark.parametrize("field", [
    "identityVerified", "roleAuthorized", "credentialsVerified",
    "sourceIndependentlyVerified", "auditPersisted",
    "source_content_inspected", "clinical_method_reconciled",
    "conflicts_disclosed", "qualifications_checked",
])
def test_missing_attestation_blocks_review(field):
    second = record("google-b")
    second[field] = False
    with pytest.raises(ValueError):
        dual_review_preflight(record("google-a"), second)


@pytest.mark.parametrize("field", ["nctId", "questionId", "sourceSha256", "decision"])
def test_mismatched_review_scope_blocks_review(field):
    second = record("google-b")
    second[field] = "different"
    with pytest.raises(ValueError):
        dual_review_preflight(record("google-a"), second)


def test_audit_hash_deterministic_and_sensitive():
    assert audit_digest({"a": 1, "b": 2}) == audit_digest({"b": 2, "a": 1})
    assert audit_digest({"a": 1}) != audit_digest({"a": 2})
