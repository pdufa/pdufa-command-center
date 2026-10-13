"""Publish the reconciled source ledger for SCANS; no score/trade promotion."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.nightly_missing_sources import coverage, now
from scripts.source_verification import VERSION, read_rows, summary


def publish(artifacts, data_dir, output):
    reconciled = coverage(artifacts, data_dir)
    source_rows = []
    checked_times = []
    for source, state in reconciled["source_statuses"].items():
        ledger = artifacts / (source.lower() + "_verification.csv")
        findings = read_rows(ledger) if source not in reconciled["manifest_rejections"] else []
        if findings:
            manifest = json.loads((artifacts / (source.lower() + "_scan_report.json")).read_text())
            checked_times.append(manifest["finished_at"])
        item = {"source": source, "status": state, **summary(findings)}
        if source == "SEC" and findings:
            # These are source-request recovery counts, never evidence proof.
            item["auto_retry_attempts"] = int(manifest.get("sec_auto_retry_attempts", 0))
            item["auto_retry_cleared"] = int(manifest.get("sec_auto_retry_cleared", 0))
            item["auto_retry_limit"] = int(manifest.get("sec_auto_retry_limit", 0))
        source_rows.append(item)
    findings = read_rows(artifacts / "combined_verification.csv")
    required_gaps = [r for r in findings if r["verification_required"] == "YES"
                     and r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}]
    optional_gaps = [r for r in findings if r["verification_required"] == "NO"
                     and r["verification_status"] != "VERIFIED"]
    complete = reconciled["scope_coverage_verified"]
    status = ("COMPLETE WITH WARNINGS" if optional_gaps else "COMPLETE") if complete else "PARTIAL"
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = "https://github.com/pdufa/pdufa-command-center/actions/runs/" + run_id if run_id.isdigit() else ""
    report = {"schema_version": 2, "verification_version": VERSION,
              "updated_at_utc": now(), "status": status,
              "source_checked_at_utc": max(checked_times) if checked_times else "",
              "execution_status": "COMPLETE" if not reconciled["manifest_rejections"] else "INCOMPLETE",
              "latest_run_id": run_id, "latest_run_url": run_url,
              "source_commit": os.environ.get("GITHUB_SHA", ""),
              "scope": "Five extended source ledgers; full trading eligibility is evaluated separately",
              "full_coverage_verified": False, "sources": source_rows,
              "required_issue_examples": required_gaps[:24],
              "supplemental_issue_examples": optional_gaps[:12], **reconciled}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    shutil.copyfile(artifacts / "combined_verification.csv", output.with_name("pdufa_source_verification.csv"))
    from scripts.nightly_missing_sources import write_rows
    from scripts.source_verification import FIELDS
    write_rows(output.with_name("pdufa_source_review_queue.csv"), required_gaps, FIELDS)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts-dir", type=Path, default=Path("reports/missing_sources"))
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--output", type=Path, default=Path("data/pdufa_source_report.json"))
    a = p.parse_args()
    report = publish(a.artifacts_dir, a.data_dir, a.output)
    print(json.dumps({k:report[k] for k in ("status", "sources_passed", "required_findings_unresolved", "optional_findings_unavailable", "manifest_rejections")}))


if __name__ == "__main__": main()
