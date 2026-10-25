import pytest

from app.scientific_google_identity import identity_from_verified_claims, verified_google_identity


def claims():
    return {
        "iss": "https://accounts.google.com",
        "aud": "scientific-client-id",
        "sub": "immutable-google-subject-123",
        "email": "reviewer@example.org",
        "email_verified": True,
    }


def test_verified_claims_do_not_grant_review_signoff():
    identity = identity_from_verified_claims(claims(), "scientific-client-id")
    assert identity["providerSubject"] == "immutable-google-subject-123"
    assert identity["identityVerified"] == "true"
    assert identity["clinicalCredentialsVerified"] == "false"
    assert identity["reviewerRoleAuthorized"] == "false"
    assert identity["maySignOff"] == "false"


@pytest.mark.parametrize("field,value", [
    ("iss", "https://evil.example"), ("aud", "other-client"),
    ("sub", ""), ("email", None), ("email_verified", False),
    ("email_verified", "true"),
])
def test_reject_invalid_identity_claims(field, value):
    payload = claims()
    payload[field] = value
    with pytest.raises(ValueError):
        identity_from_verified_claims(payload, "scientific-client-id")


def test_unconfigured_google_authentication_fails_closed(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(ValueError, match="not configured"):
        verified_google_identity("x" * 40)
