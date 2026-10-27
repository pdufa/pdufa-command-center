"""Synthetic tests: metadata cannot certify historical FDA decisions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from screen_fda_evidence import screen_candidate


def row(**changes):
    return {"application_id": "NDA123456", "submission_id": "ORIG-1",
            "review_cycle": 1, "action_type": "APPROVAL",
            "action_date": "2020-02-01", "retrieved_at": "2026-10-27T10:00:00Z",
            "official_source_url": "https://www.fda.gov/drugs/example",
            "document_title": "FDA action letter", "evidence_locator": "page 1",
            **changes}


def test_complete_metadata_is_not_verification():
    result = screen_candidate(row())
    assert result["status"] == "CANDIDATE_METADATA_COMPLETE"
    assert result["independently_verified"] is False
    assert result["model_eligible"] is False


def test_non_fda_domain_quarantined():
    assert "non_official_source" in screen_candidate(
        row(official_source_url="https://fda.gov.example.com/fake"))["issues"]


def test_missing_review_cycle_quarantined():
    assert "invalid_review_cycle" in screen_candidate(row(review_cycle=0))["issues"]


def test_invalid_digest_quarantined():
    assert "invalid_document_sha256" in screen_candidate(
        row(document_sha256="not-a-sha256"))["issues"]


def test_bad_action_date_quarantined():
    assert "invalid_action_date" in screen_candidate(row(action_date="unknown"))["issues"]


def test_non_object_quarantined():
    assert screen_candidate(None)["status"] == "QUARANTINED"
