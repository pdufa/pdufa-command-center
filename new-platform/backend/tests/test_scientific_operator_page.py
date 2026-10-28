"""Test the active isolated scientific operator HTML route."""
from fastapi.testclient import TestClient
from app import main

VALID_CLIENT = "1234567890-testpublicclient.apps.googleusercontent.com"


def test_operator_page_disabled_without_mode(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_ACCESS_MODE", raising=False)
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 503


def test_operator_page_renders_google_sign_in_and_research_when_configured(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", VALID_CLIENT)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert 'data-google-client-id="' + VALID_CLIENT + '"' in response.text
    assert "accounts.google.com/gsi/client" in response.text
    assert "/api/scientific-assessment/operator/me" in response.text
    assert "/api/scientific-assessment/operator/research" in response.text
    assert "owner@example.org" not in response.text
    assert "independent" in response.text.lower()
    assert response.headers["cache-control"].startswith("no-store")
    assert response.headers["x-frame-options"] == "DENY"
    assert "script-src 'nonce-" in response.headers["content-security-policy"]


def test_operator_page_escapes_config_in_html(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    malicious_id = '123-a.apps.googleusercontent.com"><script>alert(1)</script>'
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", malicious_id)
    with TestClient(main.app) as client:
        response = client.get("/scientific/operator")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_operator_report_requires_signin(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        response = client.get(
            "/api/scientific-assessment/operator/research",
            params={"exact_id": "TRIAL|NCT02142738"},
        )
    assert response.status_code == 401
