import json

from research.fda_prediction_ledger_audit import audit_ledger
from research.fda_prospective_prediction_ledger import append_prediction


BASE = dict(
    trial_id="EXAMPLE-TRIAL",
    prediction="ABSTAIN",
    cutoff_utc="2026-12-01T00:00:00Z",
    recorded_at_utc="2026-11-01T00:00:00Z",
    model_commit="abc123",
    evidence_manifest_sha256="a" * 64,
)


def test_valid_chain_and_expected_head(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append_prediction(path, **BASE)
    head = append_prediction(path, **BASE)
    assert audit_ledger(path, head) == (True, 2)
    assert audit_ledger(path, "0" * 64) == (False, 2)


def test_truncation_detected_against_head(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append_prediction(path, **BASE)
    head = append_prediction(path, **BASE)
    path.write_text(path.read_text().splitlines()[0] + "\n")
    assert audit_ledger(path, head) == (False, 1)


def test_mutation_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    head = append_prediction(path, **BASE)
    path.write_text(path.read_text().replace('"ABSTAIN"', '"PASS"'))
    assert audit_ledger(path, head) == (False, 0)
