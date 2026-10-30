"""Research-only signed anchor + prediction ledger integrity check.

Cryptographic validity does not establish a trusted time source unless
the signer's timestamp policy and identity are verified externally.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from research.fda_anchor_receipt import AnchorReceipt, verify_anchor_receipt
from research.fda_prediction_ledger_audit import audit_ledger


@dataclass(frozen=True)
class AnchorAudit:
    chain_intact: bool
    signed_receipt_valid: bool
    entries: int
    externally_trusted_timestamp: bool


def audit_anchored_ledger(
    ledger_path: str | Path,
    receipt: AnchorReceipt,
    trusted_signers: Mapping[str, bytes],
) -> AnchorAudit:
    chain_ok, count = audit_ledger(ledger_path, receipt.ledger_head_sha256)
    receipt_ok = verify_anchor_receipt(
        receipt, trusted_signers,
        expected_head_sha256=receipt.ledger_head_sha256,
    )
    # No caller-provided bool may certify an external timestamp.
    return AnchorAudit(chain_ok, receipt_ok, count, False)
