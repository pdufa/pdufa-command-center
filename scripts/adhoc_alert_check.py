"""Read-only ad hoc GitHub/Gmail error audit for the PDUFA Command Center.

Never mutates repository code, email, source evidence or scan schedules.
GitHub Actions saves the report as an artifact rather than overwriting results.
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO = "pdufa/pdufa-command-center"
WORKFLOWS = (
    "pdufa-nightly-clinical.yml",
    "pdufa-nightly-missing-sources.yml",
    "pdufa-nightly-report.yml",
    "ci.yml",
    "step7-live-feed.yml",
    "pdufa-nightly-report-checks.yml",
    "pdufa-overnight-sequential.yml",
    "pdufa-nightly-pacific-start.yml",
    "pdufa-morning-6am-results.yml",
    "pdufa-nightly-scoring-then-repair.yml",
)
SCAN_WORKFLOWS = frozenset(WORKFLOWS[:3] + ("step7-live-feed.yml", "pdufa-overnight-sequential.yml"))
GMAIL_FOLDERS = ("INBOX", '"[Gmail]/Sent Mail"', '"PDUFA"',
                 '"PDUFA/Scan START"', '"PDUFA/Scan END"', '"PDUFA/Scan ERROR"',
                 '"PDUFA/Daily Report"', '"PDUFA/Weekly Report"')
ERROR_SUBJECT = re.compile(r"\b(?:fail(?:ed|ure)?|error|bounce|undeliverable|delivery status notification)\b", re.I)
PDUFA_SUBJECT = re.compile(r"PDUFA|GitHub|workflow|scan", re.I)


SCAN_COMPLETION_WORKFLOWS = frozenset({
    "PDUFA Nightly Clinical Scans",
    "PDUFA Nightly FDA SEC Financial Market Issuer Sources",
    "PDUFA Nightly Scan Report Publisher",
    "Step 7 PRE PHASE 3 Live Feed",
})


def completed_scan_context(token: str, source_run_id: str) -> dict:
    """Tie post-scan audit to its actual completed run, including failures."""
    if not re.fullmatch(r"[1-9][0-9]*", source_run_id):
        raise ValueError("Invalid source scan run identifier")
    run = github_json("/actions/runs/" + source_run_id, token)
    serial = os.environ.get("PDUFA_SERIAL_STAGE_CONCLUSION", "")
    if serial:
        if __package__:
            from .nightly_sequence import completed_source_stage
        else:
            from nightly_sequence import completed_source_stage
        jobs = github_json("/actions/runs/" + source_run_id + "/jobs?per_page=100", token)
        return completed_source_stage(
            run, jobs.get("jobs", []), current_run_id=os.environ.get("GITHUB_RUN_ID", ""),
            conclusion=serial, repository=REPO)
    repository = (run.get("head_repository") or {}).get("full_name")
    if (run.get("name") not in SCAN_COMPLETION_WORKFLOWS
            or repository != REPO or run.get("head_branch") != "main"
            or run.get("status") != "completed"):
        raise ValueError("Source run is not a completed approved PDUFA main-branch scan")
    conclusion = run.get("conclusion")
    return {
        "run_id": run.get("id"),
        "workflow": run.get("name"),
        "conclusion": conclusion,
        "trigger_event": run.get("event"),
        "created_at": run.get("created_at"),
        "completed_at": run.get("updated_at"),
        "url": run.get("html_url"),
        "needs_attention": conclusion != "success",
        "note": "A successful GitHub scan does not prove FDA/SEC/clinical evidence coverage.",
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def github_json(path: str, token: str) -> dict:
    url = "https://api.github.com/repos/" + REPO + path
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pdufa-adhoc-alert-check",
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        return json.load(response)


def current_issue(runs: list[dict]) -> dict | None:
    """Only the newest run for this workflow counts as its current state."""
    if not runs:
        return None
    ordered = sorted(runs, key=lambda r: (r.get("created_at", ""), r.get("id", 0)), reverse=True)
    newest = ordered[0]
    if newest.get("status") != "completed" or newest.get("conclusion") not in ("failure", "timed_out"):
        return None
    return {
        "id": newest.get("id"),
        "status": newest.get("status"),
        "conclusion": newest.get("conclusion"),
        "created_at": newest.get("created_at"),
        "url": newest.get("html_url"),
        "attempt": newest.get("run_attempt"),
        "head_sha": newest.get("head_sha"),
    }


def audit_github(token: str) -> dict:
    observed = {}
    failures = []
    for file in WORKFLOWS:
        response = github_json("/actions/workflows/" + file + "/runs?branch=main&per_page=4", token)
        runs = response.get("workflow_runs", [])
        newest = max(runs, key=lambda r: (r.get("created_at", ""), r.get("id", 0)), default={})
        observed[file] = {
            "run_id": newest.get("id"),
            "status": newest.get("status") or "NOT_SEEN",
            "conclusion": newest.get("conclusion") or "UNKNOWN",
            "created_at": newest.get("created_at"),
            "url": newest.get("html_url"),
        }
        problem = current_issue(runs)
        if problem:
            problem["workflow"] = file
            failures.append(problem)
    return {"status": "ISSUES_FOUND" if failures else "NO_CURRENT_FAILED_RUNS",
            "workflows": observed, "current_failures": failures,
            "note": "Current-run status only; old superseded failure alerts are not current failures."}


def decode_subject(raw: str | None) -> str:
    try:
        return str(make_header(decode_header(raw or "")))
    except (ValueError, UnicodeError, LookupError):
        return str(raw or "")


def filter_headers(items: list[dict], since: datetime) -> dict:
    recent, warning_count, end_count, start_count = 0, 0, 0, 0
    for item in items:
        try:
            date = parsedate_to_datetime(item.get("Date", ""))
            if not date or not date.tzinfo or date.astimezone(timezone.utc) < since:
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        subject = decode_subject(item.get("Subject", ""))
        if not PDUFA_SUBJECT.search(subject):
            continue
        recent += 1
        warning_count += bool(ERROR_SUBJECT.search(subject))
        start_count += bool(re.search(r"\bSTART\b", subject, re.I))
        end_count += bool(re.search(r"\bEND\b", subject, re.I))
    return {"relevant_messages": recent, "error_subjects": warning_count,
            "scan_start_subjects": start_count, "scan_end_subjects": end_count}


def audit_gmail(username: str, password: str, since: datetime) -> dict:
    if not username or not password:
        return {"status": "UNAVAILABLE", "reason": "Gmail IMAP credentials missing; cannot audit Gmail."}
    items, folder_errors = [], []
    seen_messages = set()
    client = None
    try:
        client = imaplib.IMAP4_SSL("imap.gmail.com", timeout=20)
        client.login(username, password)
        # No mail is read-marked, moved, sent or deleted.
        for folder in GMAIL_FOLDERS:
            try:
                status, _ = client.select(folder, readonly=True)
                if status != "OK":
                    raise RuntimeError("Folder not accessible")
                date_clause = since.strftime("%d-%b-%Y")
                status, matches = client.uid("SEARCH", None, "SINCE", date_clause)
                if status != "OK":
                    raise RuntimeError("IMAP search failed")
                # Process the entire 36-hour SEARCH result in bounded batches,
                # not just the newest messages. Fetch headers only, read-only.
                # A missing/malformed response must remain PARTIAL, never PASS.
                uids = matches[0].split() if matches and matches[0] else []
                for offset in range(0, len(uids), 100):
                    batch = uids[offset:offset + 100]
                    expected = set(batch)
                    status, data = client.uid(
                        "FETCH", b",".join(batch),
                        "(UID X-GM-MSGID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])",
                    )
                    if status != "OK":
                        folder_errors.append(folder + " header batch fetch failed")
                        continue
                    returned = set()
                    for entry in (p for p in (data or []) if isinstance(p, tuple)):
                        if len(entry) < 2:
                            folder_errors.append(folder + " malformed header response")
                            continue
                        metadata = entry[0] if isinstance(entry[0], bytes) else b""
                        uid_match = re.search(rb"\bUID\s+(\d+)\b", metadata)
                        if not uid_match or uid_match.group(1) not in expected:
                            folder_errors.append(folder + " unrecognized header UID")
                            continue
                        uid = uid_match.group(1)
                        if uid in returned:
                            folder_errors.append(folder + " duplicate header UID")
                            continue
                        returned.add(uid)
                        if not entry[1]:
                            folder_errors.append(folder + " header unavailable")
                            continue
                        msg = email.message_from_bytes(entry[1])
                        gmail_id = re.search(rb"\bX-GM-MSGID\s+(\d+)", metadata)
                        message_id = str(msg.get("Message-ID", "")).strip()
                        identity = ("gmail:" + gmail_id.group(1).decode("ascii") if gmail_id
                                    else "message-id:" + message_id if message_id else None)
                        if identity is not None:
                            if identity in seen_messages:
                                continue
                            seen_messages.add(identity)
                        items.append(dict(msg.items()))
                    if returned != expected:
                        folder_errors.append(folder + " incomplete header batch")
            except (imaplib.IMAP4.error, RuntimeError, OSError):
                folder_errors.append(folder + " unavailable")
        if folder_errors:
            return {"status": "PARTIAL", "reason": "; ".join(dict.fromkeys(folder_errors)),
                    **filter_headers(items, since)}
        return {"status": "CHECKED", **filter_headers(items, since),
                "note": "Headers only; messages deduplicated across labels by Gmail ID or Message-ID. Counts do not prove delivery or identify a missing END by job ID."}
    except (imaplib.IMAP4.error, OSError, TimeoutError, ValueError) as exc:
        return {"status": "UNAVAILABLE",
                "reason": "Gmail IMAP connection failed (" + type(exc).__name__ + ")."}
    finally:
        if client is not None:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass


def build_report() -> tuple[dict, int]:
    since = now_utc() - timedelta(hours=36)
    report = {
        "generated_at_utc": now_utc().isoformat(),
        "scope": "Read-only ad hoc GitHub and Gmail error audit",
        "lookback_hours": 36,
        "repair": "Eligible GitHub workflow failures have a separate guarded self-repair automation; this check does not make repairs.",
    }
    code = 0
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        if not token:
            raise RuntimeError("GitHub token missing")
        report["github"] = audit_github(token)
        source_run_id = os.environ.get("PDUFA_SOURCE_RUN_ID", "").strip()
        if source_run_id:
            report["source_scan"] = completed_scan_context(token, source_run_id)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError, RuntimeError) as exc:
        report["github"] = {"status": "UNAVAILABLE", "reason": "GitHub API failed (" + type(exc).__name__ + ")."}
        code = 1
    report["gmail"] = audit_gmail(
        os.environ.get("PDUFA_GMAIL_USER", ""),
        os.environ.get("PDUFA_GMAIL_APP_PASSWORD", ""),
        since,
    )
    if report["gmail"]["status"] in ("UNAVAILABLE", "PARTIAL"):
        code = 1
    report["overall"] = (
        "CHECK_INCOMPLETE" if code else
        "ISSUES_FOUND" if (report["github"]["current_failures"]
                           or report["gmail"]["error_subjects"]
                           or report.get("source_scan", {}).get("needs_attention")) else
        "NO_CURRENT_ERRORS_DETECTED"
    )
    return report, code


def main() -> int:
    report, exit_code = build_report()
    target = Path("reports/adhoc_alert_check.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("## Ad Hoc Gmail + GitHub Error Check\n\n")
            fp.write("**Result:** " + report["overall"] + "\n\n")
            for source in ("github", "gmail"):
                info = report[source]
                fp.write("- **" + source.title() + ":** " + info["status"] + "\n")
                if info.get("reason"):
                    fp.write("  - " + info["reason"] + "\n")
            source = report.get("source_scan")
            if source:
                fp.write("- Completed source jobs: " + source["workflow"] +
                         " (run #" + str(source["run_id"]) + ", " +
                         str(source["conclusion"]) + ") — " +
                         str(source["url"]) + "\n")
            for failure in report["github"].get("current_failures", []):
                fp.write("- Unresolved: " + failure["workflow"] + " — " + str(failure.get("url")) + "\n")
            fp.write("\nRead-only audit; an accepted workflow run does not prove source evidence is complete.\n")
    print("Ad hoc audit: " + report["overall"])
    print("GitHub: " + report["github"]["status"] + "; Gmail: " + report["gmail"]["status"])
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

