from research.fda_external_timestamp_policy import (
    TimestampAuthorityPolicy, certify_timestamp, validate_policy,
)


def test_valid_configuration_does_not_prove_timestamp():
    policy = TimestampAuthorityPolicy("Example TSA", "a" * 64, "1.2.3")
    assert validate_policy(policy) == (True, ())
    assert certify_timestamp(policy, b"fabricated-token") is False


def test_invalid_configuration_rejected():
    policy = TimestampAuthorityPolicy("", "bad", "invalid", "sha1")
    valid, errors = validate_policy(policy)
    assert not valid
    assert set(errors) == {
        "MISSING_AUTHORITY", "INVALID_TRUST_ANCHOR",
        "INVALID_POLICY_OID", "UNSUPPORTED_HASH_ALGORITHM",
    }
