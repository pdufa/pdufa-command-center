"""Unit tests for Benchmark 1 leakage safeguards; no historical outcome is input."""
import hashlib
import pytest

from app.benchmark1_firewall import validate_source, freeze_input_manifest, freeze_prediction


def source(text="Predecision study evidence", published="2024-03-01T12:00:00-05:00"):
    return {
        "source_url": "https://example.org/predecision-study",
        "published_at": published,
        "retrieved_at": "2024-03-12T12:00:00-04:00",
        "text": text,
        "sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
    }


def test_valid_source_and_deterministic_manifest():
    item = source()
    assert validate_source(item) == item
    assert freeze_input_manifest([item], rules_version="v1") == freeze_input_manifest([item], rules_version="v1")


def test_reject_post_cutoff():
    with pytest.raises(ValueError, match="Post-cutoff"):
        validate_source(source(published="2024-03-14T00:00:00-04:00"))


def test_reject_undated_source():
    item = source()
    del item["published_at"]
    with pytest.raises(ValueError, match="provenance"):
        validate_source(item)


def test_reject_tampered_text():
    item = source()
    item["text"] = "changed"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_source(item)


def test_reject_known_outcome_text():
    with pytest.raises(ValueError, match="Outcome-side"):
        validate_source(source(text="FDA approves first treatment for patients with liver scarring"))


def test_reject_duplicate_sources():
    with pytest.raises(ValueError, match="Duplicate"):
        freeze_input_manifest([source(), source()], rules_version="v1")


def test_freeze_requires_all_40_assessments():
    assessments = [{"number": i, "evidence_refs": ["source1"], "reason": "test"} for i in range(1, 41)]
    frozen = freeze_prediction("ABSTAIN", "a" * 64, assessments, rules_version="v1")
    assert frozen["prediction"]["decision"] == "ABSTAIN"
    with pytest.raises(ValueError, match="40"):
        freeze_prediction("PASS", "a" * 64, assessments[:-1], rules_version="v1")


def test_invalid_decision_rejected():
    assessments = [{"number": i, "evidence_refs": ["source1"], "reason": "test"} for i in range(1, 41)]
    with pytest.raises(ValueError, match="decision"):
        freeze_prediction("APPROVED", "a" * 64, assessments, rules_version="v1")
