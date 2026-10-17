"""Read-only full-history PDUFA Gmail section audit, reusing hardened 100-UID paging.

This audits mailbox headers only; no messages are marked read, sent, archived,
deleted or moved. Never print credentials or email subject lines in public CI.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts import adhoc_alert_check

FOLDERS = {
    "INBOX": ('INBOX',),
    "SENT_MAIL": ('"[Gmail]/Sent Mail"',),
    "PDUFA": ('"PDUFA"',),
    "SCAN_START": ('"PDUFA/Scan START"',),
    "SCAN_END": ('"PDUFA/Scan END"',),
    "SCAN_ERROR": ('"PDUFA/Scan ERROR"',),
    "DAILY_REPORT": ('"PDUFA/Daily Report"',),
    "WEEKLY_REPORT": ('"PDUFA/Weekly Report"',),
}
FOLDERS["ALL"] = tuple(dict.fromkeys(('"[Gmail]/All Mail"',) + tuple(folder for group in FOLDERS.values() for folder in group)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=sorted(FOLDERS), required=True)
    parser.add_argument("--output", default="reports/gmail_section_audit.json")
    options = parser.parse_args()

    # No truncation to 36h: scan the selected PDUFA-related Gmail folders'
    # complete available history, in bounded 100-message header batches.
    adhoc_alert_check.GMAIL_FOLDERS = FOLDERS[options.section]
    checked = adhoc_alert_check.audit_gmail(
        os.getenv("PDUFA_GMAIL_USER", ""),
        os.getenv("PDUFA_GMAIL_APP_PASSWORD", ""),
        datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    result = {
        "section": options.section,
        "folders_requested": list(FOLDERS[options.section]),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "range": "All available PDUFA-relevant headers since 2000; ALL includes Gmail All Mail and configured PDUFA folders",
        "status": checked.get("status", "UNAVAILABLE"),
        "reason": checked.get("reason", ""),
        "relevant_messages": checked.get("relevant_messages", 0),
        "error_subjects": checked.get("error_subjects", 0),
        "scan_start_subjects": checked.get("scan_start_subjects", 0),
        "scan_end_subjects": checked.get("scan_end_subjects", 0),
        "note": "Read-only header audit only. Counts do not establish per-run START/END delivery. Duplicate messages across labels are deduplicated.",
    }
    target = Path(options.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Gmail section:", options.section)
    print("Audit status:", result["status"])
    print("Relevant PDUFA messages:", result["relevant_messages"])
    print("START:", result["scan_start_subjects"], "END:", result["scan_end_subjects"],
          "error subjects:", result["error_subjects"])
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## PDUFA Gmail section header audit\n\n")
            for k in ("section", "status", "checked_at_utc", "relevant_messages",
                      "scan_start_subjects", "scan_end_subjects", "error_subjects"):
                handle.write("- **" + k.replace("_", " ").title() + ":** " + str(result[k]) + "\n")
            if result["reason"]:
                handle.write("- **Audit gap:** " + str(result["reason"])[:1000] + "\n")
            handle.write("\nRead-only 100-message batches; no Gmail messages were modified. "
                         "Email counts are not delivery proofs.\n")
    return 0 if result["status"] == "CHECKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
