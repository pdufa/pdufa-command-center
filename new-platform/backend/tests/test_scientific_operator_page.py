"""Google single-operator browser path is opt-in and cannot grant signoff."""
from app.scientific_operator_page import operator_signin_page

VALID_CLIENT = "1234567890-testpublicclient.apps.googleusercontent.com"


def test_operator_page_unconfigured_has_no_google_button(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_ACCESS_MODE", raising=False)
    monkeypatch.delenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", raising=False)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    response = operator_signin_page()
    assert response.status_code == 200
    assert "not completely configured" in response.body.decode("utf-8")
    assert "g_id_signin" not in response.body.decode("utf-8")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"


def test_operator_page_renders_google_sign_in_only_when_configured(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    response = operator_signin_page()
    assert response.status_code == 200
    assert 'data-client_id="' + VALID_CLIENT + '"' in response.body.decode("utf-8")
    assert "g_id_signin" in response.body.decode("utf-8")
    assert "/api/scientific-assessment/operator/me" in response.body.decode("utf-8")
    assert "owner@example.org" not in response.body.decode("utf-8")
    assert "independent" in response.body.decode("utf-8").lower()
    assert "script-src 'nonce-" in response.headers["content-security-policy"]


def test_operator_page_never_interpolates_malicious_client_id(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID",
                       '123-a.apps.googleusercontent.com"><script>alert(1)</script>')
    response = operator_signin_page()
    assert response.status_code == 200
    assert 'data-client_id="' not in response.body.decode("utf-8")
    assert "<script>alert(1)</script>" not in response.body.decode("utf-8")
    assert "g_id_signin" not in response.body.decode("utf-8")


def test_operator_page_never_makes_scientific_approval_claim(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    response = operator_signin_page()
    assert response.status_code == 200
    assert "grant professional reviewer credentials" in response.body.decode("utf-8")
    assert "mayPromoteScientificScore" not in response.body.decode("utf-8")
