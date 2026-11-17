from assessment_levels_07_20.historical_coverage import summarize_historical_coverage


def sample():
    trial = {
        "nct_id": "NCT12345678", "application_id": "NDA123456",
        "indication": "Example indication", "frozen_on": "2024-01-01",
        "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
        "snapshot_sha256": "a" * 64,
    }
    evidence = {
        "nct_id": trial["nct_id"], "application_id": trial["application_id"],
        "indication": trial["indication"], "cutoff_on": trial["cutoff_on"],
        "evidence": [{"nct_id": trial["nct_id"], "source_url": "https://example.org/study",
                      "sha256": "b" * 64, "published_on": "2024-01-02",
                      "retrieved_on": "2024-01-03"}],
    }
    return {"trials": [trial]}, [evidence]


def test_complete_coverage_does_not_claim_accuracy():
    manifest, evidence = sample()
    report = summarize_historical_coverage(manifest, evidence)
    assert report["trial_count"] == 1
    assert report["trials_with_evidence_count"] == 1
    assert report["missing_evidence_count"] == 0
    assert report["eligible_for_blind_review"]
    assert report["accuracy"] is None
    assert report["fda_prediction"] == "ABSTAIN"


def test_missing_evidence_is_counted():
    manifest, _ = sample()
    report = summarize_historical_coverage(manifest, [])
    assert report["missing_evidence_count"] == 1
    assert not report["eligible_for_blind_review"]


def test_unlinked_evidence_is_counted():
    manifest, evidence = sample()
    evidence[0]["application_id"] = "NDA999999"
    report = summarize_historical_coverage(manifest, evidence)
    assert report["unlinked_evidence_count"] == 1
    assert report["missing_evidence_count"] == 1
    assert not report["eligible_for_blind_review"]
