import json

from assessment_levels_07_20.historical_report import main


def sample():
    trial = {
        "nct_id": "NCT12345678", "application_id": "NDA123456",
        "indication": "Example indication", "frozen_on": "2024-01-01",
        "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
        "snapshot_sha256": "a" * 64,
    }
    evidence = [{
        "nct_id": trial["nct_id"], "application_id": trial["application_id"],
        "indication": trial["indication"], "cutoff_on": trial["cutoff_on"],
        "evidence": [{"nct_id": trial["nct_id"], "source_url": "https://example.org/study",
                      "sha256": "b" * 64, "published_on": "2024-01-02",
                      "retrieved_on": "2024-01-03"}],
    }]
    return {"trials": [trial]}, evidence


def test_cli_success_without_accuracy(tmp_path, capsys):
    manifest, evidence = sample()
    a, b = tmp_path / "manifest.json", tmp_path / "evidence.json"
    a.write_text(json.dumps(manifest))
    b.write_text(json.dumps(evidence))
    assert main(["--manifest", str(a), "--evidence", str(b)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["eligible_for_blind_review"]
    assert report["accuracy"] is None
    assert report["fda_prediction"] == "ABSTAIN"


def test_cli_fails_closed_without_evidence(tmp_path, capsys):
    manifest, _ = sample()
    a, b = tmp_path / "manifest.json", tmp_path / "evidence.json"
    a.write_text(json.dumps(manifest))
    b.write_text("[]")
    assert main(["--manifest", str(a), "--evidence", str(b)]) == 1
    assert json.loads(capsys.readouterr().out)["missing_evidence_count"] == 1
