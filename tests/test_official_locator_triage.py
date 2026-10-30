"""Tests for research-only locator triage; no network or evidence promotion."""
from research.official_locator_triage import build_locator_triage


def test_locator_triage_counts_and_uniqueness():
    result = build_locator_triage()
    assert result["case_count"] == 6
    assert result["requirement_count"] == len(result["rows"])
    assert result["source_lead_count"] + result["unresolved_locator_count"] == result["requirement_count"]
    assert len({row["document_id"] for row in result["rows"]}) == result["requirement_count"]


def test_unresolved_locators_never_claim_missing_documents():
    result = build_locator_triage()
    for row in result["rows"]:
        assert row["original_bytes_acquired"] is False
        assert row["independently_verified"] is False
        assert row["publication_clock_verified"] is False
        if row["locator_status"] == "UNRESOLVED_LOCATOR":
            assert row["source_lead"] is None
            assert "NOT_LOCATED" in row["reason"] or row["reason"] == "OFFICIAL_LOCATOR_NOT_ESTABLISHED"
        else:
            assert row["source_lead"]


def test_triage_cannot_enable_prediction():
    result = build_locator_triage()
    assert result["verified_decisions"] == 0
    assert result["prediction_readiness"] == "NOT_READY"
    assert result["prediction_action"] == "ABSTAIN"
    assert result["research_only"] is True
