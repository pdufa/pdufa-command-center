"""SEC/FDA tables never confuse filing metadata with primary event proof."""
import unittest
from datetime import date

from scripts.filings_base_amendments import rows_from_submissions
from filings_base_amendments_ui import (table_rows, missing_research_rows,
    program_base_rows, today_amendments, pacific_date)


class SecFilingMetadataTests(unittest.TestCase):
    def recent(self):
        return {"form": ["8-K", "8-K/A", "424B5", "S-3/A", "4"],
                "filingDate": ["2026-10-15"] * 5,
                "accessionNumber": [
                    "0000000001-26-000001", "0000000001-26-000002",
                    "0000000001-26-000003", "0000000001-26-000004",
                    "0000000001-26-000005"],
                "primaryDocument": ["eight.htm", "amend.htm", "prospectus.htm",
                                    "", "insider.xml"]}

    def test_base_and_amendment_classification_is_only_metadata(self):
        rows = rows_from_submissions(
            ticker="ABC", cik10="0000000001", recent=self.recent(),
            index_sha256="a" * 64, as_of=date(2026, 10, 15))
        self.assertEqual([r["category"] for r in rows],
                         ["BASE", "AMENDMENT", "BASE", "AMENDMENT"])
        self.assertTrue(all(r["evidence_scope"] ==
                            "SEC_INDEX_METADATA_ONLY_NOT_FINANCING_CLOSURE" for r in rows))
        self.assertTrue(rows[3]["filing_url"].endswith("/000000000126000004/"))
        self.assertNotIn("insider.xml", [r["filing_url"] for r in rows])

    def test_only_as_of_dated_rows_and_verified_indexes(self):
        self.assertEqual(rows_from_submissions(
            ticker="ABC", cik10="0000000001",
            recent=self.recent(), index_sha256="a" * 64,
            as_of=date(2026, 10, 14)), [])
        with self.assertRaises(ValueError):
            rows_from_submissions(ticker="ABC", cik10="0000000001",
                                  recent=self.recent(), index_sha256="")


class BaseAmendmentTableTests(unittest.TestCase):
    def test_sec_amendment_cannot_claim_transaction_verified(self):
        row = {
            "ticker": "ABC", "filing_type": "8-K/A",
            "category": "AMENDMENT", "filed_at": "2026-10-15",
            "accession_number": "0000000001-26-000002",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/1/2/f.htm",
            "evidence_scope": "SEC_INDEX_METADATA_ONLY_NOT_FINANCING_CLOSURE"}
        x = table_rows([row, {**row, "category": "BASE"}], [], [])
        self.assertEqual(len(x["SEC Amendments"]), 1)
        self.assertEqual(len(x["SEC Base"]), 0)
        self.assertIn("closing not established", x["SEC Amendments"][0]["Evidence"])

    def test_fda_extension_exact_primary_proof_required(self):
        event = "ABC|DRUG"
        base = {"category": "FDA", "claim": "PDUFA_TARGET", "event_key": event,
                "ticker": "ABC", "verification_status": "VERIFIED",
                "expected": "2026-11-18", "observed": "2026-11-18",
                "reason": "Explicit dated FDA PDUFA extension supersedes 2026-10-18",
                "source_url": "https://example.com/exact.pdf"}
        ext = {"event_key": event, "ticker": "ABC",
               "extension_sequence": "1", "prior_pdufa_date": "2026-10-18",
               "current_pdufa_date": "2026-11-18"}
        x = table_rows([], [base], [ext])
        self.assertEqual(len(x["FDA Base"]), 1)
        self.assertEqual(len(x["FDA Amendments"]), 1)
        self.assertEqual(x["FDA Amendments"][0]["Verification"], "VERIFIED")
        old_source = {**base, "reason": "Some unrelated target date"}
        x = table_rows([], [old_source], [ext])
        self.assertEqual(x["FDA Amendments"][0]["Verification"], "REVIEW_REQUIRED")
        self.assertEqual(x["FDA Amendments"][0]["Primary source"], "")

    def test_unverified_and_initial_baselines_are_not_fake_amendments(self):
        ext = {"event_key": "ABC|DRUG", "ticker": "ABC", "extension_sequence": "0",
               "prior_pdufa_date": "", "current_pdufa_date": "2026-11-18"}
        tables = table_rows([], [], [ext])
        self.assertEqual(tables["FDA Amendments"], [])
        self.assertEqual(tables["FDA Base"], [])

    def test_verified_extension_without_tracking_ledger_is_still_listed(self):
        base = {"category": "FDA", "claim": "PDUFA_TARGET", "event_key": "ABC|DRUG",
                "ticker": "ABC", "verification_status": "VERIFIED",
                "observed": "2026-11-18",
                "reason": "Explicit dated FDA PDUFA extension supersedes 2026-10-18",
                "source_url": "https://example.com"}
        tables = table_rows([], [base], [])
        self.assertEqual(len(tables["FDA Amendments"]), 1)
        self.assertEqual(tables["FDA Amendments"][0]["Prior date"], "2026-10-18")




class MissingResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.registry = [{"ticker": "ABC", "cik10": "0000000001"},
                         {"ticker": "XYZ", "cik10": "bad"}]
        self.queue = [
            {"ticker": "ABC", "event_key": "ABC|TRIAL", "category": "SEC",
             "claim": "FINANCING_CLOSURE", "verification_status": "REVIEW_REQUIRED",
             "verification_required": "YES", "reason": "Second closing date missing",
             "expected": "2026-10-10", "source_url": ""},
            {"ticker": "ABC", "event_key": "ABC|TRIAL", "category": "FDA",
             "claim": "PDUFA_TARGET", "verification_status": "CONFLICT",
             "verification_required": "YES", "reason": "New FDA target differs",
             "source_url": "https://www.fda.gov/abc"},
            {"ticker": "XYZ", "event_key": "XYZ|TRIAL", "category": "SEC",
             "claim": "FINANCING_CLOSURE", "verification_status": "VERIFIED",
             "verification_required": "YES", "reason": "Done"},
            {"ticker": "ABC", "event_key": "ABC|TRIAL", "category": "SEC",
             "claim": "RUNWAY_ESTIMATE", "verification_status": "REVIEW_REQUIRED",
             "verification_required": "NO", "reason": "Optional"},
        ]

    def test_sec_queue_uses_separate_unresolved_claims_and_official_edgar_link(self):
        sec = missing_research_rows(self.queue, "SEC", self.registry)
        self.assertEqual(len(sec), 1)
        self.assertEqual(sec[0]["Ticker"], "ABC")
        self.assertEqual(sec[0]["Missing item"], "FINANCING_CLOSURE")
        self.assertIn("Second closing date missing", sec[0]["Why research is needed"])
        self.assertIn("0000000001", sec[0]["Research portal"])
        self.assertEqual(sec[0]["Primary source"], "")

    def test_fda_queue_does_not_inherit_verified_target_for_unverified_extension(self):
        extension = {"Ticker": "ABC", "Trial / event": "ABC|TRIAL",
                     "Verification": "REVIEW_REQUIRED", "Prior date": "2026-10-10",
                     "Revised date": "2026-12-10"}
        fda = missing_research_rows(self.queue, "FDA", self.registry,
                                    fda_extensions=[extension])
        self.assertEqual(len(fda), 2)
        self.assertEqual({r["Missing item"] for r in fda},
                         {"PDUFA_TARGET", "PDUFA_EXTENSION"})
        self.assertTrue(all(r["Verification"] != "VERIFIED" for r in fda))
        self.assertEqual(next(r for r in fda if r["Missing item"] == "PDUFA_EXTENSION")
                         ["Primary source"], "")
        self.assertTrue(all("fda.gov" in r["Research portal"] for r in fda))

    def test_published_verified_extension_does_not_enter_missing_list(self):
        verified_extension = {"Ticker": "ABC", "Trial / event": "ABC|TRIAL",
                              "Verification": "VERIFIED", "Prior date": "2026-10-10",
                              "Revised date": "2026-12-10"}
        fda = missing_research_rows([], "FDA", self.registry,
                                    fda_extensions=[verified_extension])
        self.assertEqual(fda, [])

    def test_unverified_source_url_does_not_become_invented_primary_proof(self):
        item = {**self.queue[0], "source_url": "file:///tmp/forged.pdf"}
        sec = missing_research_rows([item], "SEC", self.registry)
        self.assertEqual(sec[0]["Primary source"], "")
        self.assertEqual(sec[0]["Verification"], "REVIEW_REQUIRED")

    def test_invalid_cik_has_no_edgar_research_link(self):
        row = {**self.queue[0], "ticker": "XYZ", "event_key": "XYZ|TRIAL"}
        sec = missing_research_rows([row], "SEC", self.registry)
        self.assertEqual(sec[0]["Research portal"], "")




class ThreeBlockAgencyTests(unittest.TestCase):
    def setUp(self):
        self.event = {"event_key": "ABC|P3_DRUG", "ticker": "ABC",
                      "drug": "ABC-01", "phase3_date": "2026-01-10",
                      "phase3_status": "PRIMARY_MET_VERIFIED",
                      "trial_evidence_url": "https://clinicaltrials.gov/study/NCT00000001",
                      "nct_id": "NCT00000001"}
        self.p3 = {"event_key": "ABC|P3_DRUG",
                   "saved_phase3_date": "2026-01-10",
                   "saved_phase3_status": "PRIMARY_MET_VERIFIED",
                   "saved_trial_source": "https://www.sec.gov/Archives/fake",
                   "nct_ids": "NCT00000001",
                   "source_recheck_status": "NO_POSTED_REGISTRY_RESULTS"}
        self.pair = {"event_key": "ABC|P3_DRUG",
                     "first_close_date": "2026-03-04",
                     "second_close_date": "2026-05-06",
                     "first_sec_status": "VERIFIED",
                     "second_sec_status": "VERIFIED",
                     "recheck_status": "TRANSACTIONS_RECHECKED_REVIEW",
                     "second_sec_url": "https://www.sec.gov/second"}
        self.fda = {"event_key": "ABC|P3_DRUG", "category": "FDA",
                    "claim": "PDUFA_TARGET", "verification_status": "VERIFIED",
                    "source_url": "https://www.fda.gov/target"}
        self.sec = {"event_key": "ABC|P3_DRUG", "category": "SEC",
                    "claim": "FINANCING_CLOSURE", "verification_status": "VERIFIED",
                    "source_url": "https://www.sec.gov/second"}

    def test_both_bases_show_exact_trial_phase3_and_two_financings(self):
        base = program_base_rows(
            [self.event], [self.p3], [self.pair], [], [self.fda, self.sec])
        self.assertEqual(len(base["SEC"]), 1)
        self.assertEqual(len(base["FDA"]), 1)
        for agency in ("SEC", "FDA"):
            row = base[agency][0]
            self.assertEqual(row["Phase 3 readout"], "2026-01-10")
            self.assertEqual(row["2nd finance close"], "2026-05-06")
            self.assertEqual(row["1st finance close"], "2026-03-04")
            self.assertEqual(row["Trial NCT"], "NCT00000001")
            self.assertEqual(row["2nd finance status"],
                             "BOTH_DOCUMENTS_VERIFIED_SEQUENCE_REVIEW")
            self.assertEqual(row["GEM eligibility"], "NOT CERTIFIED")
            self.assertIn("TWO_FINANCING_SEQUENCE", row["Research gaps"])
        self.assertEqual(base["SEC"][0]["Agency claim"], "FINANCING_CLOSURE")
        self.assertEqual(base["FDA"][0]["Agency claim"], "PDUFA_TARGET")

    def test_historical_second_close_remains_review_only(self):
        history = {"event_key": "ABC|P3_DRUG",
                   "first_financing_date": "2026-03-04",
                   "second_financing_date": "2026-05-06"}
        base = program_base_rows([self.event], [self.p3], [], [history], [])
        self.assertEqual(base["SEC"][0]["2nd finance status"],
                         "SECOND_FINANCING_REVIEW_REQUIRED")
        self.assertEqual(base["FDA"][0]["2nd finance status"],
                         "SECOND_FINANCING_REVIEW_REQUIRED")

    def test_both_missing_lists_include_phase3_and_financing_sequence(self):
        base = program_base_rows([self.event], [self.p3], [self.pair],
                                 [], [self.fda, self.sec])
        for agency in ("SEC", "FDA"):
            missing = missing_research_rows(
                [], agency, [{"ticker": "ABC", "cik10": "0000000001"}],
                benchmarks=base[agency])
            self.assertEqual({r["Missing item"] for r in missing},
                             {"PHASE3_EXACT_EVIDENCE", "TWO_FINANCING_SEQUENCE"})

    def test_sec_today_only_amendments_with_actual_filing_date(self):
        sec = [{"category": "AMENDMENT", "filed_at": "2026-10-15",
                "ticker": "ABC", "filing_type": "8-K/A"},
               {"category": "AMENDMENT", "filed_at": "2026-10-14",
                "ticker": "ABC", "filing_type": "S-3/A"},
               {"category": "BASE", "filed_at": "2026-10-15",
                "ticker": "ABC", "filing_type": "8-K"}]
        result = today_amendments(sec, [], [], today="2026-10-15")
        self.assertEqual(len(result["SEC"]), 1)
        self.assertEqual(result["SEC"][0]["filing_type"], "8-K/A")

    def test_fda_today_only_first_detected_extension_not_updated_today(self):
        extension = {"Trial / event": "ABC|P3_DRUG", "Ticker": "ABC",
                     "Prior date": "2026-10-18",
                     "Revised date": "2026-11-18", "Verification": "REVIEW_REQUIRED"}
        old = {"event_key": "ABC|P3_DRUG",
               "prior_pdufa_date": "2026-10-18",
               "current_pdufa_date": "2026-11-18",
               "extension_detected_at": "2026-10-14T17:00:00Z",
               "last_updated_at": "2026-10-15T20:00:00Z"}
        result = today_amendments([], [extension], [old], today="2026-10-15")
        self.assertEqual(result["FDA"], [])
        fresh = {**old, "extension_detected_at": "2026-10-15T18:00:00Z"}
        result = today_amendments([], [extension], [fresh], today="2026-10-15")
        self.assertEqual(result["FDA"], [extension])
        self.assertEqual(pacific_date("2026-10-16T02:00:00Z"), "2026-10-15")
        self.assertEqual(pacific_date("2026-10-16T02:00:00"), "")

if __name__ == "__main__":
    unittest.main()
