from dataclasses import replace
from hashlib import sha256

from research.fda_anchor_receipt import AnchorReceipt
from research.fda_prospective_outcome_scoring import FrozenPrediction, VerifiedOutcome
from research.fda_provenance_scoring_pipeline import inspect_prospective_evidence


def test_missing_ledger_and_matching_document_still_abstain(tmp_path):
    data = b"%PDF-1.4\nexample\n"
    document = tmp_path / "decision.pdf"
    document.write_bytes(data)
    prediction = FrozenPrediction(
        "EXAMPLE", "PASS", "2026-11-01T00:00:00Z",
        "2026-12-01T00:00:00Z", "a" * 64,
    )
    outcome = VerifiedOutcome(
        "EXAMPLE", "PASS", "2026-12-02T00:00:00Z",
        sha256(data).hexdigest(), True,
    )
    receipt = AnchorReceipt("a" * 64, "2026-11-01T00:00:00Z", "untrusted", "")
    kwargs = dict(
        ledger_path=tmp_path / "missing.jsonl",
        anchor_receipt=receipt,
        trusted_signers={},
        outcome_document_path=document,
    )
    result = inspect_prospective_evidence(prediction, outcome, **kwargs)
    assert result.prediction_gate == "LEDGER_INTEGRITY_FAILED"
    assert result.membership_gate == "LEDGER_NOT_VERIFIED"
    assert result.chronology_gate == "CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED"
    assert result.outcome_gate == "BYTES_MATCH_ORIGIN_UNVERIFIED"
    assert result.score.status == "PROVENANCE_NOT_VERIFIED"
    assert result.score.correct is None
    invalid = inspect_prospective_evidence(
        prediction, replace(outcome, decision_at_utc="2026-11-30T00:00:00Z"), **kwargs
    )
    assert invalid.chronology_gate == "CUTOFF_NOT_BEFORE_DECISION"
    assert invalid.score.correct is None
