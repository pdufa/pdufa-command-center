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
    result = inspect_prospective_evidence(
        prediction, outcome,
        ledger_path=tmp_path / "missing.jsonl",
        anchor_receipt=AnchorReceipt("a" * 64, "2026-11-01T00:00:00Z", "untrusted", ""),
        trusted_signers={},
        outcome_document_path=document,
    )
    assert result.prediction_gate == "LEDGER_INTEGRITY_FAILED"
    assert result.membership_gate == "LEDGER_NOT_VERIFIED"
    assert result.outcome_gate == "BYTES_MATCH_ORIGIN_UNVERIFIED"
    assert result.score.status == "PROVENANCE_NOT_VERIFIED"
    assert result.score.correct is None
