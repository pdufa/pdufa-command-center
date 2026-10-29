import base64
from dataclasses import replace

import pytest

from research.fda_anchor_receipt import AnchorReceipt, receipt_payload, verify_anchor_receipt


def test_signed_anchor_receipt():
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    unsigned = AnchorReceipt("a" * 64, "2026-10-28T20:00:00Z", "trusted-anchor", "")
    signed = replace(unsigned, signature_base64=base64.b64encode(private.sign(receipt_payload(unsigned))).decode())
    trusted = {"trusted-anchor": public}
    assert verify_anchor_receipt(signed, trusted, expected_head_sha256="a" * 64)
    assert not verify_anchor_receipt(signed, trusted, expected_head_sha256="b" * 64)
    assert not verify_anchor_receipt(replace(signed, anchored_at_utc="2026-10-29T20:00:00Z"), trusted, expected_head_sha256="a" * 64)
    assert not verify_anchor_receipt(signed, {}, expected_head_sha256="a" * 64)
