"""Research-only signed ledger-head receipt verification.

A trusted signer's public key must be provisioned out of band.
The signer must independently guarantee its claimed timestamp.
A valid signature alone is not proof of external timestamping.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Mapping


_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class AnchorReceipt:
    ledger_head_sha256: str
    anchored_at_utc: str
    signer_id: str
    signature_base64: str


def receipt_payload(receipt: AnchorReceipt) -> bytes:
    return json.dumps(
        {
            "anchored_at_utc": receipt.anchored_at_utc,
            "ledger_head_sha256": receipt.ledger_head_sha256,
            "signer_id": receipt.signer_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_anchor_receipt(
    receipt: AnchorReceipt,
    trusted_signers: Mapping[str, bytes],
    *,
    expected_head_sha256: str,
) -> bool:
    if not _DIGEST.fullmatch(receipt.ledger_head_sha256):
        return False
    if receipt.ledger_head_sha256 != expected_head_sha256:
        return False
    if receipt.signer_id not in trusted_signers:
        return False
    try:
        stamp = datetime.fromisoformat(receipt.anchored_at_utc.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return False
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(trusted_signers[receipt.signer_id])
        signature = base64.b64decode(receipt.signature_base64, validate=True)
        key.verify(signature, receipt_payload(receipt))
    except (ImportError, ValueError, TypeError):
        return False
    return True
