"""Gmail SMTP notification transport for PDUFA scans.

A ChatGPT Gmail connection does not grant GitHub Actions SMTP access. Use
GitHub Actions secrets; never commit or log the app password.
"""
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
DASHBOARD = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/"


class EmailSetupError(RuntimeError):
    pass


class EmailSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailSettings:
    sender: str
    app_password: str
    recipient: str

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        sender = str(env.get("PDUFA_GMAIL_USER", "")).strip()
        password = str(env.get("PDUFA_GMAIL_APP_PASSWORD", "")).replace(" ", "").strip()
        recipient = str(env.get("PDUFA_ALERT_EMAIL", "")).strip()
        if not (sender and password and recipient):
            raise EmailSetupError("Gmail sender, app password, or recipient secret is missing")
        if not sender.lower().endswith(("@gmail.com", "@googlemail.com")):
            raise EmailSetupError("This transport requires a Gmail sender")
        for address in (sender, recipient):
            if not re.fullmatch(r"[^\s@,;<>]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", address):
                raise EmailSetupError("Invalid sender or recipient email address")
        return cls(sender, password, recipient)


def label(scan):
    return {"2": "#2 PIPELINE", "3": "#3 PRE3",
            "4": "#4 POST3", "ALL": "#2/#3/#4"}.get(str(scan).upper(), str(scan)[:36])


def when_pacific(when: datetime):
    return when.astimezone(PACIFIC).strftime("%Y-%m-%d %I:%M:%S %p %Z")


def compose_start(scan, mode, run_id, at):
    name = label(scan)
    return (
        f"[PDUFA] START - {name} - {mode}",
        f"PDUFA SCAN STARTED\n\nScan: {name}\nMode: {mode}\n"
        f"Started (Pacific): {when_pacific(at)}\nRun ID: {run_id}\n"
        "Status: IN PROGRESS. No results yet.\n\n"
        f"Dashboard: {DASHBOARD}\n"
    )


def compose_end(scan, mode, run_id, at, status, details, seconds):
    name = label(scan)
    return (
        f"[PDUFA] END - {name} - {status}",
        f"PDUFA SCAN FINISHED\n\nScan: {name}\nMode: {mode}\n"
        f"Finished (Pacific): {when_pacific(at)}\nRun ID: {run_id}\n"
        f"Final status: {status}\nElapsed: {max(seconds,0)/60:.1f} minutes\n\n"
        f"RESULTS SUMMARY\n{details}\n\n"
        f"Dashboard: {DASHBOARD}\n"
        "Unverified source items are not counted as confirmed findings.\n"
    )


def report_summary(report, exit_code, fresh, *, full_scope=False):
    if not fresh or not isinstance(report, dict) or not report:
        return ("FAILED" if exit_code else "UNVERIFIED",
                "Fresh scan report unavailable; no verified counts.")
    state = str(report.get("status", "")).upper()
    if state not in {"COMPLETE", "COMPLETE WITH WARNINGS", "PARTIAL", "FAILED"}:
        state = "UNVERIFIED"
    if exit_code and state in {"COMPLETE", "UNVERIFIED"}:
        state = "FAILED"
    elif exit_code and state == "COMPLETE WITH WARNINGS":
        state = "PARTIAL"
    lines = []
    for checked, total, label_text in (
        ("companies_checked", "companies_due", "Companies checked"),
        ("tracked_trials_checked", "tracked_trials_total", "Trials checked"),
        ("events_checked", "events_due", "Events checked"),
    ):
        v = report.get(checked)
        d = report.get(total)
        if isinstance(v, int) and not isinstance(v, bool):
            lines.append(f"{label_text}: {v}/{d}" if isinstance(d, int) else f"{label_text}: {v}")
    for key, label_text in (
        ("new_records", "New records"),
        ("candidate_field_changes", "Changed fields"),
        ("changed_trials_this_execution", "Changed trials"),
        ("companies_with_warnings", "Company warnings"),
        ("tracked_trials_with_warnings", "Trial warnings"),
        ("studies_checked", "Registry studies checked"),
        ("matched_trials", "Exact sponsor matched trials"),
        ("matched_posted_results", "Phase 3 posted results matched"),
        ("market_cap_source_unavailable", "Market cap sources unavailable"),
        ("errors_count", "Errors"),
        ("source_observations", "Source observations"),
        ("source_issue_count", "Sources needing review"),
        ("feeds_checked", "Issuer feeds checked"),
        ("issuer_news_candidates", "News items discovered (unverified)"),
        ("issuer_press_releases_verified", "Issuer releases verified"),
        ("sources_passed", "Source families complete"),
        ("sources_due", "Source families due"),
    ):
        v = report.get(key)
        if isinstance(v, int) and not isinstance(v, bool):
            lines.append(f"{label_text}: {v}")
    errors = report.get("errors")
    if isinstance(errors, list) and errors:
        lines.append(f"Errors: {len(errors)}")
    missing = report.get("missing_required_source_families")
    if isinstance(missing, list) and missing:
        lines.append("Unverified source families: " + ", ".join(map(str, missing[:10])))
    if full_scope and state in {"COMPLETE", "COMPLETE WITH WARNINGS"}:
        if report.get("full_coverage_verified") is not True:
            state = "UNVERIFIED"
            lines.append("Full-source coverage has not been verified.")
    return state, "\n".join(lines) if lines else "No source-verified counts available."


def send_email(settings, subject, body, *, smtp_factory=None):
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = settings.recipient
    message["Subject"] = subject
    message.set_content(body)
    factory = smtp_factory or smtplib.SMTP_SSL
    try:
        with factory("smtp.gmail.com", 465, timeout=25,
                     context=ssl.create_default_context()) as smtp:
            smtp.login(settings.sender, settings.app_password)
            refused = smtp.send_message(message)
            if refused:
                raise EmailSendError("Mail submission refused")
    except Exception as exc:
        # SMTP can accept an email before a network timeout; no automatic retry.
        raise EmailSendError("Mail submission failed or is unconfirmed") from exc
    return {"status": "submitted_not_delivered"}
