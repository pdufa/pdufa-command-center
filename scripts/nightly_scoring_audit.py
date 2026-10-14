"""Nightly read-only scoring-input audit from checked-in snapshots.

Does not infer FDA probabilities, join unverified assets, or fix missing data.
The source scan run is verified by the orchestration workflow before invoking
this script. Saved CSVs are not represented as fresh scan artifacts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from score_input_audit import MODELS, SOURCES, OVERLAPS, audit_tests, load_sources


def build_report(root=".", *, source_run_id: str, source_workflow: str,
                 source_conclusion: str, when=None) -> dict:
    if not source_run_id.isdecimal() or int(source_run_id) < 1:
        raise ValueError("A positive completed source run ID is required.")
    if source_workflow not in {
        "PDUFA Nightly Scan Report Publisher",
        "PDUFA Nightly FDA SEC Financial Market Issuer Sources",
        "PDUFA Overnight Sequential Scans",
    }:
        raise ValueError("Unrecognized nightly scan completion source.")
    if source_conclusion not in {"success", "failure", "timed_out", "cancelled", "skipped"}:
        raise ValueError("Source workflow conclusion must be explicit.")
    checked = load_sources(root)
    results = audit_tests(checked)
    root_path = Path(root)
    coverage = []
    for label, rel in SOURCES.items():
        coverage.append({
            "dataset": label,
            "path": rel,
            "file_present": (root_path / rel).is_file(),
            "saved_records": len(checked[label]),
        })
    gaps = sum(t["Status"] == "DATA GAP" for t in results)
    reviewed = sum(t["Status"] == "REVIEW" for t in results)
    inputs_available = any(entry["saved_records"] for entry in coverage)
    source_ok = source_conclusion == "success"
    status = ("SCAN_FAILURE" if not source_ok else
              "INPUTS_UNAVAILABLE" if not inputs_available else
              "REVIEW_REQUIRED" if gaps or reviewed else "NO_INPUT_GAPS_FOUND")
    return {
        "generated_at_utc": (when or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
        "status": status,
        "source_scan": {"workflow": source_workflow, "run_id": int(source_run_id),
                        "conclusion": source_conclusion},
        "counts": {"models_mapped": len(MODELS), "overlaps": len(OVERLAPS),
                   "input_tests": len(results), "data_gaps": gaps, "reviews": reviewed},
        "checks": results,
        "sources": coverage,
        "scope": "Read-only saved-input column/overlap checks after completed nightly source jobs",
        "provenance_note": ("Checked-in scoring datasets are inspected after the source jobs completed. "
                            "They are not necessarily the fresh artifacts of that workflow. "
                            "Missing data is not a negative clinical result; shared inputs are not independent votes."),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-workflow", required=True)
    parser.add_argument("--source-conclusion", required=True)
    parser.add_argument("--out", default="data/nightly_scoring_audit.json")
    args = parser.parse_args()
    report = build_report(source_run_id=args.source_run_id,
                          source_workflow=args.source_workflow,
                          source_conclusion=args.source_conclusion)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Scoring input audit:", report["status"],
          "source run:", report["source_scan"]["run_id"],
          "gaps:", report["counts"]["data_gaps"])
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### Nightly scoring input audit\n\n")
            handle.write("Status: **" + report["status"] + "**; "
                         + str(report["counts"]["data_gaps"]) + " missing-input findings.\n\n")
            handle.write("Source: " + args.source_workflow + " / run #" + args.source_run_id + "\n\n")
            handle.write(report["provenance_note"] + "\n")


if __name__ == "__main__":
    main()
