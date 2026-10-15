"""Gmail SMTP notification transport for PDUFA scans.

A ChatGPT Gmail connection does not grant GitHub Actions SMTP access. Use
GitHub Actions secrets; never commit or log the app password. After SMTP
acceptance, file each matching PDUFA notification under its Gmail label.
"""
import os
import re
import imaplib
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
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
    return {"2": "PIPELINE — inventory", "3": "PIPELINE — clinical enrichment",
            "4": "GEM JR — Phase 3 readout", "GEM": "GEM — verified research",
            "ALL": "PIPELINE → GEM JR → GEM"}.get(str(scan).upper(), str(scan)[:36])


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


def compose_end(scan, mode, run_id, at, status, details, seconds, *, collector_status=None):
    name = label(scan)
    clinical = collector_status in ("COMPLETE", "COMPLETE WITH WARNINGS") and str(scan) in {"2", "3", "4"}
    subject_status = (f"CLINICAL {collector_status} / OVERALL {status}" if clinical else status)
    collector_line = (f"Clinical collection: {collector_status}\nOverall PDUFA source verification: {status}\n\n"
                      if clinical else "")
    return (
        f"[PDUFA] END - {name} - {subject_status}",
        f"PDUFA SCAN FINISHED\n\nScan: {name}\nMode: {mode}\n"
        f"Finished (Pacific): {when_pacific(at)}\nRun ID: {run_id}\n"
        f"Final status: {status}\nElapsed: {max(seconds,0)/60:.1f} minutes\n\n"
        f"{collector_line}RESULTS SUMMARY\n{details}\n\n"
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
        ("source_technical_failure_count", "Blocked/failed source checks"),
        ("source_review_only_count", "Evidence gaps / review checks"),
        ("findings_verified", "Findings verified"),
        ("findings_due", "Findings checked"),
        ("required_findings_unresolved", "Required findings still unresolved"),
        ("findings_not_applicable", "Findings verified as not applicable"),
        ("optional_findings_unavailable", "Supplemental fields unavailable"),
        ("findings_unresolved", "Unresolved findings"),
        ("findings_conflicted", "Conflicting findings"),
        ("verification_technical_failure_count", "Technical verification failures"),
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
    if report.get("execution_status"):
        lines.insert(0, "Scan execution: " + str(report["execution_status"]))
    if isinstance(errors, list) and errors:
        if isinstance(report.get("errors_count"), int):
            # The count already appears above; these are explanations, not
            # another number of independent errors. Never display "Errors: 4"
            # followed by a contradictory "Errors: 1" in the same email.
            lines.append("Error details: " + "; ".join(str(e)[:180] for e in errors[:3]))
        else:
            lines.append(f"Errors: {len(errors)}")
    breakdown = report.get("source_issue_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        lines.append("Issue categories (source:status = checks):")
        for kind, count in sorted(breakdown.items(), key=lambda item: (-item[1], item[0]))[:12]:
            if isinstance(kind, str) and isinstance(count, int):
                lines.append(f"  {kind[:80]}: {count}")
    samples = report.get("source_issue_examples")
    if isinstance(samples, list) and samples:
        lines.append("Examples requiring review:")
        for row in samples[:6]:
            if isinstance(row, dict):
                ticker = str(row.get("ticker", ""))[:14]
                category = str(row.get("category", ""))[:25]
                status = str(row.get("status", ""))[:65]
                lines.append(f"  {ticker} {category}: {status}")
    sec_counts = report.get("sec_registry_status_counts")
    if isinstance(sec_counts, dict) and sec_counts:
        lines.append("SEC registry access: " + ", ".join(
            f"{name[:45]}={count}" for name, count in
            sorted(sec_counts.items(), key=lambda x: (-x[1], x[0]))[:10]
            if isinstance(count, int)))
    missing = report.get("missing_required_source_families")
    if isinstance(missing, list) and missing:
        lines.append("Unverified source families: " + ", ".join(map(str, missing[:10])))
    verification_examples = report.get("verification_issue_examples")
    if isinstance(verification_examples, list) and verification_examples:
        lines.append("Verification items requiring attention:")
        for row in verification_examples[:6]:
            if isinstance(row, dict):
                lines.append("  " + str(row.get("ticker", ""))[:14] + " " +
                    str(row.get("claim", ""))[:40] + ": " + str(row.get("reason", ""))[:150])
    rejected = report.get("manifest_rejections")
    if isinstance(rejected, dict) and rejected:
        lines.append("Missing/rejected source manifests: " + ", ".join(sorted(rejected)))
    if full_scope and state in {"COMPLETE", "COMPLETE WITH WARNINGS"}:
        if report.get("full_coverage_verified") is not True:
            state = "UNVERIFIED"
            lines.append("Full-source coverage has not been verified.")
    return state, "\n".join(lines) if lines else "No source-verified counts available."


def file_pdufa_notification(settings, message_id, *, imap_factory=None,
                            sleeper=time.sleep):
    """Apply Gmail PDUFA label and remove Inbox on the exact sent message.

    Never change another message by sender/subject searches: the unique
    SMTP Message-ID confines this to the notification just submitted.
    Filing failure never prompts a second SMTP send.
    """
    imap_factory = imap_factory or imaplib.IMAP4_SSL
    client = None
    try:
        client = imap_factory("imap.gmail.com", 993, timeout=15)
        client.login(settings.sender, settings.app_password)
        state, _ = client.select('"[Gmail]/Sent Mail"')
        if state != "OK":
            state, _ = client.select('"[Gmail]/All Mail"')
        if state != "OK":
            return "FILING_NOT_CONFIRMED"
        for attempt in range(5):
            state, matches = client.uid("SEARCH", None, "HEADER",
                                        "Message-ID", message_id)
            ids = matches[0].split() if state == "OK" and matches else []
            if ids:
                # Gmail IMAP supports X-GM-LABELS; use a non-system user label
                # and remove only Inbox, preserving Sent/All Mail and unread.
                uid = ids[-1]
                label_state, _ = client.uid("STORE", uid, "+X-GM-LABELS",
                                            "(PDUFA)")
                if label_state != "OK":
                    return "FILING_NOT_CONFIRMED"
                inbox_state, _ = client.uid("STORE", uid, "-X-GM-LABELS",
                                            r"(\Inbox)")
                return ("PDUFA_LABEL_AND_ARCHIVE_ACCEPTED"
                        if inbox_state == "OK" else "LABEL_APPLIED_ARCHIVE_NOT_CONFIRMED")
            if attempt < 4:
                sleeper(1)
    except (OSError, imaplib.IMAP4.error, TypeError, ValueError):
        return "FILING_NOT_CONFIRMED"
    finally:
        if client is not None:
            try:
                client.logout()
            except (OSError, imaplib.IMAP4.error):
                pass
    return "FILING_NOT_CONFIRMED"

def send_email(settings, subject, body, *, smtp_factory=None):
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = settings.recipient
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()
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
    filing_status = (
        file_pdufa_notification(settings, message["Message-ID"])
        if smtp_factory is None and subject.upper().startswith("[PDUFA]")
        else "NOT_CHECKED_TEST_TRANSPORT_OR_NON_PDUFA"
    )
    return {"status": "submitted_not_delivered",
            "filing_status": filing_status,
            # Compatibility with existing per-scan notification audit fields.
            "inbox_status": filing_status}


