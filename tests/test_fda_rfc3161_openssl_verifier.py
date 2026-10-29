from hashlib import sha256

from research.fda_rfc3161_openssl_verifier import verify_rfc3161_token


def test_missing_token_or_ca_fails_closed():
    result = verify_rfc3161_token(
        b"", expected_imprint_sha256="a" * 64,
        trusted_ca_pem=b"example", pinned_ca_bundle_sha256=sha256(b"example").hexdigest(),
    )
    assert not result.cryptographically_verified
    assert result.status == "MISSING_TOKEN_OR_TRUST_BUNDLE"


def test_wrong_trust_bundle_pin_fails_closed():
    result = verify_rfc3161_token(
        b"fake", expected_imprint_sha256="a" * 64,
        trusted_ca_pem=b"example", pinned_ca_bundle_sha256="0" * 64,
    )
    assert not result.cryptographically_verified
    assert result.status == "CA_BUNDLE_PIN_MISMATCH"


def test_invalid_imprint_fails_closed():
    result = verify_rfc3161_token(
        b"fake", expected_imprint_sha256="invalid",
        trusted_ca_pem=b"example", pinned_ca_bundle_sha256=sha256(b"example").hexdigest(),
    )
    assert not result.cryptographically_verified
    assert result.status == "INVALID_IMPRINT"


def test_fabricated_token_is_not_accepted():
    ca = b"not-a-valid-ca"
    result = verify_rfc3161_token(
        b"not-a-real-rfc3161-token", expected_imprint_sha256="a" * 64,
        trusted_ca_pem=ca, pinned_ca_bundle_sha256=sha256(ca).hexdigest(),
    )
    assert not result.cryptographically_verified
    assert result.status in {"TOKEN_SIGNATURE_OR_IMPRINT_INVALID", "VERIFIER_UNAVAILABLE"}
