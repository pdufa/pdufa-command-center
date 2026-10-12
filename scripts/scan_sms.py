"""Exactly one start and one final-summary SMS submission per scan run.

Requires Twilio credentials supplied as environment secrets. SMS submission
is not proof of handset delivery; all failures are explicit and never silently
reported as successful notifications.
"""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from urllib import parse, request
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
API_HOST = "https://api.twilio.com"
E164 = re.compile(r"^\+[1-9]\d{6,14}$")
SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
SMS_LIMIT = 155  # GSM-7 single segment; all composed texts use ASCII.


class SMSSetupError(RuntimeError):
    """No valid SMS provider configuration: refuse to begin the scan."""


class SMSSendError(RuntimeError):
    """SMS was not confirmed submitted; do not retry an ambiguous request."""


@dataclass(frozen=True)
class SMSSettings:
    account_sid: str
    auth_token: str
    sender: str
    recipient: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None):
        e = os.environ if env is None else env
        keys = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                "TWILIO_FROM_NUMBER", "PDUFA_SMS_TO_NUMBER")
        values = [str(e.get(key, "")).strip() for key in keys]
        if not all(values):
            raise SMSSetupError("SMS not configured: missing required Twilio/recipient environment secrets")
        account_sid, auth_token, sender, recipient = values
        if not SID.fullmatch(account_sid) or not E164.fullmatch(sender) or not E164.fullmatch(recipient):
            raise SMSSetupError("Invalid Twilio account SID or E.164 sender/recipient number")
        if sender == recipient:
            raise SMSSetupError("SMS sender and recipient must be different")
        return cls(account_sid, auth_token, sender, recipient)


def safe_label(value: str, limit: int = 24) -> str:
    cleaned = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(value))
    return " ".join(cleaned.split())[:limit]


def single_sms(message: str) -> str:
    """Do not unintentionally cause multiple SMS segments for one notification."""
    cleaned = safe_label(message, 1000)
    return cleaned if len(cleaned) <= SMS_LIMIT else cleaned[: SMS_LIMIT - 3].rstrip() + "..."


def local_clock(when: datetime) -> str:
    return when.astimezone(PACIFIC).strftime("%m/%d %I:%M%p PT")


SCAN_NAMES = {
    "2": "#2 PIPELINE",
    "3": "#3 PRE3",
    "4": "#4 POST3",
    "ALL": "#2/#3/#4",
}
STATUS_NAMES = {
    "COMPLETE": "COMPLETE",
    "COMPLETE WITH WARNINGS": "WARNINGS",
    "PARTIAL": "PARTIAL",
    "FAILED": "FAILED",
    "UNVERIFIED": "UNVERIFIED",
}


def begin_text(scan: str, mode: str, run_id: str, at: datetime) -> str:
    label = SCAN_NAMES.get(scan.upper(), scan)
    return single_sms(
        f"PDUFA {safe_label(label)} {safe_label(mode)} START {local_clock(at)}. "
        f"Run {run_id[:8]}. Scanning now; results pending."
    )


def finish_text(scan: str, mode: str, run_id: str, status: str,
                details: str, duration_seconds: float) -> str:
    label = SCAN_NAMES.get(scan.upper(), scan)
    status_label = STATUS_NAMES.get(status, "UNVERIFIED")
    elapsed = max(0, round(duration_seconds / 60))
    return single_sms(
        f"PDUFA {safe_label(label)} {safe_label(mode)} END: {status_label}. "
        f"{safe_label(details, 85)}. {elapsed}m. Run {run_id[:8]}."
    )


def summarize_report(report: dict, run_code: int, fresh: bool) -> tuple[str, str]:
    """Extract trustworthy counts; no old-file-as-new, and no made-up zero counts."""
    if not fresh or not isinstance(report, dict) or not report:
        return ("FAILED" if run_code else "UNVERIFIED",
                "No fresh verified result summary")
    state = str(report.get("status", "")).upper().strip()
    allowed = {"COMPLETE", "COMPLETE WITH WARNINGS", "PARTIAL", "FAILED"}
    state = state if state in allowed else "UNVERIFIED"
    if run_code != 0 and state in ("COMPLETE", "UNVERIFIED"):
        state = "FAILED"
    elif run_code != 0 and state == "COMPLETE WITH WARNINGS":
        state = "PARTIAL"
    fields = [
        ("companies_checked", "companies_due", "companies"),
        ("tracked_trials_checked", "tracked_trials_total", "trials"),
        ("events_checked", "events_due", "events"),
    ]
    details = []
    for checked, due, label in fields:
        have = report.get(checked)
        total = report.get(due)
        if isinstance(have, int) and not isinstance(have, bool):
            details.append(f"{label} {have}/{total}" if isinstance(total, int) else f"{label} {have}")
            break
    for key, label in (
        ("new_records", "new"), ("changed_trials_this_execution", "changed"),
        ("companies_with_warnings", "warnings"),
        ("tracked_trials_with_warnings", "trial warnings"),
        ("errors_count", "errors"),
    ):
        value = report.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            details.append(f"{label} {value}")
    if isinstance(report.get("errors"), list) and report["errors"]:
        details.append(f"errors {len(report['errors'])}")
    missing = report.get("missing_required_source_families")
    if isinstance(missing, list) and missing:
        details.append(f"missing sources {len(missing)}")
    return state, "; ".join(details) if details else "No verified counts available"


def submit_sms(settings: SMSSettings, message: str, *, opener=None) -> dict:
    """Submit once to Twilio. No retry after timeout/unknown response."""
    if len(message) > SMS_LIMIT or not message.isascii():
        raise ValueError("SMS must be ASCII and no longer than one text segment")
    endpoint = f"{API_HOST}/2010-04-01/Accounts/{settings.account_sid}/Messages.json"
    body = parse.urlencode({
        "To": settings.recipient,
        "From": settings.sender,
        "Body": message,
    }).encode("ascii")
    authentication = base64.b64encode(
        f"{settings.account_sid}:{settings.auth_token}".encode("ascii")
    ).decode("ascii")
    req = request.Request(endpoint, data=body, method="POST", headers={
        "Authorization": "Basic " + authentication,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    opener = opener or request.urlopen
    try:
        with opener(req, timeout=20) as resp:
            response = json.loads(resp.read().decode("utf-8"))
            code = resp.status
    except Exception as exc:
        # This may be an ambiguous network response after Twilio accepted it:
        # never attempt a second submission.
        raise SMSSendError("SMS submission failed or returned unknown status") from exc
    message_sid = str(response.get("sid", ""))
    if code not in (200, 201) or not message_sid.startswith("SM"):
        raise SMSSendError("SMS provider did not acknowledge a message")
    return {"status": "submitted_not_delivered", "provider_message_id": message_sid}
