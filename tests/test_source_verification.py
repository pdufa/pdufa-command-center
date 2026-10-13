"""Behavioral checks for primary identity/date/claim verification; no network."""
import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import source_verification as verify
from scripts import nightly_missing_sources as scan
from scripts.scan_email import report_summary


CIK = "0000000001"
COMPANY = {"ticker": "ABC", "company": "Test Pharma", "cik10": CIK}
EVENT = {"event_key": "ABC|DRUG", "ticker": "ABC", "company": "Test Pharma",
         "drug": "TestDrug", "indication": "lung cancer", "pdufa_date": "2026-11-01"}
SEC_DOC = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex99-1.htm"


def save_rows(path, records):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records)


def submissions(cik=1, ticker="ABC"):
    return {"cik": cik, "tickers": [ticker], "filings": {"recent": {
        "form": ["8-K"], "filingDate": ["2026-10-10"],
        "accessionNumber": ["0000000001-26-000001"], "primaryDocument": ["report.htm"]}}}


def fact(value, start=None, end="2026-09-30"):
    result = {"val": value, "end": end, "filed": "2026-10-10", "form": "10-Q", "accn": "0000000001-26-000001"}
    if start:
        result["start"] = start
    return result


def financial_payload():
    return {"cik": 1, "facts": {"us-gaap": {
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [fact(100)]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [fact(-25, "2026-07-01")]}}}}}


def market_payload(symbol="ABC", timestamp=None):
    timestamp = timestamp or datetime(2026, 10, 9, 20, tzinfo=timezone.utc).timestamp()
    return {"chart": {"error": None, "result": [{"meta": {"symbol": symbol},
        "timestamp": [timestamp], "indicators": {"quote": [{"close": [10], "volume": [1000]}]}}]}}


class VerificationTests(unittest.TestCase):
    def verifier(self, response):
        raw = response if isinstance(response, bytes) else json.dumps(response).encode()
        return verify.Verifier([COMPANY], fetch=lambda url: raw, as_of=date(2026, 10, 12))

    def test_sec_inventory_requires_cik_ticker_and_nonempty_schema(self):
        good = self.verifier(submissions()).registry(COMPANY)
        self.assertEqual(good["verification_status"], "VERIFIED")
        self.assertEqual(len(good["source_sha256"]), 64)
        self.assertEqual(self.verifier(submissions(cik=2)).registry(COMPANY)["verification_status"], "CONFLICT")
        self.assertEqual(self.verifier(submissions(ticker="XYZ")).registry(COMPANY)["verification_status"], "CONFLICT")
        self.assertEqual(self.verifier({}).registry(COMPANY)["verification_status"], "CONFLICT")
        payload = submissions()
        payload["filings"]["recent"]["form"] = []
        self.assertEqual(self.verifier(payload).registry(COMPANY)["verification_status"], "REVIEW_REQUIRED")

    def test_empty_response_is_a_technical_failure(self):
        result = self.verifier(b"").registry(COMPANY)
        self.assertEqual(result["verification_status"], "TECHNICAL_FAILURE")

    def test_response_cache_does_not_refetch_shared_company(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return json.dumps(submissions()).encode()
        v = verify.Verifier([COMPANY], fetch=fetch)
        v.registry(COMPANY)
        v.registry(COMPANY)
        self.assertEqual(len(calls), 1)

    def test_sec_403_circuit_breaker_stops_requests(self):
        v = verify.Verifier([COMPANY])
        with patch.dict("os.environ", {"SEC_USER_AGENT": "Test agent user@example.org"}), \
             patch.object(verify.time, "sleep"), \
             patch.object(verify.urllib.request, "urlopen", side_effect=HTTPError("https://data.sec.gov", 403, "denied", {}, None)) as opened:
            for i in range(4):
                with self.assertRaises(verify.SourceUnavailable):
                    v.fetch("https://data.sec.gov/submissions/CIK" + str(i).zfill(10) + ".json")
            self.assertEqual(opened.call_count, 3)

    def test_primary_target_can_be_verified_without_becoming_a_decision(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC}
        body = b"Test Pharma announced TestDrug for lung cancer. The FDA PDUFA target date is November 1, 2026."
        result = self.verifier(body).regulatory(event)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["claim"], "PDUFA_TARGET")
        self.assertNotIn("outcome", result)
        self.assertEqual(event.get("decision_date", ""), "")

    def test_primary_target_disagreement_is_a_conflict(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC}
        body = b"TestDrug for lung cancer. The PDUFA target date is December 1, 2026."
        self.assertEqual(self.verifier(body).regulatory(event)[0]["verification_status"], "CONFLICT")

    def test_explicit_indication_abbreviation_in_matching_drug_passage(self):
        event = {**EVENT,
                 "indication": "autosomal dominant hypocalcemia type 1 (ADH1)",
                 "pdufa_evidence_url": SEC_DOC}
        body = b"Test Pharma reports that TestDrug for ADH1 has PDUFA target date November 1, 2026."
        self.assertEqual(self.verifier(body).regulatory(event)[0]["verification_status"], "VERIFIED")
        for wrong in (
            b"Test Pharma reports TestDrug for ADH2 with PDUFA target date November 1, 2026.",
            b"Test Pharma reports OtherDrug for ADH1 with PDUFA target date November 1, 2026.",
        ):
            self.assertEqual(self.verifier(wrong).regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_wrong_drug_indication_company_or_cik_cannot_verify(self):
        event = {**EVENT, "pdufa_evidence_url": "https://www.fda.gov/saved-event"}
        for body in (
            b"Test Pharma OtherDrug lung cancer. PDUFA November 1, 2026.",
            b"Test Pharma TestDrug skin infection. PDUFA November 1, 2026.",
            b"Other Company TestDrug lung cancer. PDUFA November 1, 2026."):
            self.assertEqual(self.verifier(body).regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")
        event["pdufa_evidence_url"] = SEC_DOC.replace("/data/1/", "/data/2/")
        self.assertEqual(self.verifier(b"Test Pharma TestDrug lung cancer. PDUFA November 1, 2026.").regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_secondary_article_is_never_primary_evidence(self):
        event = {**EVENT, "pdufa_evidence_url": "https://news.google.com/story"}
        v = self.verifier(b"TestDrug lung cancer PDUFA November 1, 2026")
        self.assertEqual(v.regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")
        self.assertNotIn("https://news.google.com/story", v.cache)

    def test_semicolon_does_not_separate_drug_from_correct_pdufa_date(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC,
                 "drug": "MYQORZO",
                 "indication": "symptomatic obstructive HCM / MAPLE-HCM expansion",
                 "pdufa_date": "2026-11-14"}
        body = (
            b"MYQORZO approved for symptomatic obstructive HCM; Supplemental NDA "
            b"for MAPLE-HCM accepted for filing by FDA with PDUFA date of November 14, 2026."
        )
        actual = self.verifier(body).regulatory(event)[0]
        self.assertEqual(actual["verification_status"], "VERIFIED")
        self.assertEqual(actual["observed"], "2026-11-14")

    def test_two_pdufa_dates_in_one_heading_do_not_cross_attribute(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC,
                 "drug": "BBP-418", "indication": "LGMD2I/R9",
                 "pdufa_date": "2026-11-27"}
        body = (
            b"BBP-418 for LGMD2I/R9 PDUFA date set for November 27, 2026 "
            b"with Priority Review Launch upon FDA approval Encaleret for ADH1 "
            b"PDUFA date set for May 8, 2027 with Priority Review."
        )
        actual = self.verifier(body).regulatory(event)[0]
        self.assertEqual(actual["verification_status"], "VERIFIED")
        self.assertEqual(actual["observed"], "2026-11-27")
        other = {**event, "drug": "Encaleret", "indication": "ADH1",
                 "pdufa_date": "2027-05-08"}
        other_row = self.verifier(body).regulatory(other)[0]
        self.assertEqual(other_row["verification_status"], "VERIFIED")
        self.assertEqual(other_row["observed"], "2027-05-08")

    def test_multidrug_release_keeps_pdufa_dates_with_own_program(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC}
        release = (
            b"Test Pharma reports that TestDrug for lung cancer was accepted "
            b"with priority review (PDUFA November 1, 2026); "
            b"OtherDrug for skin infections received priority review "
            b"(PDUFA May 8, 2027), with no advisory committee planned."
        )
        row = self.verifier(release).regulatory(event)[0]
        self.assertEqual(row["verification_status"], "VERIFIED")
        self.assertEqual(row["observed"], "2026-11-01")
        self.assertNotIn("2027-05-08", row["observed"])
        wrong_event = {**event, "pdufa_date": "2026-11-02"}
        wrong = self.verifier(release).regulatory(wrong_event)[0]
        self.assertEqual(wrong["verification_status"], "CONFLICT")

    def test_other_program_target_in_same_filing_cannot_verify_event(self):
        event = {**EVENT, "pdufa_evidence_url": SEC_DOC}
        body = b"TestDrug is being studied in lung cancer. The trial is ongoing. We have a separate pipeline. OtherDrug is for skin infections. The PDUFA target date is November 1, 2026."
        self.assertEqual(self.verifier(body).regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_past_target_is_unresolved_even_if_original_date_matches(self):
        event = {**EVENT, "pdufa_date": "2026-09-01", "pdufa_evidence_url": SEC_DOC}
        self.assertEqual(self.verifier(b"TestDrug lung cancer. PDUFA September 1, 2026.").regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_posting_date_does_not_substitute_for_action_date(self):
        event = {**EVENT, "outcome": "APPROVED", "decision_date": "2026-10-10", "pdufa_evidence_url": SEC_DOC}
        raw = b'<script>{"datePublished":"2026-10-10"}</script>Test Pharma FDA approved TestDrug for lung cancer.'
        self.assertEqual(self.verifier(raw).regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")
        raw = b"On October 10, 2026, FDA approved TestDrug for lung cancer. Test Pharma announced the decision."
        self.assertEqual(self.verifier(raw).regulatory(event)[0]["verification_status"], "VERIFIED")

    def test_projected_crl_is_not_a_confirmed_decision(self):
        event = {**EVENT, "outcome": "CRL", "decision_date": "2026-10-10", "pdufa_evidence_url": SEC_DOC}
        body = b"TestDrug lung cancer. On October 10, 2026 Test Pharma expects the FDA may issue a complete response letter."
        self.assertEqual(self.verifier(body).regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_financing_keyword_and_date_never_certify_financing_number_two(self):
        event = {**EVENT, "financing_evidence_url": SEC_DOC, "financing_close_date": "2026-10-10"}
        result = self.verifier(b"On October 10, 2026, the company completed its public offering.").financing(event)
        self.assertEqual(result["verification_status"], "REVIEW_REQUIRED")
        self.assertIn("second-financing sequence", result["reason"])

    def test_cash_fact_and_aligned_runway_arithmetic_are_separate_claims(self):
        records = self.verifier(financial_payload()).financial(EVENT)
        self.assertEqual([r["verification_status"] for r in records], ["VERIFIED", "VERIFIED"])
        self.assertAlmostEqual(float(records[1]["observed"]), 100 / (25 / (92 / 30.4375)), places=3)
        self.assertIn("estimate", records[1]["reason"])

    def test_cash_conflict_and_incompatible_runway_period_are_visible(self):
        records = self.verifier(financial_payload()).financial({**EVENT, "cash": "200"})
        self.assertEqual(records[0]["verification_status"], "CONFLICT")
        payload = financial_payload()
        payload["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"][0]["end"] = "2026-06-30"
        records = self.verifier(payload).financial(EVENT)
        self.assertEqual(records[1]["verification_status"], "REVIEW_REQUIRED")

    def test_future_cash_filing_and_wrong_cik_cannot_verify(self):
        payload = financial_payload()
        payload["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"][0]["filed"] = "2026-10-13"
        self.assertEqual(self.verifier(payload).financial(EVENT)[0]["verification_status"], "REVIEW_REQUIRED")
        payload = financial_payload()
        payload["cik"] = 2
        self.assertEqual(self.verifier(payload).financial(EVENT)[0]["verification_status"], "CONFLICT")

    def test_verified_quote_does_not_verify_short_iv_or_borrow(self):
        records = self.verifier(market_payload()).market(EVENT)
        self.assertEqual(records[0]["verification_status"], "VERIFIED")
        self.assertEqual(records[1]["verification_status"], "UNAVAILABLE")
        self.assertEqual(self.verifier(market_payload("XYZ")).market(EVENT)[0]["verification_status"], "CONFLICT")
        stamp = datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()
        self.assertEqual(self.verifier(market_payload(timestamp=stamp)).market(EVENT)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_undated_saved_price_drift_is_not_a_live_quote_conflict(self):
        event = {**EVENT, "price_last": "250.00"}
        row = self.verifier(market_payload()).market(event)[0]
        self.assertEqual(row["verification_status"], "VERIFIED")
        self.assertEqual(row["claim"], "PRICE_VOLUME")
        self.assertEqual(row["expected"], "")
        self.assertEqual(float(row["observed"]), 10.0)
        self.assertEqual(json.loads(row["evidence"])["undated_saved_price_last"], "250.00")

    def test_market_empty_misaligned_or_nonfinite_data_cannot_verify(self):
        payload = market_payload()
        payload["chart"]["result"][0]["timestamp"] = []
        self.assertEqual(self.verifier(payload).market(EVENT)[0]["verification_status"], "REVIEW_REQUIRED")
        payload = market_payload()
        payload["chart"]["result"][0]["indicators"]["quote"][0]["close"] = [float("nan")]
        self.assertEqual(self.verifier(payload).market(EVENT)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_issuer_requires_primary_exhibit_identity_and_release_dateline(self):
        event = {**EVENT, "trial_evidence_url": SEC_DOC}
        raw = b'Exhibit 99.1. BOSTON, October 10, 2026 (GLOBE NEWSWIRE) Test Pharma announced TestDrug results in lung cancer.'
        result = self.verifier(raw).issuer(event)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-10-10")
        raw = b"Test Pharma announced TestDrug in lung cancer. The PDUFA date is November 1, 2026."
        self.assertEqual(self.verifier(raw).issuer(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_city_hyphen_dateline_is_valid_but_pdufa_date_is_not_publish_date(self):
        event = {**EVENT, "trial_evidence_url": SEC_DOC}
        raw = (b"Test Pharma reports TestDrug results in lung cancer. "
               b"SOUTH SAN FRANCISCO, Calif., October 1, 2026 - "
               b"Test Pharma announces expanded clinical results for TestDrug in lung cancer.")
        row = self.verifier(raw).issuer(event)[0]
        self.assertEqual(row["verification_status"], "VERIFIED")
        self.assertEqual(row["observed"], "2026-10-01")
        wrong = (b"Test Pharma announces TestDrug for lung cancer. "
                 b"PDUFA November 1, 2026 - FDA target date remains scheduled.")
        self.assertEqual(self.verifier(wrong).issuer(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_issuer_discovers_actual_sec_exhibit_when_saved_url_absent(self):
        def fetch(url):
            if url.endswith(".json") and "/submissions/" in url:
                return json.dumps(submissions()).encode()
            if url.endswith("index.json"):
                return b'{"directory":{"item":[{"name":"ex99-1.htm"}]}}'
            if url == SEC_DOC:
                return b"BOSTON, October 10, 2026 (GLOBE NEWSWIRE) Test Pharma announced TestDrug results in lung cancer."
            raise AssertionError(url)
        v = verify.Verifier([COMPANY], fetch=fetch, as_of=date(2026, 10, 12))
        self.assertEqual(v.issuer(EVENT)[0]["verification_status"], "VERIFIED")

    def test_source_verification_writes_ledger_and_preserves_candidate_data(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            save_rows(folder / "pdufa_candidates.csv", [EVENT])
            save_rows(folder / "company_registry.csv", [COMPANY])
            before = (folder / "pdufa_candidates.csv").read_bytes()
            result = verify.verify_source("MARKET", folder, folder / "out", fetch=lambda u: json.dumps(market_payload()).encode(), as_of=date(2026, 10, 12))
            self.assertEqual(result["findings_verified"], 1)
            self.assertEqual(result["findings_unresolved"], 0)
            self.assertEqual(result["optional_findings_unavailable"], 3)
            self.assertTrue(result["scope_coverage_verified"])
            ledger = folder / "out" / result["verification_ledger"]
            self.assertEqual(result["verification_ledger_sha256"], verify.digest(ledger.read_bytes()))
            self.assertEqual((folder / "pdufa_candidates.csv").read_bytes(), before)

    def test_duplicate_candidate_scope_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            save_rows(folder / "pdufa_candidates.csv", [EVENT, EVENT])
            save_rows(folder / "company_registry.csv", [COMPANY])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                verify.verify_source("FDA", folder, folder, fetch=lambda u: self.fail("Unexpected network request"))

    def test_email_exposes_verification_counts_and_missing_sources_without_sec_counts(self):
        state, details = report_summary({"status": "PARTIAL", "findings_verified": 2,
            "findings_unresolved": 3, "findings_conflicted": 1, "verification_technical_failure_count": 4,
            "missing_required_source_families": ["FDA"]}, 0, True)
        self.assertEqual(state, "PARTIAL")
        for text in ("Findings verified: 2", "Unresolved findings: 3", "Conflicting findings: 1", "Technical verification failures: 4", "FDA"):
            self.assertIn(text, details)


class ReconciliationTests(unittest.TestCase):
    def fixture(self, folder):
        save_rows(folder / "pdufa_candidates.csv", [EVENT])
        save_rows(folder / "company_registry.csv", [COMPANY])
        started = verify.utcnow()
        result = verify.verify_source("FDA", folder, folder, fetch=lambda u: b"TestDrug lung cancer. PDUFA November 1, 2026.", as_of=date(2026, 10, 12))
        # No primary link: genuine unresolved evidence, not a mock COMPLETE.
        report = {**result, "status": "PARTIAL", "started_at": started, "finished_at": verify.utcnow(), "recheck_exit_code": 0}
        path = folder / "fda_scan_report.json"
        path.write_text(json.dumps(report))
        return path, report

    def test_current_consistent_partial_ledger_is_reconciled(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            self.fixture(folder)
            result = scan.coverage(folder, folder)
            self.assertNotIn("FDA", result["manifest_rejections"])
            self.assertEqual(result["findings_unresolved"], 1)
            self.assertTrue((folder / "verification_review_queue.csv").exists())

    def test_complete_label_alone_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            path, report = self.fixture(folder)
            path.write_text('{"status":"COMPLETE"}')
            self.assertIn("FDA", scan.coverage(folder, folder)["manifest_rejections"])

    def test_verified_source_can_complete_its_declared_scope(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            event = {**EVENT, "pdufa_evidence_url": SEC_DOC}
            save_rows(folder / "pdufa_candidates.csv", [event])
            save_rows(folder / "company_registry.csv", [COMPANY])
            started = verify.utcnow()
            result = verify.verify_source("FDA", folder, folder, fetch=lambda u: b"TestDrug lung cancer. PDUFA November 1, 2026.", as_of=date(2026, 10, 12))
            self.assertTrue(result["scope_coverage_verified"])
            (folder / "fda_scan_report.json").write_text(json.dumps({**result, "status": "COMPLETE", "started_at": started, "finished_at": verify.utcnow()}))
            self.assertEqual(scan.coverage(folder, folder)["sources_passed"], 1)

    def test_tampered_ledger_wrong_run_scope_and_counts_are_rejected(self):
        for field, value in (("verification_run_id", "old-run"), ("verification_scope_sha256", "bad"), ("findings_verified", 999), ("scope_coverage_verified", True)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as root:
                folder = Path(root)
                path, report = self.fixture(folder)
                report[field] = value
                path.write_text(json.dumps(report))
                self.assertIn("FDA", scan.coverage(folder, folder)["manifest_rejections"])
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            self.fixture(folder)
            with (folder / "fda_verification.csv").open("a") as handle:
                handle.write("changed\n")
            self.assertIn("FDA", scan.coverage(folder, folder)["manifest_rejections"])

    def test_old_manifest_is_not_current_coverage(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            path, report = self.fixture(folder)
            report["finished_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            path.write_text(json.dumps(report))
            self.assertIn("FDA", scan.coverage(folder, folder)["manifest_rejections"])


if __name__ == "__main__":
    unittest.main()

