"""Require a forecast to appear exactly once in a verified ledger.

This verifies ledger membership, not an independently trusted timestamp.
"""
from __future__ import annotations

import json
from pathlib import Path

from research.fda_prediction_ledger_audit import audit_ledger
from research.fda_prospective_outcome_scoring import FrozenPrediction


def check_prediction_membership(
    ledger_path: str | Path,
    *,
    expected_head_sha256: str,
    prediction: FrozenPrediction,
) -> str:
    intact, _ = audit_ledger(ledger_path, expected_head_sha256)
    if not intact:
        return "LEDGER_NOT_VERIFIED"
    matching_hashes = []
    with Path(ledger_path).open("r", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("entry_hash") == prediction.ledger_entry_hash:
                matching_hashes.append(event)
    if len(matching_hashes) != 1:
        return "PREDICTION_NOT_UNIQUE"
    event = matching_hashes[0]
    if any((
        event.get("trial_id") != prediction.trial_id,
        event.get("prediction") != prediction.prediction,
        event.get("recorded_at_utc") != prediction.recorded_at_utc,
        event.get("cutoff_utc") != prediction.cutoff_utc,
    )):
        return "PREDICTION_FIELDS_MISMATCH"
    return "LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED"
