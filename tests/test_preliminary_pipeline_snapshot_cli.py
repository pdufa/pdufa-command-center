import json
from datetime import datetime, timezone
from research.preliminary_pipeline_snapshot_cli import main


def test_cli_generates_abstaining_report(tmp_path):
    source = tmp_path / "snapshot.json"
    target = tmp_path / "report.json"
    snapshot = {
        "source_system": "PDUFA_PIPELINE",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "restriction_snapshot_sha256": "a" * 64,
        "records": [{"program_id": "X", "publicly_traded": True,
                     "market_cap_usd": 500000000, "pipeline_member": True,
                     "fda_pdufa_target_confirmed": True}],
    }
    source.write_text(json.dumps(snapshot), encoding="utf-8")
    assert main([str(source), str(target)]) == 0
    result = json.loads(target.read_text(encoding="utf-8"))
    assert result["candidate_for_evidence_review"] == 1
    assert result["prediction_status"] == "ABSTAIN"
    assert result["data_authenticity_verified"] is False
