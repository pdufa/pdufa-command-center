"""Offline guards for the new FDA/SEC/issuer/financial/market source jobs."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from types import SimpleNamespace

from scripts import nightly_missing_sources as scan


def rows(path, records):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


def seed_scope(folder):
    rows(folder / "pdufa_candidates.csv", [{"event_key": "ABC|DRUG", "ticker": "ABC", "drug": "Drug"}])
    rows(folder / "company_registry.csv", [{"ticker": "ABC", "cik10": "0000000001"}])


def finish_recheck(folder, command, **kwargs):
    records = scan.read_rows(folder / "recheck_status.csv")
    for record in records:
        record["execution_id"] = command[command.index("--run-id") + 1]
        record["completed_at_utc"] = scan.now()
        record["run_status"] = "COMPLETED_WITH_ERRORS"
    rows(folder / "recheck_status.csv", records)
    return SimpleNamespace(returncode=0)


class MissingSourceTests(unittest.TestCase):
    def test_source_families_are_separate_and_not_full_baseline(self):
        self.assertEqual(set(scan.CATS), {"FDA", "SEC", "FINANCIAL", "MARKET"})
        self.assertEqual(set(scan.STATUS_MAP["SEC"]), {"financing", "ownership_insiders"})
        self.assertIn("issuer primary announcements", scan.FULL_SOURCE_FAMILIES)

    def test_coverage_requires_all_manifests(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root)
            seed_scope(output)
            data = scan.coverage(output, output)
            self.assertEqual(data["sources_passed"], 0)
            self.assertEqual(len(data["missing_required_source_families"]), 5)
            (output / "fda_scan_report.json").write_text('{"status":"COMPLETE"}')
            data = scan.coverage(output, output)
            self.assertEqual(data["sources_passed"], 0)
            self.assertIn("FDA", data["manifest_rejections"])
            self.assertIn("ISSUER", data["missing_required_source_families"])

    def test_sec_http_403_circuit_breaker_preserves_all_registry_ids(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            records = [{"ticker": "X" + str(i), "cik10": str(i + 1)}
                       for i in range(6)]
            rows(folder / "company_registry.csv", records)
            calls = []
            def denied(url, **kwargs):
                calls.append(url)
                raise HTTPError(url, 403, "Forbidden", None, None)
            with patch.object(scan, "http_bytes", side_effect=denied):
                data = scan.sec_registry(folder, folder / "out", "Test agent user@example.org")
            self.assertEqual(len(calls), 3)
            self.assertEqual(data["registry_companies"], 6)
            self.assertEqual(data["companies_checked"], 0)
            self.assertTrue(data["sec_global_403"])
            self.assertEqual(data["sec_registry_status_counts"]["NOT_ATTEMPTED_SEC_403"], 3)
            self.assertEqual(len(scan.read_rows(folder / "out/sec_registry_inventory.csv")), 6)

    def test_issuer_feed_is_discovery_not_verified_release(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            rows(folder / "pdufa_candidates.csv", [
                {"event_key": "ABC|DRUG", "ticker": "ABC", "company": "Test Pharma"}])
            payload = b"""<rss><channel><item><title>Possible topline headline</title>
            <link>https://example.org/news</link>
            <pubDate>Sun, 11 Oct 2026 12:00:00 GMT</pubDate>
            </item></channel></rss>"""
            with patch.object(scan, "http_bytes", return_value=payload):
                data = scan.issuer_discovery(folder, folder / "news")
            self.assertEqual(data["issuer_press_releases_verified"], 0)
            self.assertEqual(data["issuer_news_candidates"], 1)
            audit = scan.read_rows(folder / "news/issuer_news_discovery.csv")
            self.assertEqual(audit[0]["verification"], "NEWS_DISCOVERY_REVIEW_ONLY")

    def test_live_fda_attempts_each_saved_event_without_invented_success(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            rows(folder / "pdufa_candidates.csv", [
                {"event_key": "ABC|DRUG", "ticker": "ABC", "drug": "Drug"}])
            rows(folder / "recheck_status.csv", [
                {"event_key": "ABC|DRUG", "requested_scope": "ALL",
                 "run_status": "COMPLETED_WITH_ERRORS",
                 "pdufa_date_status": "SOURCE_BLOCKED_RETAINED"}])
            with patch.object(scan.subprocess, "run", side_effect=lambda command, **kw: finish_recheck(folder, command, **kw)) as execution:
                outcome = scan.recheck("FDA", folder, folder / "audit")
            command = execution.call_args.args[0]
            self.assertIn("--all", command)
            self.assertIn("pdufa_date", command)
            self.assertEqual(outcome["events_checked"], 1)
            self.assertGreater(outcome["source_issue_count"], 0)

    def test_sec_report_separates_review_from_actual_blockages(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            rows(folder / "pdufa_candidates.csv", [
                {"event_key": "AAA|DRUG", "ticker": "AAA"},
                {"event_key": "BBB|DRUG", "ticker": "BBB"},
                {"event_key": "CCC|DRUG", "ticker": "CCC"}])
            rows(folder / "recheck_status.csv", [
                {"event_key": "AAA|DRUG", "ticker": "AAA",
                 "requested_scope": "ALL", "financing_status": "NO_SOURCE",
                 "ownership_insiders_status": "SEC_FILINGS_CHECKED"},
                {"event_key": "BBB|DRUG", "ticker": "BBB",
                 "requested_scope": "ALL", "financing_status": "PARTIAL_SOURCE_REVIEW",
                 "ownership_insiders_status": "SEC_FILINGS_CHECKED"},
                {"event_key": "CCC|DRUG", "ticker": "CCC",
                 "requested_scope": "ALL", "financing_status": "SOURCE_BLOCKED_RETAINED",
                 "ownership_insiders_status": "SEC_FILINGS_CHECKED"}])
            with patch.object(scan.subprocess, "run", side_effect=lambda command, **kw: finish_recheck(folder, command, **kw)):
                result = scan.recheck("SEC", folder, folder / "artifact")
            self.assertEqual(result["source_issue_count"], 3)
            self.assertEqual(result["source_technical_failure_count"], 1)
            self.assertEqual(result["source_review_only_count"], 2)
            self.assertEqual(len(result["source_issue_examples"]), 3)
            self.assertEqual(result["source_issue_breakdown"]["financing:NO_SOURCE"], 1)

    def test_combined_audit_report_stays_partial(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            seed_scope(folder)
            report = folder / "coverage.json"
            code = scan.main(["--source", "AUDIT",
                              "--data-dir", str(folder),
                              "--artifacts-dir", str(folder),
                              "--report", str(report)])
            self.assertEqual(code, 0)
            state = json.loads(report.read_text())
            self.assertEqual(state["status"], "PARTIAL")
            self.assertFalse(state["full_coverage_verified"])
            self.assertEqual(state["sources_passed"], 0)

    def test_email_separates_completed_collection_from_technical_source_failures(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            report = folder / "audit.json"
            evidence = {
                "scope_coverage_verified": False,
                "verification_technical_failure_count": 4,
                "required_findings_unresolved": 4,
                "findings_unresolved": 0,
                "findings_conflicted": 0,
            }
            with patch.object(scan, "coverage", return_value=evidence):
                result = scan.main(["--source", "AUDIT",
                                    "--data-dir", str(folder),
                                    "--artifacts-dir", str(folder),
                                    "--report", str(report)])
            saved = json.loads(report.read_text())
            self.assertEqual(result, 0)
            self.assertEqual(saved["status"], "PARTIAL")
            self.assertEqual(saved["execution_status"], "COMPLETE_WITH_VERIFICATION_ERRORS")
            self.assertEqual(saved["errors_count"], 4)
            self.assertIn("4 technical source verification failure", saved["errors"][0])
            self.assertFalse(saved["full_coverage_verified"])
            # Research gaps alone do not falsely claim a transport failure.
            clean = dict(evidence, verification_technical_failure_count=0)
            with patch.object(scan, "coverage", return_value=clean):
                scan.main(["--source", "AUDIT",
                           "--data-dir", str(folder),
                           "--artifacts-dir", str(folder),
                           "--report", str(report)])
            saved = json.loads(report.read_text())
            self.assertEqual(saved["status"], "PARTIAL")
            self.assertEqual(saved["execution_status"], "COMPLETE")
            self.assertEqual(saved["errors_count"], 0)
            self.assertEqual(saved["errors"], [])

    def test_stale_recheck_rows_do_not_count_as_current_collection(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            seed_scope(folder)
            rows(folder / "recheck_status.csv", [{
                "event_key": "ABC|DRUG", "requested_scope": "ALL",
                "run_status": "COMPLETED", "execution_id": "old-run",
                "completed_at_utc": scan.now(), "pdufa_date_status": "FINAL_DECISION_VERIFIED"}])
            with patch.object(scan.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                outcome = scan.recheck("FDA", folder, folder / "out")
            self.assertEqual(outcome["events_checked"], 0)
            self.assertEqual(outcome["collection_missing_event_keys"], ["ABC|DRUG"])


if __name__ == "__main__":
    unittest.main()

