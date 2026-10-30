import json

from research.predictions_nightly_cli import run_cli


def test_cli_disabled_does_not_read_or_write(tmp_path):
    result = run_cli([
        "--candidates", str(tmp_path / "absent.json"),
        "--evidence", str(tmp_path / "absent2.json"),
        "--jobs", str(tmp_path / "jobs"),
    ])
    assert result["status"] == "DISABLED"
    assert not (tmp_path / "jobs").exists()


def test_cli_explicit_run_with_input_exports(tmp_path):
    candidates = tmp_path / "candidates.json"
    evidence = tmp_path / "evidence.json"
    candidates.write_text(json.dumps([{"trial_id": "T1", "groups": ["WT"]}]))
    evidence.write_text(json.dumps({"T1": {
        "Phase 3 efficacy and endpoints": {
            "findings": "Endpoint reported",
            "source_urls": ["https://clinicaltrials.gov/study/NCT123"],
        }
    }}))
    result = run_cli([
        "--candidates", str(candidates),
        "--evidence", str(evidence),
        "--jobs", str(tmp_path / "jobs"),
        "--enable",
    ])
    assert result["status"] == "FINISHED"
    assert len(result["worker"]["processed"]) == 1
    assert result["worker"]["processed"][0]["decision"] == "ABSTAIN"
