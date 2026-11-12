"""Fail-closed scheduled Level 3 source-readiness report verification.

Report status is source-only. Reconstruct expected contents from the same
checksum-bound registry receipts and FOCUS snapshot, rather than trusting
client-provided counts or purported clinical verdicts.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from level3_focus_evidence_readiness import build_readiness


def verify_level3_report(
    report: object, roster_bytes: bytes, directory: Path,
    now: datetime | None = None,
) -> bool:
    if not isinstance(report, dict) or not isinstance(roster_bytes, bytes):
        return False
    try:
        now = now or datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.tzinfo is None:
            return False
        stamp = report.get("built_at_utc")
        if not isinstance(stamp, str):
            return False
        built = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if built.tzinfo is None or not timedelta(0) <= now - built <= timedelta(minutes=5):
            return False
        expected = build_readiness(roster_bytes, directory, built)
        return report == expected
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, OverflowError):
        return False
