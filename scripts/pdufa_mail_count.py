"""Count only PDUFA-labelled mail; never select or modify Inbox or read bodies."""
from __future__ import annotations

import argparse
import imaplib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCOPE = "PDUFA_ONLY_EXCLUDING_INBOX_TRASH_SPAM"
QUERY = '"-in:inbox -in:trash -in:spam"'
LIST_ROW = re.compile(rb'\([^)]*\) (?:"(?:[^"\\]|\\.)*"|NIL) ("(?:[^"\\]|\\.)*"|[^\r\n]+)')


def pdufa_folders(rows):
    folders = []
    for row in rows or []:
        if not isinstance(row, bytes):
            raise ValueError("Malformed folder listing")
        match = LIST_ROW.fullmatch(row)
        if not match:
            raise ValueError("Malformed folder listing")
        name = match.group(1)
        if name.startswith(b'"'):
            name = re.sub(rb'\\(.)', rb'\1', name[1:-1])
        # A broad LIST match must never expand the authorized scope.
        if name == b"PDUFA" or name.startswith(b"PDUFA/"):
            if b"\r" in name or b"\n" in name:
                raise ValueError("Unsafe folder name")
            folders.append(name)
    return sorted(set(folders))


def collect(username, password, *, imap_factory=imaplib.IMAP4_SSL):
    result = {"schema_version": 1, "scope": SCOPE, "status": "UNAVAILABLE",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "total_count": None, "unread_count": None,
              "excluded_labels": ["INBOX", "TRASH", "SPAM"], "folders_checked": 0}
    if not username or not password:
        result["reason"] = "Gmail count connection is not configured"
        return result
    client = None
    try:
        client = imap_factory("imap.gmail.com", timeout=20)
        client.login(username, password)
        status, rows = client.list('""', '"PDUFA*"')
        if status != "OK":
            raise ValueError("PDUFA labels unavailable")
        folders = pdufa_folders(rows)
        if not folders:
            raise ValueError("No PDUFA labels found")
        messages = {}
        for folder in folders:
            quoted = b'"' + folder.replace(b"\\", b"\\\\").replace(b'"', b'\\"') + b'"'
            status, _ = client.select(quoted, readonly=True)
            if status != "OK":
                raise ValueError("PDUFA label unavailable")
            status, matches = client.uid("SEARCH", None, "UNDELETED", "X-GM-RAW", QUERY)
            if status != "OK" or not isinstance(matches, list) or len(matches) != 1 or not isinstance(matches[0], bytes):
                raise ValueError("Incomplete count search")
            uids = matches[0].split()
            if any(not uid.isdigit() for uid in uids) or len(set(uids)) != len(uids):
                raise ValueError("Malformed count identities")
            for offset in range(0, len(uids), 100):
                batch = uids[offset:offset + 100]
                status, records = client.uid("FETCH", b",".join(batch), "(UID X-GM-MSGID FLAGS)")
                if status != "OK":
                    raise ValueError("Count metadata unavailable")
                returned = set()
                for entry in records or []:
                    if not isinstance(entry, bytes):
                        raise ValueError("Malformed count metadata")
                    uid = re.search(rb"\bUID\s+(\d+)\b", entry)
                    identity = re.search(rb"\bX-GM-MSGID\s+(\d+)\b", entry)
                    flags = re.search(rb"\bFLAGS\s+\(([^)]*)\)", entry)
                    if not uid or not identity or not flags or uid[1] not in batch or uid[1] in returned:
                        raise ValueError("Incomplete count metadata")
                    returned.add(uid[1])
                    seen = b"\\Seen" in flags[1].split()
                    messages[identity[1]] = messages.get(identity[1], False) or seen
                if returned != set(batch):
                    raise ValueError("Incomplete count batch")
            result["folders_checked"] += 1
        result.update(status="CHECKED", total_count=len(messages),
                      unread_count=sum(not seen for seen in messages.values()))
    except (imaplib.IMAP4.error, OSError, TimeoutError, ValueError, TypeError):
        # Do not expose server responses, labels, credentials or email metadata.
        result["reason"] = "PDUFA-only count could not be completed; no zero count inferred"
    finally:
        if client is not None:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
    result["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/pdufa_mail_count.json")
    args = parser.parse_args()
    result = collect(os.getenv("PDUFA_GMAIL_USER", ""), os.getenv("PDUFA_GMAIL_APP_PASSWORD", ""))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Aggregate counts only. A failed check is also published to avoid stale green.
    print("PDUFA-only email count:", result["status"], "total:", result["total_count"], "unread:", result["unread_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
