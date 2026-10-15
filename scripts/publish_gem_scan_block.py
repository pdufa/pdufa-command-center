#!/usr/bin/env python3
"""Publish fail-closed, read-only GEM block scan status for the SCANS dashboard.

ClinicalTrials.gov posted results are not adjudicated successful Phase 3
readouts. Workflow execution, archive integrity and financing close evidence
are separate. This report never authorizes, suggests or executes a trade.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ACTIONS = ("VERIFY_ALL", "REVERIFY_PARTIAL", "RESCAN_ALL")
SCHEMA_VERSION = 1
STAGES = ("Phase 3", "Post-Financing", "PDUFA")


def dict_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def make_block_report(readiness, collector_state, *, action,
                      collector_outcome, audit_outcome, run_id=None,
                      timestamp=None):
    if action not in ACTIONS:
        raise ValueError("Unsupported GEM control action")
    if collector_outcome not in ("success", "failure", "skipped"):
        raise ValueError("Unsupported collector outcome")
    if audit_outcome not in ("success", "failure"):
        raise ValueError("Unsupported audit outcome")
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    has_audit = (audit_outcome == "success" and bool(readiness)
                 and isinstance(readiness.get("acceptance_checks"), dict))
    collector_performed = action != "VERIFY_ALL"
    collector_ok = (not collector_performed or collector_outcome == "success")
    # VERIFY_ALL does not recollect records or manufacture new observations.
    if not collector_performed:
        collection = "NOT_RUN — SAVED-SOURCE VERIFICATION ONLY"
    elif collector_outcome == "success":
        collection = "COMPLETE — REGISTRY POSTINGS ONLY"
    else:
        collection = "FAILED — NO CURRENT REGISTRY CERTIFICATION"
    errors = []
    if not has_audit:
        errors.append("GEM readiness audit unavailable or invalid")
    if not collector_ok:
        errors.append("Live Phase 3 registry collection did not complete")
    status = "PARTIAL" if has_audit and collector_ok else "FAILED"
    risks = readiness.get("blocking_or_review_flags") if has_audit else []
    if not isinstance(risks, list):
        risks = ["Malformed GEM audit source flags"]
        status = "FAILED"
    counts = readiness.get("ranked", {}) if has_audit else {}
    ranked = {stage: counts.get(stage) if type(counts.get(stage)) is int else None
              for stage in STAGES} if isinstance(counts, dict) else {s: None for s in STAGES}
    include_collector_counts = collector_performed and collector_ok and collector_state.get("complete") is True and collector_state.get("status") == "COMPLETE"
    if collector_performed and collector_ok and not include_collector_counts:
        status = "FAILED"
        errors.append("Collector state did not confirm a complete source pass")
    checked_count = readiness.get("phase3_saved_ledger_rows") if has_audit else None
    stored_count = collector_state.get("stored_results") if include_collector_counts else None
    if include_collector_counts and checked_count != stored_count:
        status = "FAILED"
        errors.append("Phase 3 ledger and collector state disagree")
    run_link = ("https://github.com/pdufa/pdufa-command-center/actions/runs/" +
                str(run_id) if str(run_id or "").isdigit() and int(run_id) > 0 else "")
    return {
        "schema_version": SCHEMA_VERSION, "scan": "GEM",
        "label": "BLOCK 4 — GEMS", "action": action,
        "generated_at_utc": timestamp, "run_id": int(run_id) if run_link else None,
        "run_url": run_link,
        "status": status, "collector_status": collection,
        "collector_performed": collector_performed,
        "artifact_integrity": "NOT INDEPENDENTLY CHECKED",
        "source_verification": "NOT VERIFIED — NOT TRADE READY",
        "full_universe_coverage_verified": False,
        "historical_return_edge_validated": False,
        "trade_entry_authorized": False,
        "clinical_registry": {
            "studies_checked": (collector_state.get("studies_checked") if include_collector_counts else None),
            "matched_posted_results": (collector_state.get("matched_posted_results") if include_collector_counts else None),
            "new_records": (collector_state.get("new_records") if include_collector_counts else None),
            "stored_results": stored_count,
            "finished_at": (collector_state.get("finished_at") if include_collector_counts else None),
        },
        "saved_phase3_reconciled": (readiness.get("phase3_saved_ledger_reconciled") is True
                                    if has_audit else False),
        "observed_phase3_rows": checked_count,
        "verified_phase3_tracking": (readiness.get("verified_phase3_tracking") if has_audit else None),
        "awaiting_second_financing": (readiness.get("awaiting_second_financing") if has_audit else None),
        "ranked_research_only": ranked,
        "cash_runway": (readiness.get("cash_runway") if has_audit else {}),
        "hedge_fund_13f": (readiness.get("hedge_fund_13f") if has_audit else {}),
        "insider_form4": (readiness.get("insider_form4") if has_audit else {}),
        "bpw_comparable": {},  # Backwards-compatible field; diagnostic is separate.
        "two_benchmark_candidate_count": (
            readiness.get("two_benchmark_candidate_count")
            if has_audit and type(readiness.get("two_benchmark_candidate_count")) is int
            else None
        ),
        "two_benchmark_policy": (
            readiness.get("two_benchmark_policy") if has_audit else
            "RELEASED PHASE 3 RESULTS + VERIFIED SECOND POST-READOUT FINANCING CLOSE"
        ),
        "strict_entry_gate_shortlist_count": (
            readiness.get("strict_entry_gate_shortlist_count")
            if has_audit and type(readiness.get("strict_entry_gate_shortlist_count")) is int
            else None
        ),
        "sec_source_health": (readiness.get("sec_source_health") if has_audit else {}),
        "market_source_health": (readiness.get("market_source_health") if has_audit else {}),
        "acceptance_checks": (readiness.get("acceptance_checks") if has_audit else {}),
        "blocking_or_review_flags": risks,
        "errors": errors,
        "research_status": (readiness.get("research_status") if has_audit else "HOLD — AUDIT FAILED"),
        "caveat": ("GEM is a research-only fourth scan block. Two entry benchmarks: "
                   "source-verified Phase 3 results released and independently "
                   "verified second post-readout financing closed. Financial and "
                   "market factors are rankings and risk warnings only. "
                   "PDUFA -3 is a planned exit, not an executed sale."),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=ACTIONS, required=True)
    parser.add_argument("--collector-outcome", choices=("success", "failure", "skipped"), required=True)
    parser.add_argument("--audit-outcome", choices=("success", "failure"), required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/gem_daily"))
    parser.add_argument("--output", type=Path, default=Path("data/gem_scan_block_report.json"))
    args = parser.parse_args(argv)
    readiness = dict_json(args.report_dir / "gem_readiness.json")
    # BPW feature coverage is now a separate on-demand research diagnostic.
    # Do not fold a manual comparison into a nightly eligibility report.
    report = make_block_report(
        readiness,
        dict_json(args.data_dir / "phase3_intake_status.json"),
        action=args.action, collector_outcome=args.collector_outcome,
        audit_outcome=args.audit_outcome,
        run_id=os.environ.get("GITHUB_RUN_ID"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(args.output)
    print(json.dumps({"scan": "GEM", "action": args.action,
                      "status": report["status"],
                      "stored_results": report["clinical_registry"]["stored_results"],
                      "errors": report["errors"]}))
    return 0 if report["status"] != "FAILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
