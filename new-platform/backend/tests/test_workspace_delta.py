"""Regression tests for safe incremental workspace patching."""
from app.workspace_delta import publish


def snapshot(rows, as_of="2026-10-19T10:00:00Z"):
    return {
        "mode": "LIVE_READ_ONLY_GITHUB_SOURCE", "asOf": as_of,
        "pipeline": rows,
        "members": {"GEM_JR": {"rows": []}, "GEM": {"rows": []}},
        "sourceHealth": {"state": "COMPLETE_PUBLISHED"},
    }


def test_delta_add_update_remove():
    first = publish(snapshot([
        {"programId": "PDUFA-000001", "ticker": "AAA", "score": 1},
        {"programId": "PDUFA-000002", "ticker": "BBB", "score": 1},
    ]))
    assert first["reset"] is True
    changed = publish(snapshot([
        {"programId": "PDUFA-000001", "ticker": "AAA", "score": 2},
        {"programId": "PDUFA-000003", "ticker": "CCC", "score": 1},
    ]), since=first["version"])
    assert changed["reset"] is False
    assert changed["baseVersion"] == first["version"]
    assert {r["programId"] for r in changed["changes"]["PIPELINE"]["upsert"]} == {
        "PDUFA-000001", "PDUFA-000003"}
    assert changed["changes"]["PIPELINE"]["remove"] == ["PDUFA-000002"]
    assert changed["changes"]["PIPELINE"]["count"] == 2


def test_same_version_unchanged():
    base = snapshot([{"programId": "PDUFA-000004", "ticker": "DDD"}])
    version = publish(base)["version"]
    assert publish(base, since=version)["unchanged"] is True


def test_unknown_version_requires_full_reset():
    result = publish(snapshot([]), since="not-a-known-version")
    assert result["reset"] is True


def test_duplicate_identity_is_rejected():
    base = snapshot([{"programId": "PDUFA-000001"}, {"programId": "PDUFA-000001"}])
    try:
        publish(base)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate identities must never produce an unsafe delta")


def test_stale_source_is_rejected():
    stale = snapshot([])
    stale["sourceHealth"]["state"] = "STALE"
    try:
        publish(stale)
    except ValueError:
        pass
    else:
        raise AssertionError("Stale source must not be published as a new version")


def test_fetch_timestamp_does_not_create_false_delta():
    initial = snapshot([{"programId": "PDUFA-000101", "ticker": "AAA"}])
    version = publish(initial)["version"]
    refreshed = snapshot([{"programId": "PDUFA-000101", "ticker": "AAA"}],
                         as_of="2026-10-19T10:05:00Z")
    refreshed["fetchedAt"] = "2026-10-19T17:05:00Z"
    assert publish(refreshed, since=version)["unchanged"] is True
