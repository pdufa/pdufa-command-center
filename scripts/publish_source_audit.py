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
    # Publish fresh SEC rechecks as a separate, non-authoritative research
    # section inside the existing source report. This report is already
    # deployed to SCANS; no workflow modification or trading-state mutation.
    ir_report = {"status": "NO_FRESH_RESULT", "leads_checked": 0,
                 "sec_transactions_verified": 0, "results": []}
    ir_path = artifacts / "finance_ir_sec_recheck.csv"
    sec_manifest_path = artifacts / "sec_scan_report.json"
    if sec_manifest_path.is_file():
        sec_manifest = json.loads(sec_manifest_path.read_text())
        intended = int(sec_manifest.get("public_ir_leads_checked_against_sec", 0))
        if (sec_manifest.get("public_ir_recheck_status") == "COMPLETE"
                and ir_path.is_file()):
            raw_ir_rows = read_rows(ir_path)
            # A single closing is not the second post-Phase3 financing;
            # publish no entry authorization, including when SEC verifies it.
            valid = (len(raw_ir_rows) == intended and 0 < intended <= 1000 and
                     all(row.get("company_ir_status") == "CONFIRMED_PUBLIC_SOURCE_LEAD"
                         and row.get("gem_entry_authorized") == "NO"
                         and row.get("event_key") and row.get("ir_close_date")
                         and row.get("sec_recheck_status")
                         for row in raw_ir_rows))
            if valid:
                ir_report = {
                    "status": "COMPLETE_RESEARCH_ONLY",
                    "leads_checked": len(raw_ir_rows),
                    "sec_transactions_verified": sum(
                        row.get("sec_recheck_status") == "SEC_TRANSACTION_VERIFIED"
                        for row in raw_ir_rows),
                    "results": raw_ir_rows,
                    "entry_authorized": False,
                }
            else:
                ir_report["status"] = "RECHECK_LEDGER_INCONSISTENT"
        elif sec_manifest.get("public_ir_recheck_status") == "FAILED":
            ir_report["status"] = "SEC_RECHECK_FAILED"
    report = {"schema_version": 2, "verification_version": VERSION,
              "updated_at_utc": now(), "status": status,
              "source_checked_at_utc": max(checked_times) if checked_times else "",
              "execution_status": "COMPLETE" if not reconciled["manifest_rejections"] else "INCOMPLETE",
              "latest_run_id": run_id, "latest_run_url": run_url,
              "source_commit": os.environ.get("GITHUB_SHA", ""),
              "scope": "Five extended source ledgers; full trading eligibility is evaluated separately",
              "full_coverage_verified": False, "sources": source_rows,
              "public_ir_sec_recheck": ir_report,
              "required_issue_examples": required_gaps[:24],
              "supplemental_issue_examples": optional_gaps[:12], **reconciled}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    # Independently publish filing-index metadata, not funded-closing proof.
    # If SEC source reconciliation was rejected, keep the previous snapshot and
    # declare it stale rather than silently updating it.
    watch = artifacts / "sec_filing_watch.csv"
    accepted_sec = "SEC" not in reconciled["manifest_rejections"]
    if accepted_sec and watch.is_file():
        from scripts.filings_base_amendments import FIELDS as WATCH_FIELDS, SOURCE_SCOPE
        watch_rows = read_rows(watch)
        sec_ledger = read_rows(artifacts / "sec_verification.csv")
        issuer_indexes = {
            (r["ticker"], r["source_sha256"])
            for r in sec_ledger
            if r.get("claim") == "FILINGS_INVENTORY"
            and r.get("verification_status") == "VERIFIED"
        }
        if all(
            set(row) == set(WATCH_FIELDS)
            and (row["ticker"], row["source_index_sha256"]) in issuer_indexes
            and row["evidence_scope"] == SOURCE_SCOPE
            and row["category"] in {"BASE", "AMENDMENT"}
            and bool(row["filing_url"].startswith("https://www.sec.gov/Archives/edgar/data/"))
            for row in watch_rows
        ) and len({(r["ticker"], r["accession_number"]) for r in watch_rows}) == len(watch_rows):
            shutil.copyfile(watch, output.with_name("sec_filing_watch.csv"))
            report["sec_filing_watch_status"] = "PUBLISHED_INDEX_ONLY"
            report["sec_filing_watch_rows"] = len(watch_rows)
        else:
            report["sec_filing_watch_status"] = "REJECTED_UNTRUSTED_METADATA"
            report["sec_filing_watch_rows"] = None
    else:
        report["sec_filing_watch_status"] = "PENDING_SEC_REPORT_OR_INVENTORY"
        report["sec_filing_watch_rows"] = None
    # Re-write the report with the SEC watch publication result visible.
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
