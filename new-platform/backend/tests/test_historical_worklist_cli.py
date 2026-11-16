import json

from assessment_levels_07_20.historical_worklist_cli import main


def test_cli_generates_missing_source_tasks(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    sources = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"trials": [{
        "nct_id": "NCT12345678", "application_id": "NDA123456",
        "indication": "Example", "cutoff_on": "2024-02-01"
    }]}), encoding="utf-8")
    sources.write_text("[]", encoding="utf-8")
    assert main(["--manifest", str(manifest), "--sources", str(sources)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["task_count"] >= 2
    assert result["collection_executed"] is False
    assert result["scientific_status"] == "NOT_VERIFIED"


def test_cli_rejects_invalid_json(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    sources = tmp_path / "sources.json"
    manifest.write_text("{broken", encoding="utf-8")
    sources.write_text("[]", encoding="utf-8")
    assert main(["--manifest", str(manifest), "--sources", str(sources)]) == 2
    assert json.loads(capsys.readouterr().err)["collection_executed"] is False


def test_cli_rejects_missing_file(tmp_path, capsys):
    assert main(["--manifest", str(tmp_path / "absent.json"),
                 "--sources", str(tmp_path / "other.json")]) == 2
    assert "error" in json.loads(capsys.readouterr().err)
