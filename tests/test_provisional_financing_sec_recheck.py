"""Mocked regression tests: public financing evidence can NEVER grant GEM entry."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from provisional_financing_sec_recheck import recheck_leads


EVENT_KEY = "CYTK|MYQORZO_HCM_20261114"
CIK = "0001061983"
ACC = "0001061983-26-000111"
BASE = ("https://www.sec.gov/Archives/edgar/data/" +
        str(int(CIK)) + "/" + ACC.replace("-", "") + "/")
CLOSE = "2026-05-08"


class FakeVerifier:
    as_of = date(2026, 10, 13)
    def __init__(self, actual=True):
        self.actual = actual
        self.calls = 0

    def cik(self, event):
        return CIK if event.get("ticker") == "CYTK" else ""

    def submissions(self, event):
        return "sec-index", {}, {
            "form": ["8-K"],
            "filingDate": ["2026-05-11"],
            "accessionNumber": [ACC],
            "primaryDocument": ["filing.htm"],
        }

    def body(self, url):
        assert url == BASE + "index.json"
        return json.dumps({"directory": {"item": [
            {"name": "ex99-1.htm"}
        ]}}).encode("utf-8")

    def financing(self, event):
        self.calls += 1
        assert event["financing_close_date"] == CLOSE
        url = event["financing_evidence_url"]
        if self.actual and url == BASE + "ex99-1.htm":
            return {"verification_status": "VERIFIED",
                    "source_url": url, "source_sha256": "a" * 64}
        return {"verification_status": "REVIEW_REQUIRED",
                "source_url": url, "source_sha256": ""}


class TestFreshPublicFinanceSEC(unittest.TestCase):
    def run_test(self, verifier, ticker="CYTK"):
        with tempfile.TemporaryDirectory() as d:
            targets = Path(d) / "targets.csv"
            output = Path(d) / "result.csv"
            with targets.open("w", newline="") as handle:
                w = csv.DictWriter(handle, fieldnames=[
                    "event_key", "ticker", "public_close_date",
                    "transaction_type", "company_ir_url", "research_limitations"])
                w.writeheader()
                w.writerow({
                    "event_key": EVENT_KEY, "ticker": ticker,
                    "public_close_date": CLOSE,
                    "transaction_type": "PUBLIC_EQUITY",
                    "company_ir_url": "https://ir.cytokinetics.com/release",
                    "research_limitations": "One closing only",
                })
            rows = recheck_leads(verifier,
                                 [{"event_key": EVENT_KEY, "ticker": "CYTK"}],
                                 targets, output)
            self.assertEqual(list(csv.DictReader(output.open())), rows)
            return rows[0]

    def test_same_company_sec_document_proves_only_one_transaction(self):
        row = self.run_test(FakeVerifier(actual=True))
        self.assertEqual(row["sec_recheck_status"], "SEC_TRANSACTION_VERIFIED")
        self.assertEqual(row["company_ir_status"], "CONFIRMED_PUBLIC_SOURCE_LEAD")
        self.assertEqual(row["gem_entry_authorized"], "NO")
        self.assertEqual(len(row["sec_sha256"]), 64)

    def test_pricing_or_missing_closure_is_not_verified(self):
        row = self.run_test(FakeVerifier(actual=False))
        self.assertEqual(row["sec_recheck_status"], "SEC_DOCUMENT_NOT_CONFIRMED")
        self.assertEqual(row["gem_entry_authorized"], "NO")

    def test_wrong_ticker_cannot_borrow_other_company_filings(self):
        verifier = FakeVerifier()
        row = self.run_test(verifier, ticker="SMMT")
        self.assertEqual(row["sec_recheck_status"], "REVIEW_IDENTITY_OR_DATE")
        self.assertEqual(verifier.calls, 0)


    def test_exhibit_10_financing_agreement_is_searched(self):
        class AgreementVerifier(FakeVerifier):
            def body(self, url):
                assert url == BASE + "index.json"
                return json.dumps({"directory": {"item": [
                    {"name": "ex99-1.htm"},
                    {"name": "ex-10_1.htm"},
                    {"name": "../escape.htm"},
                ]}}).encode("utf-8")

            def financing(self, event):
                self.calls += 1
                url = event["financing_evidence_url"]
                if url == BASE + "ex-10_1.htm":
                    return {"verification_status": "VERIFIED",
                            "source_url": url, "source_sha256": "b" * 64}
                self.assert_safe_url(url)
                return {"verification_status": "REVIEW_REQUIRED",
                        "source_url": url, "source_sha256": ""}

            @staticmethod
            def assert_safe_url(url):
                assert ".." not in url

        verifier = AgreementVerifier(actual=False)
        row = self.run_test(verifier)
        self.assertEqual(row["sec_recheck_status"], "SEC_TRANSACTION_VERIFIED")
        self.assertTrue(row["sec_url"].endswith("ex-10_1.htm"))
        self.assertEqual(row["gem_entry_authorized"], "NO")

    def test_relevant_later_eighth_filing_is_no_longer_skipped(self):
        class ManyFilingsVerifier(FakeVerifier):
            def submissions(self, event):
                accs = [f"0001061983-26-{100+i:06d}" for i in range(12)]
                self.final_accession = accs[-1].replace("-", "")
                return "sec-index", {}, {
                    "form": ["8-K"] * 12,
                    "filingDate": [
                        (date(2026, 5, 9) + timedelta(days=i)).isoformat()
                        for i in range(12)
                    ],
                    "accessionNumber": accs,
                    "primaryDocument": ["filing.htm"] * 12,
                }

            def body(self, url):
                assert url.endswith("/index.json")
                return json.dumps({"directory": {"item": [
                    {"name": "ex99-1.htm"},
                ]}}).encode("utf-8")

            def financing(self, event):
                self.calls += 1
                url = event["financing_evidence_url"]
                if self.final_accession + "/ex99-1.htm" in url:
                    return {"verification_status": "VERIFIED",
                            "source_url": url, "source_sha256": "c" * 64}
                return {"verification_status": "REVIEW_REQUIRED",
                        "source_url": url, "source_sha256": ""}

        verifier = ManyFilingsVerifier()
        row = self.run_test(verifier)
        self.assertEqual(row["sec_recheck_status"], "SEC_TRANSACTION_VERIFIED")
        self.assertGreater(verifier.calls, 8)
        self.assertEqual(row["gem_entry_authorized"], "NO")

    def test_outside_date_window_and_filing_id_not_accepted(self):
        from provisional_financing_sec_recheck import _filings
        class UntrustedIndex(FakeVerifier):
            def submissions(self, event):
                return "sec-index", {}, {
                    "form": ["8-K", "8-K", "8-K", "8-K"],
                    "filingDate": ["2026-05-01", "2026-05-11",
                                   "2026-05-12", "2026-10-14"],
                    "accessionNumber": [ACC, "../escape", ACC, ACC],
                    "primaryDocument": ["filing.htm"] * 4,
                }
        filings = _filings(UntrustedIndex(), {"ticker": "CYTK"}, date(2026, 5, 8))
        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0][0], date(2026, 5, 12))

    def test_no_closure_in_any_document_remains_unverified(self):
        row = self.run_test(FakeVerifier(actual=False))
        self.assertEqual(row["sec_recheck_status"], "SEC_DOCUMENT_NOT_CONFIRMED")
        self.assertEqual(row["gem_entry_authorized"], "NO")


if __name__ == "__main__":
    unittest.main()
