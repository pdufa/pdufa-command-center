"""Research-only cutoff gate for signed ledger-head receipts.

Trust in the signer's clock and issuance process must be established
independently; a signature only authenticates the signer's assertion.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from research.fda_anchor_receipt import AnchorReceipt
from research.fda_anchored_ledger_audit import audit_anchored_ledger


@dataclass(frozen=True)
class CutoffGate:
    status: str
    entries: int


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def check_anchor_before_cutoff(
    ledger_path: str | Path,
    receipt: AnchorReceipt,
    trusted_signers: Mapping[str, bytes],
    *,
    prediction_cutoff_utc: str,
) -> CutoffGate:
    audit = audit_anchored_ledger(ledger_path, receipt, trusted_signers)
    if not audit.chain_intact:
        return CutoffGate("LEDGER_INTEGRITY_FAILED", audit.entries)
    if not audit.signed_receipt_valid:
        return CutoffGate("SIGNATURE_INVALID", audit.entries)
    try:
        anchor_time = _timestamp(receipt.anchored_at_utc)
        cutoff = _timestamp(prediction_cutoff_utc)
    except ValueError:
        return CutoffGate("INVALID_TIMESTAMP", audit.entries)
    if anchor_time > cutoff:
        return CutoffGate("ANCHOR_AFTER_CUTOFF", audit.entries)
    # A signed pre-cutoff assertion is not proof of trusted external time.
    return CutoffGate("SIGNED_PRE_CUTOFF_UNTRUSTED_TIME", audit.entries)
