"""The single operator login is not a substitute for independent review."""
from fastapi.testclient import TestClient

from app import main


def test_single_operator_requires_config(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_ACCESS_MODE", raising=False)
    monkeypatch.delenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", raising=False)
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 503


def test_single_operator_requires_verified_google_token(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me")
    assert r.status_code == 401


def test_single_operator_rejects_other_google_account(monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "someoneelse@example.org",
                                   "providerSubject": "another-google-sub"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 403


def test_single_operator_cannot_sign_off_or_promote_score(monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "OWNER@example.org",
                                   "providerSubject": "approved-google-sub"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 200
    payload = r.json()
    assert payload["role"] == "operator"
    assert payload["identityVerified"] is True
    assert payload["maySubmitScientificReview"] is False
    assert payload["maySignOff"] is False
    assert payload["independentlyVerified"] is False
    assert payload["mayPromoteScientificScore"] is False
    assert payload["reviewerProvisioningRequired"] is True


def test_auth_status_exposes_mode_not_email(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID",
                       "example-client.apps.googleusercontent.com")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/reviewer/auth-status",
                       headers={"X-PDUFA-Internal-Key": "test-internal-key"})
    assert r.status_code == 200
    assert r.json()["accessMode"] == "single_operator"
    assert r.json()["singleOperatorConfigured"] is True
    assert r.json()["independentVerificationRequiresDistinctReviewers"] is True
    assert "owner@example.org" not in r.text


def test_single_operator_page_discloses_no_account_email(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", "web-client.apps.googleusercontent.com")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert "Sign in with your Google account" in response.text
    assert "https://accounts.google.com/gsi/client" in response.text
    assert "owner@example.org" not in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "no-store" in response.headers["cache-control"]
    assert "nonce-" in response.headers["content-security-policy"]


def test_operator_scientific_research_is_denied_without_identity(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/operator/research",
                              params={"exact_id": "TRIAL|NCT02142738"})
    assert response.status_code == 401


def test_operator_review_worksheet_denies_unauthenticated_requests(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/worksheet/NCT02142738")
    assert r.status_code == 401


def test_operator_review_worksheet_never_promotes_science(monkeypatch):
    from app import scientific_google_identity, scientific_review_packet
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "OWNER@example.org", "providerSubject": "one-google-id"})
    called = []
    def packet(nct):
        called.append(nct)
        return {
            "nctId": nct, "scientificallyVerified": False,
            "readyForFullScientificConclusion": False,
            "scientificConclusion": None, "fdaApprovalProbability": None,
            "reconciliation": {
                "unresolvedCount": 8, "independentlyResolvedCount": 0,
                "checks": [{"title": "Original SAP", "resolved": False,
                            "criteriaSatisfied": 0, "resolutionCriteria": ["Audit protocol date"]}],
            },
            "packetIntegrity": {"algorithm": "SHA-256", "digest": "0"*64},
        }
    monkeypatch.setattr(scientific_review_packet, "build_review_packet", packet)
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/worksheet/NCT02142738",
                       headers={"Authorization": "Bearer simulated-test-token"})
    assert r.status_code == 200
    assert called == ["NCT02142738"]
    assert r.headers["cache-control"] == "private, no-store"
    assert r.json()["scientificallyVerified"] is False
    assert r.json()["readyForFullScientificConclusion"] is False
    assert r.json()["reconciliation"]["checks"][0]["resolved"] is False


def test_operator_review_worksheet_rejects_wrong_account_and_bad_id(monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "someoneelse@example.org"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/worksheet/NCT02142738",
                       headers={"Authorization": "Bearer simulated-test-token"})
    assert r.status_code == 403
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "owner@example.org"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/worksheet/INVALID",
                       headers={"Authorization": "Bearer simulated-test-token"})
    assert r.status_code == 422
