"""Google single-operator browser path is opt-in and cannot grant signoff."""
from fastapi.testclient import TestClient
from app import main

VALID_CLIENT = "1234567890-testpublicclient.apps.googleusercontent.com"


def test_operator_page_unconfigured_has_no_google_button(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_ACCESS_MODE", raising=False)
    monkeypatch.delenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", raising=False)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert "not completely configured" in response.text
    assert "g_id_signin" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"


def test_operator_page_renders_google_sign_in_only_when_configured(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert 'data-client_id="' + VALID_CLIENT + '"' in response.text
    assert "g_id_signin" in response.text
    assert "/api/scientific-assessment/operator/me" in response.text
    assert "owner@example.org" not in response.text
    assert "independent" in response.text.lower()
    assert "script-src 'nonce-" in response.headers["content-security-policy"]


def test_operator_page_never_interpolates_malicious_client_id(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID",
                       '123-a.apps.googleusercontent.com"><script>alert(1)</script>')
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert 'data-client_id="' not in response.text
    assert "<script>alert(1)</script>" not in response.text
    assert "g_id_signin" not in response.text


def test_operator_page_never_makes_scientific_approval_claim(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert "grant professional reviewer credentials" in response.text
    assert "mayPromoteScientificScore" not in response.text
