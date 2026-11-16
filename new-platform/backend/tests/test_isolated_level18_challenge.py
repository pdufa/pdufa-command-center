from assessment_levels_07_20.level18_challenge import validate_level18_challenge


def example():
    return {
        "nct_id": "NCT04576949", "cutoff_on": "2026-01-03",
        "evidence_receipts": [{
            "receipt_id": "r1", "nct_id": "NCT04576949",
            "source_url": "https://example.org/study",
            "published_on": "2026-01-01", "retrieved_on": "2026-01-02",
        }],
        "challenges": [{
            "counterargument": "Selection bias may affect inference",
            "alternative_explanation": "Baseline differences may contribute",
            "owner_id": "example-owner", "evidence_receipt_ids": ["r1"],
            "owner_acceptance_claimed": False,
        }],
    }


def test_evidence_linked_challenge_is_not_acceptance():
    result = validate_level18_challenge(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_unlinked_counterargument_rejected():
    record = example()
    record["challenges"][0]["evidence_receipt_ids"] = ["missing"]
    assert "UNLINKED_CHALLENGE_EVIDENCE_0" in validate_level18_challenge(record)["errors"]


def test_unverified_owner_acceptance_rejected():
    record = example()
    record["challenges"][0]["owner_acceptance_claimed"] = True
    assert "UNVERIFIED_OWNER_ACCEPTANCE_0" in validate_level18_challenge(record)["errors"]


def test_wrong_trial_receipt_rejected():
    record = example()
    record["evidence_receipts"][0]["nct_id"] = "NCT00000001"
    assert "RECEIPT_TRIAL_MISMATCH_0" in validate_level18_challenge(record)["errors"]


def test_post_cutoff_evidence_rejected():
    record = example()
    record["evidence_receipts"][0]["retrieved_on"] = "2026-01-04"
    assert "POST_CUTOFF_RECEIPT_0" in validate_level18_challenge(record)["errors"]
