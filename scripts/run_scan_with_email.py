#!/usr/bin/env python3
"""Send start and end Gmail messages around one PDUFA scan run.

No GitHub scan schedule is activated. A Gmail SMTP app password is required as
a private Actions secret; the ChatGPT Gmail connector does not supply it.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.scan_email import (
    EmailSettings, EmailSetupError, EmailSendError,
    compose_start, compose_end, report_summary, send_email
)
from scripts.scan_sms import (SMSSettings, SMSSetupError, SMSSendError,
                              begin_text, finish_text, submit_sms)


def fingerprint(path):
    try:
        stat = path.stat()
        return (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None


def read_updated_report(path, previous):
    state = fingerprint(path)
    if state is None or state == previous:
        return {}, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data, True) if isinstance(data, dict) else ({}, False)
    except (OSError, ValueError, UnicodeError):
        return {}, False


def save_audit(folder, run_id, data):
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (run_id + ".json")
    pending = folder / (run_id + ".json.tmp")
    pending.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    pending.replace(dest)


def run_scan(*, scan, mode, command, status_file, audit_dir,
             settings=None, sender=send_email, executor=subprocess.run,
             timeout_seconds=None, cwd=None, clock=None, timer=None,
             require_sms=False, sms_settings=None, sms_sender=submit_sms):
    if not re.fullmatch(r"[A-Za-z0-9 _-]{1,40}", scan):
        raise ValueError("Invalid scan name")
    if mode not in {"BASELINE", "DELTA", "DEEP", "RECONCILE", "MANUAL"}:
        raise ValueError("Invalid scan mode")
    if not command or command[0] == "--":
        raise ValueError("Scanner command required")
    if timeout_seconds is not None and timeout_seconds < 1:
        raise ValueError("timeout_seconds must be positive")
    settings = settings if settings is not None else EmailSettings.from_env()
    # SMS is opt-in until a real handset delivery test is confirmed. Validate
    # both transports BEFORE a single START notification or any scan begins.
    if require_sms:
        sms_settings = sms_settings if sms_settings is not None else SMSSettings.from_env()
    clock = clock or (lambda: datetime.now(timezone.utc))
    timer = timer or time.monotonic
    run_id = str(uuid.uuid4())
    start = clock()
    timer_start = timer()
    before = fingerprint(status_file)
    audit = {
        "run_id": run_id,
        "scan": scan,
        "mode": mode,
        "started_at_utc": start.isoformat(),
        "scan_executed": False,
        "start_email": "PENDING",
        "end_email": "PENDING",
        "coverage_status": "NOT_STARTED",
        "channel": "EMAIL_AND_SMS" if require_sms else "EMAIL",
        "policy": "START_AND_FINAL_SUMMARY_PER_SCAN",
        "start_sms": "PENDING" if require_sms else "NOT_ENABLED",
        "end_sms": "PENDING" if require_sms else "NOT_ENABLED",
    }
    try:
        subject, body = compose_start(scan, mode, run_id, start)
        response = sender(settings, subject, body)
        audit["start_email"] = response["status"]
        audit["start_inbox"] = response.get("inbox_status", "NOT_CONFIRMED")
        if audit["start_email"] != "submitted_not_delivered":
            raise EmailSendError("Mail provider did not acknowledge START message")
    except Exception as exc:
        audit["start_email"] = "FAILED_OR_UNKNOWN"
        audit["end_email"] = "NOT_SENT_SCAN_NOT_STARTED"
        audit["error_type"] = type(exc).__name__
        save_audit(audit_dir, run_id, audit)
        return 4, audit

    if require_sms:
        try:
            result = sms_sender(sms_settings, begin_text(scan, mode, run_id, start))
            audit["start_sms"] = result["status"]
            audit["start_sms_message_id"] = result.get("provider_message_id")
            if audit["start_sms"] != "submitted_not_delivered":
                raise SMSSendError("Provider did not acknowledge START SMS")
        except Exception as exc:
            # An already-submitted START email needs a matching abort email.
            # Never retry an ambiguous SMS response or execute the scan.
            audit["start_sms"] = "FAILED_OR_UNKNOWN"
            audit["end_sms"] = "NOT_SENT_SCAN_NOT_STARTED"
            audit["scan_executed"] = False
            audit["coverage_status"] = "FAILED"
            audit["error_type"] = type(exc).__name__
            try:
                subject, body = compose_end(
                    scan, mode, run_id, clock(), "FAILED",
                    "SMS START unconfirmed; scan was not launched", 0)
                audit["end_email"] = sender(settings, subject, body)["status"]
            except Exception:
                audit["end_email"] = "FAILED_OR_UNKNOWN"
            save_audit(audit_dir, run_id, audit)
            return 4, audit

    try:
        save_audit(audit_dir, run_id, audit)
    except OSError:
        # One start message was submitted; report the failure rather than
        # starting an unaudited scan.
        audit["coverage_status"] = "FAILED"
        audit["summary"] = "Audit storage unavailable; scan not launched"
        try:
            subject, body = compose_end(
                scan, mode, run_id, clock(), "FAILED", audit["summary"], 0)
            audit["end_email"] = sender(settings, subject, body)["status"]
        except Exception:
            audit["end_email"] = "FAILED_OR_UNKNOWN"
        if require_sms:
            try:
                final = sms_sender(sms_settings, finish_text(
                    scan, mode, run_id, "FAILED", audit["summary"], 0))
                audit["end_sms"] = final["status"]
            except Exception:
                audit["end_sms"] = "FAILED_OR_UNKNOWN"
        return 4, audit

    returncode = 1
    exception_name = None
    try:
        audit["scan_executed"] = True
        kwargs = {"cwd": cwd, "check": False}
        if timeout_seconds is not None:
            kwargs["timeout"] = timeout_seconds
        process = executor(command, **kwargs)
        returncode = int(process.returncode)
    except BaseException as exc:
        exception_name = type(exc).__name__
        returncode = 1
    finally:
        finished = clock()
        duration = max(0.0, timer() - timer_start)
        report, fresh = read_updated_report(status_file, before)
        state, details = report_summary(
            report, returncode, fresh, full_scope=scan.upper() in {"2", "3", "4", "ALL"})
        if exception_name:
            details += "\nScanner error: " + exception_name
        audit.update({
            "scan_exit_code": returncode,
            "finished_at_utc": finished.isoformat(),
            "duration_seconds": round(duration, 1),
            "coverage_status": state,
            "summary": details,
            "fresh_status_report": fresh,
        })
        try:
            subject, body = compose_end(
                scan, mode, run_id, finished, state, details, duration,
                collector_status=(report.get("collector_status")
                                  if report.get("scan_kind") == "CLINICAL_SOURCE_COLLECTION_ONLY"
                                  else None))
            response = sender(settings, subject, body)
            audit["end_email"] = response["status"]
            audit["end_inbox"] = response.get("inbox_status", "NOT_CONFIRMED")
            if audit["end_email"] != "submitted_not_delivered":
                audit["end_email"] = "FAILED_OR_UNKNOWN"
        except Exception as exc:
            audit["end_email"] = "FAILED_OR_UNKNOWN"
            audit["end_error_type"] = type(exc).__name__
        if require_sms:
            try:
                final = sms_sender(sms_settings, finish_text(
                    scan, mode, run_id, state, details, duration))
                audit["end_sms"] = final["status"]
                audit["end_sms_message_id"] = final.get("provider_message_id")
                if audit["end_sms"] != "submitted_not_delivered":
                    audit["end_sms"] = "FAILED_OR_UNKNOWN"
            except Exception as exc:
                audit["end_sms"] = "FAILED_OR_UNKNOWN"
                audit["end_sms_error_type"] = type(exc).__name__
        save_audit(audit_dir, run_id, audit)
    if audit["end_email"] != "submitted_not_delivered" or (require_sms and audit["end_sms"] != "submitted_not_delivered"):
        return 4, audit
    if returncode:
        return returncode, audit
    return (0 if audit["coverage_status"] == "COMPLETE" else 3), audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", required=True)
    parser.add_argument("--mode", choices=["BASELINE", "DELTA", "DEEP",
                                           "RECONCILE", "MANUAL"], required=True)
    parser.add_argument("--status-file", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, default=Path("reports/scan_notifications"))
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--require-sms", action="store_true",
                        help="Require one SMS and one email at START and END; off until SMS delivery is verified")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        code, audit = run_scan(
            scan=args.scan, mode=args.mode, command=command,
            status_file=args.status_file, audit_dir=args.audit_dir,
            timeout_seconds=args.timeout_seconds, cwd=Path.cwd(),
            require_sms=args.require_sms)
    except (EmailSetupError, SMSSetupError, ValueError) as exc:
        print("Scan blocked; notification configuration unavailable: " +
              type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps({
        "status": audit["coverage_status"],
        "start_email": audit["start_email"],
        "end_email": audit["end_email"],
        "start_sms": audit["start_sms"],
        "end_sms": audit["end_sms"],
        "start_inbox": audit.get("start_inbox", "NOT_CONFIRMED"),
        "end_inbox": audit.get("end_inbox", "NOT_CONFIRMED"),
        "summary": audit.get("summary", ""),
    }, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
