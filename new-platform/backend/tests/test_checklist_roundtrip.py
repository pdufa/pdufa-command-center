from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app


def test_per_ticker_checklist_autosave_and_restore(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-secret-not-for-production")
    ticker = "T" + uuid4().hex[:10].upper()
    path = "/api/checklists/" + ticker + "/PIPELINE"
    headers = {"X-PDUFA-Internal-Key": "test-secret-not-for-production"}
    with TestClient(app) as client:
        initial = client.get(path, headers=headers)
        assert initial.status_code == 200
        assert initial.json()["version"] == 0

        save = client.put(path, headers=headers, json={
            "version": 0, "selections": {"cash": True, "market_cap": True},
            "notes": "Research notes for restored checklist"
        })
        assert save.status_code == 200
        assert save.json()["version"] == 1

        restored = client.get(path, headers=headers)
        assert restored.status_code == 200
        assert restored.json()["selections"]["cash"] is True
        assert restored.json()["notes"] == "Research notes for restored checklist"

        outdated = client.put(path, headers=headers, json={
            "version": 0, "selections": {}, "notes": "stale attempt"
        })
        assert outdated.status_code == 409

        changed = client.put(path, headers=headers, json={
            "version": 1, "selections": {"cash": False}, "notes": "Updated"
        })
        assert changed.status_code == 200
        assert changed.json()["version"] == 2
        assert client.get(path, headers=headers).json()["selections"]["cash"] is False


def test_archived_gem_stages_reject_new_writes_but_preserve_read_access(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-secret-not-for-production")
    ticker = "T" + uuid4().hex[:10].upper()
    headers = {"X-PDUFA-Internal-Key": "test-secret-not-for-production"}
    with TestClient(app) as client:
        for stage in ("GEM_JR", "GEM"):
            path = "/api/checklists/" + ticker + "/" + stage
            archived = client.get(path, headers=headers)
            assert archived.status_code == 200
            assert archived.json()["version"] == 0
            disabled = client.put(path, headers=headers, json={
                "version": 0, "selections": {"market_cap": True},
                "notes": "Must not create archived stage association"
            })
            assert disabled.status_code == 410
            assert client.get(path, headers=headers).json()["version"] == 0
