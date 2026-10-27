"""Synthetic tests for the conservative FDA source review queue."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_fda_evidence_review_queue import build_review_queue

def candidate(**changes):
    row = dict(application_id="NDA123456", submission_id="ORIG-1",
               review_cycle=1, action_type="APPROVAL",
               action_date="2024-02-01", retrieved_at="2024-02-02T12:00:00Z",
               official_source_url="https://www.accessdata.fda.gov/test.pdf",
               document_title="FDA letter", evidence_locator="page 1",
               document_sha256="a" * 64)
    row.update(changes)
    return row

def test_clean_metadata_still_needs_independent_review():
    result = build_review_queue([candidate()])
    assert result["tasks"][0]["status"] == "AWAITING_INDEPENDENT_REVIEW"
    assert result["model_eligible_count"] == 0
    assert result["verified_pass_count"] == 0

def test_duplicate_cycle_quarantined():
    result = build_review_queue([candidate(), candidate()])
    assert "duplicate_review_cycle_identity" in result["tasks"][1]["issues"]

def test_missing_hash_quarantined():
    result = build_review_queue([candidate(document_sha256=None)])
    assert "source_bytes_not_hashed" in result["tasks"][0]["issues"]

def test_retrieval_before_action_quarantined():
    result = build_review_queue([candidate(retrieved_at="2024-01-01T00:00:00Z")])
    assert "retrieval_precedes_action" in result["tasks"][0]["issues"]

def test_naive_timestamp_quarantined():
    result = build_review_queue([candidate(retrieved_at="2024-02-02T12:00:00")])
    assert "retrieval_timestamp_missing_timezone" in result["tasks"][0]["issues"]

def test_nonobject_quarantined():
    result = build_review_queue([None])
    assert result["tasks"][0]["status"] == "QUARANTINED"
