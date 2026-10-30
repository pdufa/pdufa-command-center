from dataclasses import replace

from research.fda_outcome_identity_gate import (
    FDAOutcomeIdentityEvidence, FDAProgramIdentity, check_outcome_identity,
)


PROGRAM = FDAProgramIdentity("TRIAL-1", "NDA-123456", "Example Drug", "Condition A")
EVIDENCE = FDAOutcomeIdentityEvidence(
    "NDA 123456", "Example Drug", "Condition A", "PASS", "a" * 64
)


def test_matching_identity_does_not_authenticate_outcome():
    assert check_outcome_identity(
        PROGRAM, EVIDENCE
    ) == "IDENTITY_MATCHED_FDA_DECISION_NOT_AUTHENTICATED"


def test_wrong_application_rejected():
    assert check_outcome_identity(
        PROGRAM, replace(EVIDENCE, application_number="NDA 654321")
    ) == "APPLICATION_MISMATCH"


def test_wrong_indication_rejected():
    assert check_outcome_identity(
        PROGRAM, replace(EVIDENCE, indication="Condition B")
    ) == "INDICATION_MISMATCH"


def test_wrong_product_rejected():
    assert check_outcome_identity(
        PROGRAM, replace(EVIDENCE, product_name="Different Drug")
    ) == "PRODUCT_MISMATCH"


def test_bad_document_digest_rejected():
    assert check_outcome_identity(
        PROGRAM, replace(EVIDENCE, document_sha256="bad")
    ) == "INVALID_DOCUMENT_DIGEST"
