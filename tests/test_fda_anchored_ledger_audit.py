import base64
from dataclasses import replace

import pytest

from research.fda_anchor_receipt import AnchorReceipt, receipt_payload
from research.fda_anchored_ledger_audit import audit_anchored_ledger
from research.fda_prospective_prediction_ledger import append_prediction


def test_anchored_ledger_chain_and_receipt(tmp_path):
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    path = tmp_path / "predictions.jsonl"
    head = append_prediction(
        path, trial_id="EXAMPLE", prediction="ABSTAIN",
        cutoff_utc="2026-12-01T00:00:00Z",
        recorded_at_utc="2026-11-01T00:00:00Z",
        model_commit="abc123", evidence_manifest_sha256="a" * 64,
    )
    unsigned = AnchorReceipt(head, "2026-11-01T00:01:00Z", "signer-1", "")
    receipt = replace(unsigned, signature_base64=base64.b64encode(private.sign(receipt_payload(unsigned))).decode())
    result = audit_anchored_ledger(path, receipt, {"signer-1": public})
    assert result.chain_intact and result.signed_receipt_valid
    assert result.entries == 1
    assert result.externally_trusted_timestamp is False
    path.write_text(path.read_text().replace('"ABSTAIN"', '"PASS"'))
    tampered = audit_anchored_ledger(path, receipt, {"signer-1": public})
    assert not tampered.chain_intact
