"""Safely repair eligible GitHub workflow failures and trash ONLY proven resolved alerts.

Never deletes arbitrary mail, primary-source warnings, START/END notices, or
messages whose precise GitHub run cannot be authenticated. Repairs use the
existing conservative fail-closed classifier; no source scans are auto-rerun.
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr
from pathlib import Path

from scripts.pdufa_auto_repair import decide, RERUN_ALLOWLIST

REPOSITORY = "pdufa/pdufa-command-center"
FAILURE_SUBJECT = re.compile(r"^\[pdufa/pdufa-command-center\]\s+(?:PR )?Run failed:", re.I)
RUN_LINK = re.compile(r"https://github\.com/pdufa/pdufa-command-center/actions/runs/([1-9][0-9]*)\b")
FOLDERS = {
    "ALL": '"[Gmail]/All Mail"',
    "INBOX": "INBOX",
    "SENT_MAIL": '"[Gmail]/Sent Mail"',
    "PDUFA": '"PDUFA"',
    "SCAN_START": '"PDUFA/Scan START"',
    "SCAN_END": '"PDUFA/Scan END"',
    "SCAN_ERROR": '"PDUFA/Scan ERROR"',
    "DAILY_REPORT": '"PDUFA/Daily Report"',
    "WEEKLY_REPORT": '"PDUFA/Weekly Report"',
}
# Does not consume or forward email content to public logs.
MAX_FAILURE_NOTICES = 500
MAX_REPAIR_REQUESTS = 3


def decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except (ValueError, LookupError, UnicodeError):
        return value


def exact_run_ids(body: str) -> set[int]:
    return {int(value) for value in RUN_LINK.findall(body)}


def is_failure_notification(subject: str, sender: str) -> bool:
    addr = parseaddr(sender)[1].lower()
    return bool(FAILURE_SUBJECT.match(decode(subject)) and
                addr in {"notifications@github.com", "noreply@github.com"})


def source_run_valid(run: dict, run_id: int) -> bool:
    return (
        run.get("id") == run_id and
        (run.get("head_repository") or {}).get("full_name") == REPOSITORY and
        isinstance(run.get("name"), str) and bool(run["name"]) and
        run.get("status") == "completed" and
        isinstance(run.get("html_url"), str) and
        run["html_url"] == f"https://github.com/{REPOSITORY}/actions/runs/{run_id}"
    )


def confirmed_fixed(run: dict, run_id: int) -> bool:
    """A failed notification is resolved only when its IDENTICAL run was rerun successfully."""
    return (source_run_valid(run, run_id) and run.get("conclusion") == "success"
            and isinstance(run.get("run_attempt"), int) and run["run_attempt"] >= 2)


def github_json(path: str, token: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}{path}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "pdufa-gmail-safe-repair"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def retrieve_message(client: imaplib.IMAP4_SSL, uid: bytes) -> str | None:
    status, pieces = client.uid("FETCH", uid, "(UID BODY.PEEK[])")
    if status != "OK":
        return None
    for piece in pieces or []:
        if not isinstance(piece, tuple) or len(piece) < 2 or not piece[1]:
            continue
        message = email.message_from_bytes(piece[1])
        plain = message.get_body(preferencelist=("plain",))
        try:
            return plain.get_content() if plain else None
        except (UnicodeError, LookupError):
            return None
    return None


def safe_repair(run_id: int, run: dict, token: str, main_sha: str) -> str:
    """Attempt exactly one approved transient failed-jobs rerun; never issue source scans."""
    if not source_run_valid(run, run_id):
        return "BLOCKED_RUN_IDENTITY"
    if run.get("status") != "completed" or run.get("conclusion") != "failure":
        return "NOT_ELIGIBLE"
    # Cheap fail-closed screening before downloading any private failure logs.
    if (run.get("name") not in RERUN_ALLOWLIST or
            run.get("head_branch") != "main" or
            run.get("head_sha") != main_sha or
            run.get("event") not in {"push", "schedule", "workflow_dispatch"} or
            run.get("run_attempt") != 1):
        return "REQUIRES_MANUAL_REPAIR"
    jobs = github_json(f"/actions/runs/{run_id}/jobs?per_page=100", token).get("jobs", [])
    if not isinstance(jobs, list):
        return "BLOCKED_JOBS"
    cmd = ["gh", "run", "view", str(run_id), "--repo", REPOSITORY, "--log-failed"]
    env = dict(os.environ, GH_TOKEN=token)
    result = subprocess.run(cmd, env=env, text=True, capture_output=True,
                            timeout=35, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return "BLOCKED_FAILURE_LOGS"
    manifest_path = Path("data/step7_live_status.json")
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    action, _ = decide(run, jobs, result.stdout, main_sha, manifest,
                       datetime.now(timezone.utc))
    if action != "rerun":
        return "REQUIRES_MANUAL_REPAIR"
    subprocess.run(["gh", "run", "rerun", str(run_id), "--repo", REPOSITORY, "--failed"],
                   env=env, capture_output=True, text=True, timeout=35, check=True)
    return "RERUN_REQUESTED_NOT_YET_FIXED"


def parse_headers(client: imaplib.IMAP4_SSL, batch: list[bytes]) -> tuple[list[tuple[bytes, str]], bool]:
    status, pieces = client.uid(
        "FETCH", b",".join(batch),
        "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])")
    if status != "OK":
        return [], False
    matched = []
    returned = set()
    for piece in pieces or []:
        if not isinstance(piece, tuple) or len(piece) < 2 or not piece[1]:
            continue
        metadata = piece[0] if isinstance(piece[0], bytes) else b""
        uid = re.search(rb"\bUID\s+(\d+)\b", metadata)
        if not uid or uid.group(1) not in batch or uid.group(1) in returned:
            continue
        returned.add(uid.group(1))
        msg = email.message_from_bytes(piece[1])
        if is_failure_notification(msg.get("Subject", ""), msg.get("From", "")):
            matched.append((uid.group(1), decode(msg.get("Subject", ""))))
    return matched, returned == set(batch)


# Priority always comes from the validated GitHub workflow name, never
# solely from subject claims or email arrival order.
PRIORITY_LABELS = {
    1: "Critical overnight / PIPELINE / GEM JR / GEM scans",
    2: "FDA / SEC / clinical / financial evidence",
    3: "Gmail authentication / notification delivery",
    4: "Dashboard / API / CI / integrations",
    5: "Resolved / superseded / other historical notices",
}


def workflow_priority(name: str) -> int:
    """Operational severity of the actual GitHub workflow."""
    value = str(name).casefold()
    if re.search(r"\b(?:overnight|nightly clinical|pipeline|gem(?:[ -]?jr)?|phase\s*3\s*(?:readout|scan)|sequential scans|clinical scan)\b", value):
        return 1
    if re.search(r"\b(?:fda|sec|financial|financing|clinical evidence|source|filings|evidence|registry|runway)\b", value):
        return 2
    if re.search(r"\b(?:gmail|email|inbox|smtp|imap|notification|delivery)\b", value):
        return 3
    if re.search(r"\b(?:dashboard|api|ci|streamlit|vercel|render|deploy|bootstrap|integration|acceptance|test|validation|frontend|backend)\b", value):
        return 4
    return 5


def notice_priority(run: dict, main_sha: str) -> int:
    """Confirmed resolved retries and superseded main failures are last."""
    if confirmed_fixed(run, run.get("id")):
        return 5
    if (run.get("head_branch") == "main" and run.get("conclusion") == "failure"
            and run.get("head_sha") != main_sha):
        return 5
    return workflow_priority(run.get("name", ""))


def prioritized_queue(items: list[tuple[bytes, int, dict, int]]) -> list[tuple[bytes, int, dict, int]]:
    """Serve highest severity first; newest UID first within a band."""
    return sorted(items, key=lambda item: (item[3], -int(item[0])))


def process_section(section: str, token: str, *, repair: bool = True, trash: bool = True) -> dict:
    priority_stats = {
        str(rank): {
            "label": label, "notices": 0, "repair_requests": 0,
            "confirmed_resolved_trashed": 0, "manual_review_or_pending": 0,
        }
        for rank, label in PRIORITY_LABELS.items()
    }
    result = {
        "section": section, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL", "headers_checked": 0, "failure_notifications": 0,
        "confirmed_resolved_trashed": 0, "repair_requests": 0,
        "pending_or_unresolved": 0, "unmatched_run_reference": 0, "safety_blocks": 0,
        "fetch_errors": 0, "skipped_due_to_limit": 0,
        "processing_priority": list(PRIORITY_LABELS.values()),
        "priority_stats": priority_stats,
        "notes": [
            "Inventory every mailbox header before any repair or cleanup.",
            "Check exact linked GitHub run IDs; process validated notices by severity, not arrival order.",
            "Only transient approved workflow failures are retried. No source scans are automatically rerun.",
            "An email goes to Trash only after the SAME GitHub run succeeds on a later attempt.",
            "Unresolved, unmatched and source-evidence alerts stay visible.",
        ],
    }
    username = os.environ.get("PDUFA_GMAIL_USER", "").strip()
    password = os.environ.get("PDUFA_GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not (username and password and token):
        result["status"] = "BLOCKED_MISSING_CREDENTIALS"
        return result
    main_sha = github_json("/commits/main", token).get("sha", "")
    client = imaplib.IMAP4_SSL("imap.gmail.com", timeout=20)
    try:
        client.login(username, password)
        selected, _ = client.select(FOLDERS[section], readonly=not trash)
        if selected != "OK":
            result["status"] = "FOLDER_UNAVAILABLE"
            return result
        status, matches = client.uid("SEARCH", None, "ALL")
        if status != "OK":
            result["status"] = "SEARCH_FAILED"
            return result
        uids = matches[0].split() if matches and matches[0] else []
        errors = False
        candidates: list[tuple[bytes, str]] = []
        # Pass 1: examine ALL headers in 100-item batches BEFORE touching mail.
        for pos in range(0, len(uids), 100):
            batch = uids[pos:pos + 100]
            found, complete = parse_headers(client, batch)
            result["headers_checked"] += len(batch)
            if not complete:
                errors = True
                result["fetch_errors"] += 1
                continue
            candidates.extend(found)
        result["failure_notifications"] = len(candidates)
        # Bound per-run work but prioritize potential critical messages.
        # Classification from the email SUBJECT is preliminary only; actual
        # repair and cleanup rely on the VERIFIED GitHub run metadata.
        preliminary = sorted(candidates, key=lambda item: (
            workflow_priority(item[1]), -int(item[0])))
        if len(preliminary) > MAX_FAILURE_NOTICES:
            result["skipped_due_to_limit"] = len(preliminary) - MAX_FAILURE_NOTICES
            errors = True
        queue: list[tuple[bytes, int, dict, int]] = []
        run_cache: dict[int, dict] = {}
        # Pass 2: validate exact run metadata for every candidate.
        # Do not mutate emails or initiate reruns during this phase.
        for uid, _ in preliminary[:MAX_FAILURE_NOTICES]:
            body = retrieve_message(client, uid)
            ids = exact_run_ids(body or "")
            if len(ids) != 1:
                result["unmatched_run_reference"] += 1
                continue
            run_id = next(iter(ids))
            if run_id not in run_cache:
                try:
                    run_cache[run_id] = github_json(f"/actions/runs/{run_id}", token)
                except Exception:
                    result["fetch_errors"] += 1
                    errors = True
                    continue
            run = run_cache[run_id]
            if not source_run_valid(run, run_id):
                result["safety_blocks"] += 1
                continue
            queue.append((uid, run_id, run, notice_priority(run, main_sha)))
        repair_attempted: set[int] = set()
        # Pass 3: sequence by VERIFIED severity, processing P1 before P2...
        for uid, run_id, run, rank in prioritized_queue(queue):
            group = priority_stats[str(rank)]
            group["notices"] += 1
            if confirmed_fixed(run, run_id):
                if trash:
                    move_status, _ = client.uid("MOVE", uid, '"[Gmail]/Trash"')
                    if move_status == "OK":
                        result["confirmed_resolved_trashed"] += 1
                        group["confirmed_resolved_trashed"] += 1
                    else:
                        result["fetch_errors"] += 1
                        errors = True
                continue
            result["pending_or_unresolved"] += 1
            group["manual_review_or_pending"] += 1
            if repair and run_id not in repair_attempted and result["repair_requests"] < MAX_REPAIR_REQUESTS:
                repair_attempted.add(run_id)
                try:
                    answer = safe_repair(run_id, run, token, main_sha)
                    if answer == "RERUN_REQUESTED_NOT_YET_FIXED":
                        result["repair_requests"] += 1
                        group["repair_requests"] += 1
                    else:
                        result["safety_blocks"] += 1
                except Exception:
                    result["fetch_errors"] += 1
                    errors = True
        result["status"] = "PARTIAL_ERRORS" if errors else "CHECKED"
    except (imaplib.IMAP4.error, OSError, TimeoutError):
        result["status"] = "MAILBOX_UNAVAILABLE"
    finally:
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=sorted(FOLDERS), required=True)
    parser.add_argument("--output", default="reports/gmail_repair_cleanup.json")
    args = parser.parse_args()
    try:
        result = process_section(args.section, os.environ.get("GITHUB_TOKEN", ""))
    except Exception:
        result = {"section": args.section, "status": "FAILED", "notes": [
            "Cannot confirm current GitHub or Gmail state; no unverified email was intentionally trashed."
        ]}
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("## PDUFA Gmail safe repair & cleanup\n\n")
            for key in ("section", "status", "headers_checked", "failure_notifications",
                        "repair_requests", "confirmed_resolved_trashed", "pending_or_unresolved",
                        "unmatched_run_reference", "safety_blocks", "fetch_errors", "skipped_due_to_limit"):
                output.write(f"- **{key.replace('_',' ').title()}:** {result.get(key, 0)}\n")
            output.write("\n### Priority order (highest first)\n\n")
            for rank, counts in result.get("priority_stats", {}).items():
                output.write(
                    f"- **P{rank} {counts['label']}**: {counts['notices']} notice(s), "
                    f"{counts['repair_requests']} repair requests, "
                    f"{counts['confirmed_resolved_trashed']} verified notices moved to Trash, "
                    f"{counts['manual_review_or_pending']} pending / manual-review.\n"
                )
            output.write("\nOnly independently confirmed resolved failure notifications move to Trash.\n")
    print("Gmail safe-repair status:", result["status"])
    for key in ("failure_notifications", "repair_requests", "confirmed_resolved_trashed",
                "pending_or_unresolved", "safety_blocks", "fetch_errors"):
        print(key + ":", result.get(key, 0))
    return 0 if result["status"] == "CHECKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
