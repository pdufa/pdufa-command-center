#!/usr/bin/env python3
"""GEM block START/END Gmail notification; submitted is NOT delivered.

Uses the same configured Gmail secrets and SMTP sender as clinical scans.
An unavailable START email is an explicit failure, not a silently skipped
notification. END is attempted for unsuccessful/partial scans as well.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts.scan_email import (
    EmailSettings, EmailSetupError, EmailSendError,
    compose_start, compose_end, send_email,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=("START", "END"), required=True)
    parser.add_argument("--mode", choices=("BASELINE", "DELTA", "RECONCILE", "MANUAL"), required=True)
    parser.add_argument("--report", type=Path, default=Path("data/gem_scan_block_report.json"))
    parser.add_argument("--audit-dir", type=Path, default=Path("reports/gem_daily"))
    args = parser.parse_args(argv)
    run = str(os.environ.get("GITHUB_RUN_ID") or "manual")
    when = datetime.now(timezone.utc)
    status = "NOT_SUBMITTED"
    try:
        settings = EmailSettings.from_env()
        if args.event == "START":
            subject, body = compose_start("GEM", args.mode, run, when)
        else:
            try:
                report = json.loads(args.report.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                report = {}
            state = report.get("status") if isinstance(report, dict) else None
            if state not in ("PARTIAL", "FAILED"):
                state = "UNVERIFIED"
            counts = (report.get("clinical_registry") or {}) if isinstance(report, dict) else {}
            summary = (
                "GEM research-only block; not a trade approval.\n"
                f"Registry studies checked: {counts.get('studies_checked', 'Not reported')}\n"
                f"New results: {counts.get('new_records', 'Not reported')}\n"
                f"Stored Phase 3 observations: {counts.get('stored_results', 'Not reported')}\n"
                "All-source financing, clinical efficacy, market and historical returns "
                "are NOT independently certified by this report."
            )
            subject, body = compose_end("GEM", args.mode, run, when, state, summary, 0)
        response = send_email(settings, subject, body)
        status = response.get("status", "FAILED_OR_UNKNOWN")
        if status != "submitted_not_delivered":
            raise EmailSendError("Gmail did not acknowledge GEM notice")
        code = 0
    except (EmailSetupError, EmailSendError, OSError, ValueError) as exc:
        status = "FAILED_OR_UNKNOWN"
        code = 2
        error_type = type(exc).__name__
        print(f"GEM {args.event} notice unavailable: {error_type}")
    audit = {
        "event": args.event, "scan": "GEM", "mode": args.mode,
        "run_id": run, "at_utc": when.isoformat(), "status": status,
        "note": "SMTP acknowledgment does not prove inbox delivery",
    }
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    file = args.audit_dir / f"gem_email_{run}_{args.event.lower()}.json"
    file.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
