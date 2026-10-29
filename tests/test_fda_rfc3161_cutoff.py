from research.fda_rfc3161_cutoff import check_verified_timestamp_cutoff
from research.fda_rfc3161_openssl_verifier import RFC3161Verification


TIMES = dict(
    token_generation_time_utc="2026-10-01T12:00:00Z",
    prediction_recorded_at_utc="2026-10-01T11:00:00Z",
    prediction_cutoff_utc="2026-10-02T00:00:00Z",
    fda_decision_at_utc="2026-10-03T00:00:00Z",
)


def test_unverified_token_rejected():
    assert check_verified_timestamp_cutoff(
        RFC3161Verification("INVALID"), **TIMES
    ) == "TOKEN_NOT_CRYPTOGRAPHICALLY_VERIFIED"


def test_verified_signature_still_needs_time_binding():
    assert check_verified_timestamp_cutoff(
        RFC3161Verification("SIGNATURE_VERIFIED", True), **TIMES
    ) == "CHRONOLOGY_PLAUSIBLE_TOKEN_TIME_BINDING_UNVERIFIED"


def test_late_timestamp_rejected():
    times = {**TIMES, "token_generation_time_utc": "2026-10-02T01:00:00Z"}
    assert check_verified_timestamp_cutoff(
        RFC3161Verification("SIGNATURE_VERIFIED", True), **times
    ) == "TOKEN_AFTER_CUTOFF"


def test_decision_before_cutoff_rejected():
    times = {**TIMES, "fda_decision_at_utc": "2026-10-01T13:00:00Z"}
    assert check_verified_timestamp_cutoff(
        RFC3161Verification("SIGNATURE_VERIFIED", True), **times
    ) == "CUTOFF_NOT_BEFORE_FDA_DECISION"
