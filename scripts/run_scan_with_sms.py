#!/usr/bin/env python3
"""Mandatory two-SMS wrapper for any #2/#3/#4 or additional PDUFA collector.

No scanner is scheduled here. Invoke each scan through this wrapper only after
configured SMS credentials are available. It refuses to start work unless the
START text is acknowledged and always attempts an END text with an honest
summary after the child terminates (including nonzero exit).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.scan_sms import (SMSSettings, SMSSetupError, SMSSendError,
                              begin_text, finish_text, submit_sms, summarize_report)


def stamp():
    return datetime.now(timezone.utc)


def _metadata(path: Path):
    try:
        record = path.stat()
        return record.st_mtime_ns, record.st_size
    except OSError:
        return None


def _fresh_report(path: Path, old_metadata):
    # A previously saved result must never masquerade as this run's result.
    if _metadata(path) == old_metadata:
        return {}, False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            return {}, False
        return report, True
    except (OSError, ValueError, UnicodeError):
        return {}, False


def _save_audit(audit_dir: Path, run_id: str, info: dict):
    audit_dir.mkdir(parents=True, exist_ok=True)
    dest = audit_dir / f"{run_id}.json"
    temp = dest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    temp.replace(dest)


def run_scan(*, scan: str, mode: str, command: list[str],
             status_file: Path, audit_dir: Path,
             settings: SMSSettings | None = None,
             sender: Callable = submit_sms,
             executor: Callable = subprocess.run,
             now: Callable = stamp, monotonic: Callable = time.monotonic,
             cwd: Path | None = None) -> tuple[int, dict]:
    if not re.fullmatch(r"[A-Za-z0-9 _-]{1,40}", scan):
        raise ValueError("Invalid scan ID")
    if mode not in {"BASELINE", "DELTA", "DEEP", "RECONCILE", "MANUAL"}:
        raise ValueError("Invalid scan mode")
    if not command or command[0] == "--":
        raise ValueError("An executable command is required")
    # No work begins if this is absent; alerts are mandatory, not best effort.
    settings = settings if settings is not None else SMSSettings.from_env()
    run_id = str(uuid.uuid4())
    started = now()
    clock_start = monotonic()
    previous_report = _metadata(status_file)
    audit = {
        "run_id": run_id,
        "scan": scan,
        "mode": mode,
        "started_at_utc": started.isoformat(),
        "sms_policy": "START_THEN_FINAL_SUMMARY",
        "start_sms": "PENDING",
        "end_sms": "PENDING",
        "scan_executed": False,
        "coverage_status": "NOT_STARTED",
    }
    try:
        start_result = sender(settings, begin_text(scan, mode, run_id, started))
        audit["start_sms"] = start_result["status"]
        audit["start_provider_message_id"] = start_result.get("provider_message_id")
        if audit["start_sms"] != "submitted_not_delivered":
            raise SMSSendError("SMS sender did not acknowledge the start text")
    except (SMSSendError, OSError, ValueError, KeyError) as exc:
        audit["start_sms"] = "FAILED_OR_UNKNOWN"
        audit["end_sms"] = "NOT_SENT_SCAN_NOT_STARTED"
        audit["configuration_or_delivery_error"] = type(exc).__name__
        _save_audit(audit_dir, run_id, audit)
        return 4, audit

    exit_code = 1
    exception_type = None
    try:
        audit["scan_executed"] = True
        completed = executor(command, cwd=cwd, check=False)
        exit_code = int(completed.returncode)
    except (Exception, KeyboardInterrupt) as exc:
        exception_type = type(exc).__name__
        exit_code = 1
    finally:
        finished = now()
        duration = max(0, monotonic() - clock_start)
        report, fresh = _fresh_report(status_file, previous_report)
        status, details = summarize_report(report, exit_code, fresh)
        if exception_type:
            details = (details + f"; {exception_type}").strip("; ")
        audit.update({
            "finished_at_utc": finished.isoformat(),
            "duration_seconds": round(duration, 1),
            "scan_exit_code": exit_code,
            "coverage_status": status,
            "summary": details,
            "fresh_status_report": fresh,
        })
        try:
            final = sender(settings, finish_text(
                scan, mode, run_id, status, details, duration))
            audit["end_sms"] = final["status"]
            audit["end_provider_message_id"] = final.get("provider_message_id")
            if audit["end_sms"] != "submitted_not_delivered":
                audit["end_sms"] = "FAILED_OR_UNKNOWN"
        except (SMSSendError, OSError, ValueError, KeyError) as exc:
            audit["end_sms"] = "FAILED_OR_UNKNOWN"
            audit["end_sms_error"] = type(exc).__name__
        _save_audit(audit_dir, run_id, audit)
    # An unverified scan or a failed SMS is not a successful scan run.
    if audit["end_sms"] != "submitted_not_delivered":
        return 4, audit
    if exit_code != 0:
        return exit_code, audit
    return (0 if audit["coverage_status"] == "COMPLETE" else 3), audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scan", required=True, help="2, 3, 4, or another named scan")
    p.add_argument("--mode", required=True,
                   choices=("BASELINE", "DELTA", "DEEP", "RECONCILE", "MANUAL"))
    p.add_argument("--status-file", required=True, type=Path,
                   help="JSON coverage status rewritten by the scanner")
    p.add_argument("--audit-dir", type=Path,
                   default=Path("reports") / "scan_notifications")
    p.add_argument("--cwd", type=Path, default=Path.cwd())
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="Scanner command following --, e.g. -- python script.py")
    options = p.parse_args()
    command = options.command[1:] if options.command[:1] == ["--"] else options.command
    if not command:
        p.error("A scanner command is required after --")
    try:
        result_code, audit = run_scan(
            scan=options.scan, mode=options.mode,
            command=command, status_file=options.status_file,
            audit_dir=options.audit_dir, cwd=options.cwd)
    except (SMSSetupError, ValueError) as exc:
        print(f"Scan blocked before launch: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "run_id": audit["run_id"],
        "scan": audit["scan"],
        "coverage_status": audit["coverage_status"],
        "start_sms": audit["start_sms"],
        "end_sms": audit["end_sms"],
        "summary": audit.get("summary", ""),
    }, indent=2))
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
