"""Fail-closed nightly recovery triage for source conflicts and code failures.

All instructions are diagnostic; existing nightly verification performs source
rechecks, and the existing approved repair tool may retry selected CI jobs.
This module never changes SEC/FDA/Phase-3 evidence, trading entry, or code.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ISSUE_FIELDS = ("event_key", "ticker", "category", "claim",
                "verification_status", "verification_required", "reason",
                "source_url")
REPAIR_TYPES = frozenset({
    "RECHECK_CIK_MATCHED_SEC_FINANCING",
    "RECHECK_ISSUER_FDA_TARGET",
    "RECHECK_SOURCE_FINANCIAL",
    "RECHECK_ISSUER_ANNOUNCEMENT",
    "RECHECK_SOURCE_GENERAL",
    "HOLD_CONFLICT_AND_RECHECK_PRIMARY",
    "RETRY_PROVIDER_NEXT_CYCLE",
    "HOLD_SOURCE_FAILURE",
})


def _safe_str(value, maximum=350):
    return str(value or "").strip()[:maximum]


def classify(row):
    """A conflict can NEVER become VERIFIED through an automatic label."""
    category = _safe_str(row.get("category"), 30).upper()
    claim = _safe_str(row.get("claim"), 70).upper()
    state = _safe_str(row.get("verification_status"), 40).upper()
    reason = _safe_str(row.get("reason"), 450)
    if state == "CONFLICT":
        return "CRITICAL", "HOLD_CONFLICT_AND_RECHECK_PRIMARY", True
    if state == "TECHNICAL_FAILURE":
        return "HIGH", "RETRY_PROVIDER_NEXT_CYCLE", True
    if state not in {"REVIEW_REQUIRED", "UNAVAILABLE"}:
        return "REVIEW", "HOLD_SOURCE_FAILURE", True
    if category == "SEC" and claim == "FINANCING_CLOSURE":
        return "HIGH", "RECHECK_CIK_MATCHED_SEC_FINANCING", True
    if category == "FDA":
        return "HIGH", "RECHECK_ISSUER_FDA_TARGET", True
    if category == "FINANCIAL":
        return "NORMAL", "RECHECK_SOURCE_FINANCIAL", True
    if category == "ISSUER":
        return "NORMAL", "RECHECK_ISSUER_ANNOUNCEMENT", True
    return "NORMAL", "RECHECK_SOURCE_GENERAL", True


def triage_source_rows(rows, source_report=None):
    """Create a one-to-one diagnostic queue; never reduce unresolved count."""
    source_report = source_report if isinstance(source_report, dict) else {}
    findings = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _safe_str(row.get("verification_required")).upper() != "YES":
            continue
        state = _safe_str(row.get("verification_status"), 40).upper()
        if state in {"VERIFIED", "NOT_APPLICABLE"}:
            continue
        identity = tuple(_safe_str(row.get(k), 220) for k in
                         ("event_key", "category", "claim"))
        if identity in seen or not all(identity):
            # Duplicates or missing identifiers must not silently collapse;
            # flag whole triage as INCOMPLETE so callers can show a hold.
            return {"status": "INCOMPLETE_IDENTITY_CONFLICT",
                    "source_report_run_id": _safe_str(source_report.get("latest_run_id")),
                    "findings_count": len(findings),
                    "source_total_expected": source_report.get("required_findings_unresolved"),
                    "counts_by_action": {},
                    "items": findings,
                    "trade_gate_modified": False}
        seen.add(identity)
        urgency, action, blocking = classify(row)
        findings.append({
            "event_key": identity[0],
            "ticker": _safe_str(row.get("ticker"), 30),
            "category": identity[1],
            "claim": identity[2],
            "verification_status": state,
            "priority": urgency,
            "next_scan_action": action,
            "manual_review_if_persistent": blocking,
            "reason": _safe_str(row.get("reason"), 350),
            "source_url": _safe_str(row.get("source_url"), 350),
            "auto_verified": False,
            "gem_trade_entry": "BLOCKED_FROM_THIS_FINDING",
        })
    findings.sort(key=lambda a: (
        {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "REVIEW": 3}.get(a["priority"], 4),
        a["category"], a["ticker"], a["event_key"]))
    expected = source_report.get("required_findings_unresolved")
    valid_expected = type(expected) is int and expected >= 0
    status = ("READY_FOR_NEXT_NIGHT_RECHECK"
              if valid_expected and len(findings) == expected
              else "INCOMPLETE_OR_STALE_QUEUE")
    return {
        "status": status,
        "source_report_run_id": _safe_str(source_report.get("latest_run_id")),
        "source_total_expected": expected if valid_expected else None,
        "findings_count": len(findings),
        "counts_by_action": dict(Counter(x["next_scan_action"] for x in findings)),
        "items": findings,
        "trade_gate_modified": False,
        "note": "Actions name rechecks already supported by the nightly source pipeline; "
                "they are not claims of a successful repair or a source verification.",
    }


def triage_code_failures(alerts, repair_result):
    """Surface current CI failures, even when existing safe repair skips them."""
    alerts = alerts if isinstance(alerts, dict) else {}
    github = alerts.get("github") or {}
    problems = github.get("current_failures", [])
    decisions = repair_result.get("decisions", []) if isinstance(repair_result, dict) else []
    action_by_id = {d.get("run_id"): d for d in decisions if isinstance(d, dict)}
    out = []
    for r in problems if isinstance(problems, list) else []:
        if not isinstance(r, dict) or type(r.get("id")) is not int:
            continue
        decision = action_by_id.get(r["id"], {})
        action = _safe_str(decision.get("action", "skip"), 30)
        out.append({
            "run_id": r["id"],
            "workflow": _safe_str(r.get("workflow"), 120),
            "auto_repair": ("ONE_FAILED_JOB_RETRY_REQUESTED"
                            if action == "rerun_requested"
                            else "DIAGNOSIS_ONLY_MANUAL_CODE_REVIEW"),
            "explanation": _safe_str(decision.get("reason"), 350),
            "code_changed": False,
            "trade_gate_modified": False,
        })
    return out


def build_report(queue_rows, source_report, alerts=None, repair_result=None,
                 source_run_id=None):
    base = triage_source_rows(queue_rows, source_report)
    source_run = _safe_str(source_run_id)
    published_id = _safe_str(source_report.get("latest_run_id"))
    # If the associated source run has not yet published the verified queue,
    # explain that triage is from the previous snapshot, never a fresh audit.
    matching = bool(source_run and published_id and source_run == published_id)
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_id": source_run,
        "source_report_run_id": published_id,
        "source_snapshot_matches_current_run": matching,
        "queue_status": (base["status"] if matching
                          else "PREVIOUS_SNAPSHOT_PENDING_SOURCE_PUBLICATION"),
        "unresolved_findings": base["findings_count"],
        "expected_unresolved_findings": base["source_total_expected"],
        "next_scan_actions": base["counts_by_action"],
        "source_items": base["items"],
        "code_failures": triage_code_failures(alerts, repair_result),
        "code_auto_patch_enabled": False,
        "automatic_evidence_promotion_enabled": False,
        "gem_trade_entry_authorized": False,
        "safe_retries_requested": (
            repair_result.get("rerun_requests", 0)
            if isinstance(repair_result, dict) else 0),
        "note": "Only safe transient job retries are initiated by the separate, "
                "existing repair step. Source follow-ups run in the next nightly "
                "SEC/FDA/financial/issuer verification cycle; conflicts and deterministic "
                "code failures remain manual-review holds.",
    }


def _json(path):
    try:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return obj if isinstance(obj, dict) else {}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=Path("data/pdufa_source_review_queue.csv"))
    p.add_argument("--source-report", type=Path, default=Path("data/pdufa_source_report.json"))
    p.add_argument("--alerts", type=Path, default=Path("reports/adhoc_alert_check.json"))
    p.add_argument("--repair", type=Path, default=Path("reports/post_scan_repair.json"))
    p.add_argument("--source-run-id", default="")
    p.add_argument("--out", type=Path, default=Path("reports/nightly_recovery_triage.json"))
    a = p.parse_args(argv)
    try:
        with a.queue.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        rows = []
    report = build_report(rows, _json(a.source_report), _json(a.alerts),
                          _json(a.repair), a.source_run_id)
    a.out.parent.mkdir(exist_ok=True, parents=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "queue_status", "unresolved_findings", "expected_unresolved_findings",
        "source_snapshot_matches_current_run", "safe_retries_requested",
        "gem_trade_entry_authorized")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
