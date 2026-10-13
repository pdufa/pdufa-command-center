"""Compare sequential published source audits without confusing checks with jobs.

Invoked ONLY after checkout of latest main, before a new reconciled audit is
committed. Older overlapping scans never replace a newer published report.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

KEYS = ("event_key", "category", "claim")
CLOSED = {"VERIFIED", "NOT_APPLICABLE"}
MAX_HISTORY = 30


def _instant(raw):
    try:
        value = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
        return value.astimezone(timezone.utc) if value.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def _issues(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if any(not all(row.get(key) for key in KEYS) for row in rows):
        raise ValueError("Review queue lacks required event/category/claim identity")
    if any(row.get("verification_required") != "YES" or
           row.get("verification_status") in CLOSED for row in rows):
        raise ValueError("Review queue contains a nonmandatory or resolved item")
    mapping = {tuple(row[k] for k in KEYS): row for row in rows}
    if len(mapping) != len(rows):
        raise ValueError("Duplicate review item identity")
    return mapping


def _snapshot(report):
    return {"run_id": str(report.get("latest_run_id") or ""),
            "checked_at_utc": str(report.get("source_checked_at_utc") or ""),
            "remaining": report.get("required_findings_unresolved"),
            "required": report.get("required_findings_due"),
            "status": report.get("status", "UNKNOWN")}


def _sample(keys, rows, limit=12):
    return [{"event_key": key[0], "ticker": rows[key].get("ticker", ""),
             "category": key[1], "claim": key[2]}
            for key in sorted(keys)[:limit]]


def compare(prior_report, prior_rows, incoming_report, incoming_rows):
    """Pure audit reconciliation. Return action, updated report.

    Never infer 'verified' from a disappearing record if scope has changed.
    """
    fresh_time = _instant(incoming_report.get("source_checked_at_utc"))
    if fresh_time is None:
        raise ValueError("Incoming report does not have a valid checked timestamp")
    if not str(incoming_report.get("latest_run_id", "")).isdigit():
        raise ValueError("Incoming report lacks GitHub run identity")
    if len(incoming_rows) != int(incoming_report["required_findings_unresolved"]):
        raise ValueError("Incoming review queue does not match published mandatory gap count")
    out = dict(incoming_report)
    if not prior_report:
        out["comparison"] = {"available": False, "reason": "No previously published audit"}
        out["verification_history"] = [_snapshot(out)]
        return "PUBLISH", out
    previous_time = _instant(prior_report.get("source_checked_at_utc"))
    if previous_time and fresh_time <= previous_time:
        return "SKIP_STALE", None

    try:
        old_count = int(prior_report["required_findings_unresolved"])
    except (KeyError, ValueError, TypeError):
        old_count = -1
    comparable = (old_count >= 0 and len(prior_rows) == old_count
                  and bool(prior_report.get("verification_scope_sha256"))
                  and prior_report.get("verification_scope_sha256") ==
                  incoming_report.get("verification_scope_sha256"))
    if comparable:
        before = set(prior_rows)
        after = set(incoming_rows)
        resolved, added, persisted = before - after, after - before, before & after
        changed = [key for key in persisted if
                   prior_rows[key]["verification_status"] != incoming_rows[key]["verification_status"]]
        out["comparison"] = {
            "available": True,
            "previous_run_id": str(prior_report.get("latest_run_id") or ""),
            "previous_remaining": old_count,
            "resolved_count": len(resolved),
            "new_count": len(added),
            "still_unresolved_count": len(persisted),
            "status_changed_count": len(changed),
            "net_reduction": old_count - len(incoming_rows),
            "resolved_examples": _sample(resolved, prior_rows),
            "new_examples": _sample(added, incoming_rows),
        }
    else:
        out["comparison"] = {
            "available": False,
            "reason": "Prior issue queue unavailable, inconsistent or event scope changed",
            "previous_run_id": str(prior_report.get("latest_run_id") or ""),
        }
    history = list(prior_report.get("verification_history") or [])
    if not all(isinstance(row, dict) for row in history):
        history = []
    prior = _snapshot(prior_report)
    if not history or history[-1].get("run_id") != prior["run_id"]:
        history.append(prior)
    fresh = _snapshot(out)
    history = [row for row in history if row.get("run_id") != fresh["run_id"]]
    out["verification_history"] = (history + [fresh])[-MAX_HISTORY:]
    return "PUBLISH", out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-report", type=Path, required=True)
    parser.add_argument("--prior-queue", type=Path, required=True)
    parser.add_argument("--incoming-report", type=Path, required=True)
    parser.add_argument("--incoming-queue", type=Path, required=True)
    args = parser.parse_args()

    incoming = json.loads(args.incoming_report.read_text(encoding="utf-8"))
    current_queue = _issues(args.incoming_queue)
    if args.prior_report.is_file():
        previous = json.loads(args.prior_report.read_text(encoding="utf-8"))
        prior_queue = _issues(args.prior_queue) if args.prior_queue.is_file() else {}
    else:
        previous, prior_queue = {}, {}

    action, result = compare(previous, prior_queue, incoming, current_queue)
    if action == "SKIP_STALE":
        print("STALE_SOURCE_AUDIT: incoming checked time is not newer; keep latest published main")
        raise SystemExit(3)
    args.incoming_report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    comp = result["comparison"]
    print(json.dumps({"action": action, "current": incoming["required_findings_unresolved"],
                      "comparison": comp}))


if __name__ == "__main__":
    main()
