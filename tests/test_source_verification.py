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

    def test_full_september_month_is_not_corrupted_by_sept_abbreviation(self):
        self.assertEqual(verify.dates("September 4, 2026"), {"2026-09-04"})
        self.assertEqual(verify.dates("Sept. 4, 2026"), {"2026-09-04"})
        self.assertEqual(verify.dates("Sep 4, 2026"), {"2026-09-04"})
        self.assertEqual(verify.dates("September 4, 2026 and Sept. 5, 2026"),
                         {"2026-09-04", "2026-09-05"})

    def test_sec_transient_retry_never_promotes_unverified_or_conflicting_evidence(self):
        base = {"event_key": "ABC|DRUG", "ticker": "ABC", "category": "SEC",
                "claim": "FINANCING_CLOSURE", "verification_status": "TECHNICAL_FAILURE",
                "reason": "HTTP_503", "source_url": SEC_DOC, "source_sha256": ""}
        calls, delays = [], []
        fresh = {**base, "verification_status": "VERIFIED",
                 "source_sha256": "a" * 64, "reason": "Dated SEC closing documented"}
        new, attempted = verify.retry_sec_claim(
            base, lambda: (calls.append("fetch"), fresh)[1],
            sleeper=lambda seconds: delays.append(seconds))
        self.assertTrue(attempted)
        self.assertEqual(new["verification_status"], "VERIFIED")
        self.assertEqual(calls, ["fetch"])
        self.assertEqual(delays, [2])
        for blocked in ("HTTP_403", "HTTP_401", "An identifying SEC_USER_AGENT is required",
                        "SourceUnavailable", "HTTP_404"):
            calls.clear()
            prior = {**base, "reason": blocked}
            same, attempted = verify.retry_sec_claim(prior, lambda: calls.append("should not run"))
            self.assertFalse(attempted, blocked)
            self.assertEqual(same, prior)
            self.assertFalse(calls)
        review, attempted = verify.retry_sec_claim(
            {**base, "verification_status": "REVIEW_REQUIRED", "reason": "No proof of close"},
            lambda: self.fail("Missing evidence must never auto-retry"))
        self.assertFalse(attempted)
        self.assertEqual(review["verification_status"], "REVIEW_REQUIRED")
        with self.assertRaisesRegex(ValueError, "ungrounded verification"):
            verify.retry_sec_claim(base, lambda: {**fresh, "source_sha256": ""}, sleeper=lambda _: None)
        with self.assertRaisesRegex(ValueError, "claim identity"):
            verify.retry_sec_claim(base, lambda: {**fresh, "ticker": "XYZ"}, sleeper=lambda _: None)

    def test_sec_source_auto_rechecks_transport_failure_within_original_run(self):
        calls = []
        def first_fails_then_succeeds(url):
            if "/submissions/" in url:
                calls.append(url)
                if len(calls) == 1:
                    raise verify.SourceUnavailable("HTTP_503")
                return json.dumps(submissions()).encode()
            raise AssertionError("Unexpected external request " + url)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            save_rows(folder / "pdufa_candidates.csv", [{**EVENT}])
            save_rows(folder / "company_registry.csv", [COMPANY])
            out = folder / "reports"
            with patch.object(verify.time, "sleep"):
                manifest = verify.verify_source(
                    "SEC", folder, out, fetch=first_fails_then_succeeds,
                    as_of=date(2026, 10, 12))
            entries = verify.read_rows(out / "sec_verification.csv")
            indexed = next(row for row in entries if row["claim"] == "FILINGS_INVENTORY")
            self.assertEqual(indexed["verification_status"], "VERIFIED")
            self.assertEqual(len(indexed["source_sha256"]), 64)
            self.assertEqual(manifest["sec_auto_retry_attempts"], 1)
            self.assertEqual(manifest["sec_auto_retry_cleared"], 1)
            self.assertEqual(manifest["sec_auto_retry_limit"], 8)
            self.assertEqual(len(calls), 2)
            financing = next(row for row in entries if row["claim"] == "FINANCING_CLOSURE")
            self.assertEqual(financing["verification_status"], "REVIEW_REQUIRED")
            self.assertEqual(manifest["required_findings_unresolved"], 1)

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

    def test_sec_released_final_tranche_is_actual_funding_not_second_phase3(self):
        event = {**EVENT, "financing_evidence_url": SEC_DOC,
                 "financing_close_date": "2025-10-23"}
        release = (
            b"Test Pharma Closes Purchase of All Drug Assets. "
            b"Closing releases final $2.5 million of $11 million financing "
            b"led by existing investors. WOBURN, Mass., October 23, 2025 - "
            b"Test Pharma today announced the closing of its restructuring "
            b"and asset purchase agreement with its former parent company. "
            b"The transaction was funded through an $11 million investment "
            b"led by existing investors; $8.5 million was funded earlier."
        )
        row = self.verifier(release).financing(event)
        self.assertEqual(row["verification_status"], "VERIFIED", row)
        self.assertEqual(row["observed"], "2025-10-23")
        self.assertIn("final financing tranche", row["reason"])
        self.assertIn("not the second post-Phase-3 financing sequence", row["reason"])
        self.assertEqual(len(row["source_sha256"]), 64)
        self.assertTrue(verify.documented_released_final_tranche(release.decode(), "2025-10-23"))
        for false_claim in (
            release.replace(b"October 23, 2025", b"October 24, 2025"),
            release.replace(b"Closing releases final", b"Closing may release final"),
            release.replace(b"Closing releases final", b"Closing expects to release final"),
            release.replace(b"final $2.5 million of $11 million", b"final $25 million of $11 million"),
            release.replace(b"today announced the closing", b"today announced plans for"),
        ):
            self.assertNotEqual(
                self.verifier(false_claim).financing(event)["verification_status"], "VERIFIED")

    def test_sec_dated_completed_preferred_share_purchase_is_a_closing_not_stage_two(self):
        event = {**EVENT, "financing_evidence_url": SEC_DOC,
                 "financing_close_date": "2026-07-01"}
        filing = (
            b"On July 1, 2026 (the Closing Date), Test Pharma entered into an "
            b"Investment Agreement with the Purchasers providing for the "
            b"issuance and sale of shares of Series A Preferred Stock. "
            b"Pursuant to the Investment Agreement, the Purchasers purchased "
            b"an aggregate of 933,900 shares of Preferred Stock at a purchase "
            b"price of $1,000 per share, for an aggregate purchase price of "
            b"$933,900,000. The preferred shares were issued."
        )
        record = self.verifier(filing).financing(event)
        self.assertEqual(record["verification_status"], "VERIFIED")
        self.assertIn("second post-Phase-3 financing order", record["reason"])
        self.assertEqual(record["observed"], "2026-07-01")
        self.assertEqual(len(record["source_sha256"]), 64)

        # Merely entering an agreement, projecting purchases, or a mismatch
        # of the evidenced Closing Date must not verify cash receipt.
        for invalid in (
            b"On July 1, 2026 (the Closing Date), Test Pharma entered "
            b"into an Investment Agreement. Purchasers will purchase "
            b"933,900 preferred shares for $933,900,000 in the future.",
            b"On July 1, 2026 (the Closing Date), Test Pharma entered "
            b"into an Investment Agreement for Series A Preferred Stock. "
            b"The Purchasers purchased an aggregate of 933,900 shares of "
            b"Preferred Stock for an unspecified price.",
            filing.replace(b"July 1, 2026", b"July 2, 2026"),
        ):
            self.assertEqual(self.verifier(invalid).financing(event)["verification_status"],
                             "REVIEW_REQUIRED")

    def test_sec_completed_previously_announced_convertible_notes_close(self):
        event = {**EVENT, "financing_evidence_url": SEC_DOC,
                 "financing_close_date": "2025-11-18"}
        close = (b"On November 18, 2025, Test Pharma completed its previously-announced "
                 b"public offering of $230,000,000 aggregate principal amount of "
                 b"1.625% convertible senior notes due 2031.")
        item = self.verifier(close).financing(event)
        self.assertEqual(item["verification_status"], "VERIFIED")
        self.assertEqual(item["observed"], "2025-11-18")
        self.assertIn("not the post-Phase-3 second-financing sequence", item["reason"])
        self.assertEqual(len(item["source_sha256"]), 64)
        for unverified in (
            b"On November 18, 2025, Test Pharma expects to complete its "
            b"previously-announced public offering of $230,000,000 of notes.",
            b"On November 18, 2025, Test Pharma completed its "
            b"previously-announced public offering of convertible notes.",
            close.replace(b"November 18, 2025", b"November 19, 2025"),
        ):
            self.assertNotEqual(
                self.verifier(unverified).financing(event)["verification_status"],
                "VERIFIED")

    def test_sec_credit_facility_requires_actual_draw_not_total_capacity(self):
        event = {**EVENT, "financing_evidence_url": SEC_DOC,
                 "financing_close_date": "2026-09-04"}
        actual = (
            b"On September 4, 2026 (the Closing Date), Test Pharma entered "
            b"into a Credit Agreement with its lenders. The Credit Agreement "
            b"provides a senior secured credit facility of up to $400 million "
            b"available in the following tranches: (1) $75 million drawn on "
            b"the Closing Date, (2) a potential additional $75 million draw "
            b"at the Company's option following FDA approval."
        )
        self.assertTrue(
            verify.documented_drawn_credit_tranche(actual.decode(), "2026-09-04"),
            {"dates": sorted(verify.dates(actual.decode())),
             "matches_closing": bool(verify.re.search(r"(?i)\bClosing\s+Date\b", actual.decode())),
             "matches_credit": bool(verify.re.search(r"(?i)\bcredit\s+agreement\b", actual.decode())),
             "matches_draw": bool(verify.re.search(
                 r"(?i)\$\s*[\d,.]+\s+(?:million|billion)\s+drawn\s+on\s+the\s+Closing\s+Date\b",
                 actual.decode()))})
        result = self.verifier(actual).financing(event)
        self.assertEqual(result["verification_status"], "VERIFIED", result)
        self.assertEqual(result["observed"], "2026-09-04")
        self.assertIn("actual funded credit-facility draw", result["reason"])
        self.assertIn("$75 million drawn on the Closing Date", result["evidence"])
        self.assertIn("undrawn commitments", result["reason"])
        not_funded = (
            b"On September 4, 2026 (the Closing Date), Test Pharma entered "
            b"into a Credit Agreement for a $400 million credit facility; "
            b"the first $75 million may be drawn on the Closing Date."
        )
        self.assertNotEqual(
            self.verifier(not_funded).financing(event)["verification_status"],
            "VERIFIED")
        wrong_date = actual.replace(b"September 4, 2026", b"September 5, 2026")
        self.assertNotEqual(
            self.verifier(wrong_date).financing(event)["verification_status"],
            "VERIFIED")

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

    def test_official_businesswire_datelines_verify_issuer_release(self):
        vertex = {**EVENT, "company": "Vertex Pharmaceuticals Incorporated",
                  "drug": "povetacicept",
                  "indication": "IgA nephropathy (IgAN) in adults",
                  "trial_evidence_url": SEC_DOC}
        release = (
            b"BOSTON--(BUSINESS WIRE)--Jun. 1, 2026-- "
            b"Vertex Pharmaceuticals Incorporated today announced that "
            b"povetacicept for IgA nephropathy (IgAN) in adults "
            b"was accepted for FDA BLA review."
        )
        result = self.verifier(release).issuer(vertex)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-06-01")

        exel = {**EVENT, "company": "Exelixis, Inc.",
                "drug": "zanzalintinib + atezolizumab",
                "indication": "metastatic colorectal cancer",
                "trial_evidence_url": SEC_DOC}
        combination = (
            b"ALAMEDA, Calif.--(BUSINESS WIRE)--Feb. 2, 2026-- "
            b"Exelixis, Inc. today announced its NDA for zanzalintinib, "
            b"in combination with atezolizumab, for metastatic colorectal "
            b"cancer was accepted for FDA review."
        )
        actual = self.verifier(combination).issuer(exel)[0]
        self.assertEqual(actual["verification_status"], "VERIFIED")
        self.assertEqual(actual["observed"], "2026-02-02")

        # Two molecules mentioned in unrelated sections don't establish
        # a named combination. Nor can a future PDUFA goal be the release date.
        unrelated = (
            b"ALAMEDA, Calif.--(BUSINESS WIRE)--Feb. 2, 2026-- "
            b"Exelixis, Inc. today announced zanzalintinib for metastatic "
            b"colorectal cancer. " + b"Research continues. " * 19 +
            b"Separately, the company announced atezolizumab development."
        )
        self.assertEqual(self.verifier(unrelated).issuer(exel)[0]["verification_status"],
                         "REVIEW_REQUIRED")
        undated = (
            b"Exelixis, Inc. announced zanzalintinib in combination with "
            b"atezolizumab for metastatic colorectal cancer. "
            b"PDUFA target action date December 3, 2026--."
        )
        self.assertEqual(self.verifier(undated).issuer(exel)[0]["verification_status"],
                         "REVIEW_REQUIRED")
        for fake_dateline in (
            b"PDUFA December 3, 2026-- FDA action is expected.",
            b"PDUFA December 3, 2026 \xe2\x80\x94 date set by FDA.",
            b"PDUFA December 3, 2026 (FDA target date).",
        ):
            head = (b"Exelixis, Inc. announced zanzalintinib with atezolizumab "
                    b"for metastatic colorectal cancer. ")
            self.assertEqual(self.verifier(head + fake_dateline).issuer(exel)[0]
                             ["verification_status"], "REVIEW_REQUIRED")

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

