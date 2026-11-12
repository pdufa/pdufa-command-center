"""Verify every scheduled live-registry status against saved local NCT receipts.

Read-only checks. No network calls, predictions, repo writes or publication of
source content. A partial source batch is normal; it is never full coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from windows_local_agent_live_focus_registry import valid_cache, verified_roster

MAX_SCHEDULED_FETCHES = 10


def verify_live_summary(
    report: object, roster_bytes: bytes, capture_dir: Path,
    now: datetime | None = None,
) -> bool:
    if not isinstance(report, dict) or not isinstance(roster_bytes, bytes):
        return False
    try:
        if now is None:
            now = datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.tzinfo is None:
            return False
        if not isinstance(capture_dir, Path) or capture_dir.is_symlink():
            return False
        roster = json.loads(roster_bytes.decode("utf-8"))
        ncts = verified_roster(roster)
        fresh = sum(
            valid_cache(capture_dir / f"{nct}.json", nct,
                        hashlib.sha256(roster_bytes).hexdigest(), now)
            for nct in ncts
        )
        numbers = (
            "saved_roster_size", "fresh_exact_registry_captures",
            "remaining_without_fresh_capture", "network_attempts_this_run",
            "newly_captured_this_run", "failed_attempts_this_run",
            "scientific_levels_completed",
        )
        if any(type(report.get(k)) is not int or report[k] < 0 for k in numbers):
            return False
        attempts, newly, failed = (
            report["network_attempts_this_run"],
            report["newly_captured_this_run"],
            report["failed_attempts_this_run"],
        )
        expected = {
            "schema_version": 1,
            "workflow": "LEVEL2_FOCUS_LIVE_REGISTRY_CAPTURE",
            "saved_roster_size": len(ncts),
            "fresh_exact_registry_captures": fresh,
            "remaining_without_fresh_capture": len(ncts) - fresh,
            "source_state": (
                "ALL_FRESH_SOURCE_ONLY" if fresh == len(ncts)
                else "PARTIAL_SOURCE_CAPTURE"
            ),
            "source_adjudication": "NOT_COMPLETED",
            "clinical_prediction": None,
            "fda_approval_probability": None,
            "scientific_levels_completed": 0,
            "production_modified": False,
            "repository_modified": False,
            "roster_live_membership_verified": False,
            "cohort_sha256": hashlib.sha256(roster_bytes).hexdigest(),
        }
        return (
            all(type(report.get(k)) is type(v) and report[k] == v
                for k, v in expected.items())
            and attempts <= MAX_SCHEDULED_FETCHES
            and newly + failed == attempts
            and newly <= fresh
        )
    except (OSError, ValueError, TypeError, UnicodeError, KeyError, OverflowError):
        return False
