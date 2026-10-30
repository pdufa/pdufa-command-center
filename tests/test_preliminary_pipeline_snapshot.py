import pytest
from research.preliminary_pipeline_snapshot import triage_pipeline_snapshot


def _snapshot():
    return {
        "source_system": "PDUFA_PIPELINE",
        "exported_at": "2026-10-29T08:00:00-07:00",
        "restriction_snapshot_sha256": "a" * 64,
        "records": [{"program_id": "CASE-1", "publicly_traded": True,
                     "market_cap_usd": 300000000, "pipeline_member": True,
                     "fda_pdufa_target_confirmed": True}],
    }


def test_traceable_snapshot_does_not_become_a_prediction():
    report = triage_pipeline_snapshot(_snapshot(), now="2026-10-29T08:30:00-07:00")
    assert report["candidate_for_evidence_review"] == 1
    assert len(report["snapshot_sha256"]) == 64
    assert report["restriction_settings_verified"] is False
    assert report["prediction_status"] == "ABSTAIN"


@pytest.mark.parametrize("change", [
    {"exported_at": "2026-10-27T08:00:00-07:00"},
    {"exported_at": "2026-10-30T08:00:00-07:00"},
    {"exported_at": "2026-10-29T08:00:00"},
    {"source_system": "OTHER"},
    {"restriction_snapshot_sha256": "unverified"},
])
def test_rejects_untraceable_or_stale_snapshots(change):
    snapshot = _snapshot()
    snapshot.update(change)
    with pytest.raises(ValueError):
        triage_pipeline_snapshot(snapshot, now="2026-10-29T08:30:00-07:00")
