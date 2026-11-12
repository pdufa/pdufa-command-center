#!/usr/bin/env python3
"""Read-only, once-per-accepted-level email notifier for PDUFA Levels 4-20.

Only externally reviewed levels in the strict sequence ledger are eligible.
Never emails on draft PR creation, test passage, or an unreviewed checkpoint.
Configuration stays on the owner's PC; secrets are not written to GitHub.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import json
import os
from pathlib import Path
import re
import smtplib
import sys

from pdufa_strict_level_runner import load_sequence, DATA, MONITOR_ISSUE, REPO
from pdufa_level_completion import safe_json

STATE = DATA / "level_accepted_email_state.json"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,30}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
GITHUB_COMMENT = re.compile(
    r"https://github\.com/pdufa/pdufa-command-center/issues/1096#issuecomment-[0-9]+\Z"
)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def mailbox(text: object) -> str:
    if not isinstance(text, str) or len(text) > 254 or "\n" in text or "\r" in text:
        raise ValueError("Invalid email address")
    display, address = parseaddr(text)
    if display or address != text or not EMAIL_RE.fullmatch(text):
        raise ValueError("Email address must be a single mailbox")
    return address

def config(env: dict | None = None) -> tuple[str, str, str] | None:
    e = os.environ if env is None else env
    user = e.get("PDUFA_GMAIL_USER")
    pwd = e.get("PDUFA_GMAIL_APP_PASSWORD")
    dest = e.get("PDUFA_ALERT_EMAIL")
    if not user or not pwd or not dest:
        return None
    if not isinstance(pwd, str) or not 8 <= len(pwd) <= 256 or "\n" in pwd or "\r" in pwd:
        raise ValueError("Gmail credential appears invalid")
    return mailbox(user), pwd, mailbox(dest)

def accepted_events(seq: dict) -> list[dict]:
    rows = seq.get("accepted_levels")
    if not isinstance(rows, list) or len(rows) > 17:
        raise ValueError("Invalid independent acceptance sequence")
    events = []
    for idx, item in enumerate(rows):
        lvl = idx + 4
        users = item.get("verified_reviewers", [])
        urls = item.get("review_comment_urls", [])
        digest = item.get("review_evidence_sha256")
        if (item.get("level") != lvl or type(lvl) is not int
                or not isinstance(digest, str) or not SHA_RE.fullmatch(digest)
                or not isinstance(users, list) or len(users) != 2
                or any(not isinstance(x, str) or not x for x in users)
                or len({x.lower() for x in users}) != 2
                or not isinstance(urls, list) or len(urls) != 2
                or any(not isinstance(url, str) or not GITHUB_COMMENT.fullmatch(url)
                       for url in urls)
                or not isinstance(item.get("verified_utc"), str)):
            raise ValueError("Level lacks independently reviewed acceptance evidence")
        events.append({"level": lvl, "sha256": digest, "reviewers": users,
                       "approved_utc": item["verified_utc"], "review_comment_urls": urls})
    return events

def load_state() -> dict:
    if not STATE.exists():
        return {"schema_version": 1, "sent": {}, "last_error": None,
                "last_checked_utc": None}
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1 or not isinstance(data.get("sent"), dict)
            or any(not re.fullmatch(r"(?:[4-9]|1[0-9]|20)", str(k))
                   or not SHA_RE.fullmatch(str(v.get("sha256", "")))
                   for k, v in data["sent"].items())):
        raise ValueError("Invalid persisted email delivery ledger")
    return data

def message(event: dict, recipient: str, sender: str) -> EmailMessage:
    n = event["level"]
    completed = n == 20
    next_step = "All Levels 4-20 have independently accepted reviews." if completed else (
        f"Level {n+1} is now eligible to begin."
    )
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"PDUFA Level {n} independently accepted — " + (
        "Levels 4–20 complete" if completed else f"Level {n+1} next"
    )
    msg.set_content(
        f"PDUFA Level {n} has passed its external scientific and code review gates.\n\n"
        f"Verified acceptance time: {event['approved_utc']}\n"
        f"Approved evidence SHA-256: {event['sha256']}\n"
        f"Distinct reviewers: {', '.join(event['reviewers'])}\n"
        f"Next: {next_step}\n\n"
        f"Live monitor: https://github.com/{REPO}/issues/{MONITOR_ISSUE}\n\n"
        "This confirms the documented scientific acceptance checkpoint only. "
        "It does not authorize merges, deployments, published FDA predictions, or trades.\n"
    )
    return msg

def smtp_send(msg: EmailMessage, user: str, pwd: str, *, smtp_factory=smtplib.SMTP_SSL) -> None:
    with smtp_factory(SMTP_SERVER, SMTP_PORT, timeout=25) as client:
        client.login(user, pwd)
        client.send_message(msg)

def process(*, events: list[dict] | None = None, credentials: tuple[str, str, str] | None = None,
            send=smtp_send) -> dict:
    events = accepted_events(load_sequence()) if events is None else events
    state = load_state()
    credentials = config() if credentials is None else credentials
    sent_now = 0
    pending = 0
    for event in events:
        key = str(event["level"])
        prior = state["sent"].get(key)
        if prior:
            if prior.get("sha256") != event["sha256"]:
                raise ValueError("Accepted evidence changed after notification")
            continue
        if credentials is None:
            pending += 1
            continue
        user, pwd, recipient = credentials
        msg = message(event, mailbox(recipient), mailbox(user))
        try:
            send(msg, user, pwd)
        except (OSError, smtplib.SMTPException, TimeoutError) as exc:
            # Do not publish SMTP credentials, email addresses, or exception details.
            state["last_error"] = type(exc).__name__
            state["last_checked_utc"] = stamp()
            safe_json(STATE, state)
            pending += 1
            continue
        state["sent"][key] = {"sha256": event["sha256"], "sent_utc": stamp()}
        state["last_error"] = None
        state["last_checked_utc"] = stamp()
        safe_json(STATE, state)
        sent_now += 1
    state["last_checked_utc"] = stamp()
    if credentials is None and pending:
        state["last_error"] = "LOCAL_GMAIL_CONFIGURATION_MISSING"
    safe_json(STATE, state)
    return {"accepted_levels": len(events), "sent_now": sent_now, "pending": pending,
            "total_sent": len(state["sent"]), "last_error": state.get("last_error"),
            "next_event": "NEXT_INDEPENDENT_LEVEL_ACCEPTANCE"}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    flags = p.add_mutually_exclusive_group(required=True)
    flags.add_argument("--once", action="store_true")
    flags.add_argument("--status", action="store_true")
    flags.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    try:
        if args.self_test:
            assert len(accepted_events({"accepted_levels": []})) == 0
            assert config({}) is None
            assert mailbox("example@example.org") == "example@example.org"
            print("PASS: independent-acceptance-only email gate")
            return 0
        if args.status:
            accepted = accepted_events(load_sequence())
            state = load_state()
            print(json.dumps({
                "accepted_levels": len(accepted),
                "notified_levels": len(state["sent"]),
                "email_configured": config() is not None,
                "pending_notifications": len(accepted) - len(state["sent"]),
                "last_error": state.get("last_error")
            }, indent=2))
            return 0
        print(json.dumps(process(), indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print("PDUFA_LEVEL_EMAIL_BLOCKED:", type(exc).__name__)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
