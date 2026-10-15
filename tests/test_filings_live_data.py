"""Published scan updates replace visible details without launching another scan."""
import csv
import io
import unittest
from unittest.mock import patch

from filings_base_amendments_ui import load_section_details, missing_research_rows
from filings_live_data import DATA_FILES, published_filings_files, download_published_files
from scripts.source_verification import FIELDS


def csv_bytes(rows, fields):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


class LiveFilingsDetailsTests(unittest.TestCase):
    def bundle(self, resolved=False):
        files = {name: b"event_key,ticker\n" for name in DATA_FILES}
        event = {"event_key": "ABC|DRUG", "ticker": "ABC", "drug": "Drug"}
        files["pdufa_candidates.csv"] = csv_bytes([event], event)
        company = {"ticker": "ABC", "cik10": "0000000001"}
        files["company_registry.csv"] = csv_bytes([company], company)
        claim = {**dict.fromkeys(FIELDS, ""), "event_key": "ABC|DRUG", "ticker": "ABC",
                 "category": "FDA", "claim": "PDUFA_TARGET", "verification_required": "YES",
                 "verification_status": "VERIFIED" if resolved else "REVIEW_REQUIRED",
                 "checked_at": "2026-10-15T20:00:00Z" if resolved else "2026-10-15T18:00:00Z",
                 "source_url": "https://example.org/primary" if resolved else "",
                 "source_sha256": "a" * 64 if resolved else ""}
        files["pdufa_source_verification.csv"] = csv_bytes([claim], FIELDS)
        files["pdufa_source_review_queue.csv"] = csv_bytes([] if resolved else [claim], FIELDS)
        return files

    def test_finished_scan_changes_base_and_missing_evidence_together(self):
        with patch("filings_base_amendments_ui.published_filings_files",
                   side_effect=[(self.bundle(), ""), (self.bundle(True), "")]), \
                patch("filings_base_amendments_ui.st.session_state", {}), \
                patch("filings_base_amendments_ui.required_issue_queue") as old_queue:
            before, after = load_section_details(), load_section_details()
        self.assertEqual(before["bases"]["FDA"][0]["Agency verification"], "REVIEW_REQUIRED")
        self.assertEqual(after["bases"]["FDA"][0]["Agency verification"], "VERIFIED")
        self.assertEqual(len(missing_research_rows(before["queue"], "FDA", before["registry"])), 1)
        self.assertEqual(missing_research_rows(after["queue"], "FDA", after["registry"]), [])
        old_queue.assert_not_called()

    def test_network_failure_keeps_last_good_details_and_shows_staleness(self):
        with patch("filings_base_amendments_ui.published_filings_files", side_effect=[
                (self.bundle(True), ""), (None, "Latest published details are unavailable")]), \
                patch("filings_base_amendments_ui.st.session_state", {}), \
                patch("filings_base_amendments_ui.required_issue_queue") as old_queue:
            before, after = load_section_details(), load_section_details()
        self.assertEqual(before["bases"], after["bases"])
        self.assertIn("unavailable", after["refresh_notice"])
        old_queue.assert_not_called()

    def test_download_uses_one_immutable_data_revision(self):
        published_filings_files.clear()
        self.addCleanup(published_filings_files.clear)
        revision = "a" * 40
        with patch("filings_live_data._json_get", return_value=[{"sha": revision}]), \
                patch("filings_live_data.download_published_files", return_value=self.bundle()) as download:
            files, notice = published_filings_files()
        self.assertIn("pdufa_candidates.csv", files)
        self.assertEqual(notice, "")
        download.assert_called_once_with(revision)

    def test_missing_api_token_or_rate_limit_still_reads_public_results(self):
        published_filings_files.clear()
        self.addCleanup(published_filings_files.clear)
        with patch("filings_live_data._json_get", side_effect=OSError("API unavailable")), \
                patch("filings_live_data.download_published_files", return_value=self.bundle()) as download:
            files, notice = published_filings_files()
        self.assertIn("pdufa_source_review_queue.csv", files)
        self.assertEqual(notice, "")
        self.assertEqual(download.call_args.args[0], "main")

    def test_failed_refresh_is_not_presented_as_empty_or_verified(self):
        published_filings_files.clear()
        self.addCleanup(published_filings_files.clear)
        with patch("filings_live_data._json_get", side_effect=OSError("API unavailable")), \
                patch("filings_live_data.download_published_files", side_effect=OSError("raw unavailable")):
            files, notice = published_filings_files()
        self.assertIsNone(files)
        self.assertIn("unavailable", notice)

    def test_untrusted_revision_is_rejected_before_any_download(self):
        download_published_files.clear()
        with patch("filings_live_data.fetch_published_file") as fetch:
            with self.assertRaises(ValueError):
                download_published_files("../../untrusted")
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
