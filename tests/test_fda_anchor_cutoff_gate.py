import base64
from dataclasses import replace

import pytest

from research.fda_anchor_cutoff_gate import check_anchor_before_cutoff
from research.fda_anchor_receipt import AnchorReceipt, receipt_payload
from research.fda_prospective_prediction_ledger import append_prediction


def test_signed_receipt_before_and_after_cutoff(tmp_path):
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    path = tmp_path / "ledger.jsonl"
    head = append_prediction(
        path, trial_id="EXAMPLE", prediction="ABSTAIN",
        cutoff_utc="2026-12-01T00:00:00Z",
        recorded_at_utc="2026-11-01T00:00:00Z",
        model_commit="abc123", evidence_manifest_sha256="a" * 64,
    )
    unsigned = AnchorReceipt(head, "2026-11-01T00:01:00Z", "trusted-key", "")
    signed = replace(unsigned, signature_base64=base64.b64encode(private.sign(receipt_payload(unsigned))).decode())
    keys = {"trusted-key": public}
    early = check_anchor_before_cutoff(path, signed, keys, prediction_cutoff_utc="2026-12-01T00:00:00Z")
    assert early.status == "SIGNED_PRE_CUTOFF_UNTRUSTED_TIME"
    late = check_anchor_before_cutoff(path, signed, keys, prediction_cutoff_utc="2026-10-01T00:00:00Z")
    assert late.status == "ANCHOR_AFTER_CUTOFF"
    unknown = check_anchor_before_cutoff(path, signed, {}, prediction_cutoff_utc="2026-12-01T00:00:00Z")
    assert unknown.status == "SIGNATURE_INVALID"
