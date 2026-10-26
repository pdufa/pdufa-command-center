"""Fail-closed worklist tests using complete synthetic 741-NCT/130-issuer inputs."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_qualification_ledger import GATES
from phase3_rights_review_worklist import build_worklist, registry_priority, REQUIRED_REVIEW, write_review_csv, safe_csv_value
from phase3_sec_trial_rights_join import build_join
from test_phase3_sec_trial_rights_join import TrialSecRightsJoinTests


class Phase3RightsWorklistTests(unittest.TestCase):
    def setUp(self):
        fixture = TrialSecRightsJoinTests()
        fixture.setUp()
        self.program, self.casebook, self.leads, self.pilot = (
            fixture.program, fixture.casebook, fixture.leads, fixture.pilot
        )
        self.join = build_join(self.program, self.casebook, self.leads, self.pilot)
        self.registry = {
            "census_total": 741, "source_identity_verified": 741,
            "source_errors": [], "qualified_pipeline_total": None,
            "original_source_records": [],
        }
        self.ledger = {
            "report_type": "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY",
            "total": 741, "qualified_pipeline_total": None,
            "records": [],
        }
        for i, case in enumerate(self.casebook["items"]):
            nct, ticker = case["nct_id"], case["ticker"]
            company = "Company " + ticker
            case["saved_census_company"] = company
            self.registry["original_source_records"].append({
                "nct_id": nct, "census_ticker": ticker, "census_company": company,
                "source": case["original_registry_api_url"],
                "source_sha256": case["original_registry_sha256"],
                "fetched_at_utc": "2026-10-26T00:00:00Z",
                "current_registry_status": (
                    "RECRUITING" if i % 3 == 0
                    else "SUSPENDED" if i % 3 == 1 else "COMPLETED"
                ),
                "phase3_in_current_registry": True,
                "status_matches_dated_census": True,
            })
            self.ledger["records"].append({
                "nct_id": nct, "ticker": ticker, "company": company,
                "source_url": "https://clinicaltrials.gov/study/" + nct,
                "source_sha256": case["original_registry_sha256"],
                "qualified_pipeline": None,
                "qualification_status": "REVIEW",
                "gates": {g: "PASS" if g == "registry_identity" else "REVIEW" for g in GATES},
            })

    def report(self):
        return build_worklist(self.registry, self.ledger, self.casebook, self.leads, self.join)

    def test_full_scope_priority_and_missing_rights_are_explicit(self):
        report = self.report()
        self.assertEqual((report["total_trials"], report["total_issuer_research_pointers"]), (741, 130))
        self.assertEqual(report["priority_counts"]["P1_CURRENTLY_ACTIVE_REGISTRY_ONLY"], 247)
        self.assertEqual(report["priority_counts"]["P2_REGISTRY_STATUS_OR_PHASE_REVIEW"], 247)
        self.assertEqual(report["priority_counts"]["P3_HISTORICAL_OR_ENDED_REGISTRY_ONLY"], 247)
        self.assertEqual(report["trials_with_issuer_primary_document_text"], 12)
        self.assertEqual(report["trials_with_trial_exact_term_lexical_lead"], 0)
        self.assertEqual(report["independently_verified_current_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertEqual([x["research_review_queue_position"] for x in report["items"]], list(range(1, 742)))

    def test_review_priority_is_not_eligibility_or_trial_outcome(self):
        rows = self.report()["items"]
        self.assertEqual(rows[0]["research_priority"], "P1_CURRENTLY_ACTIVE_REGISTRY_ONLY")
        self.assertTrue(all(not r["commercial_rights_verified"]
                            and r["qualified_pipeline"] is None for r in rows))
        self.assertTrue(all(r["rights_review_checklist"] ==
                            {key: "NOT_VERIFIED" for key in REQUIRED_REVIEW}
                            for r in rows))
        self.assertEqual(len(REQUIRED_REVIEW), 6)

    def test_per_trial_source_links_are_not_other_issuer(self):
        r = {x["nct_id"]: x for x in self.report()["items"]}
        self.assertEqual(r["NCT00000001"]["ticker"], "TEST001")
        self.assertEqual(r["NCT00000001"]["issuer_sec_cik"], "0000000001")
        self.assertEqual(r["NCT00000002"]["ticker"], "TEST002")
        self.assertTrue(all("/data/1/" in x["url"] for x in r["NCT00000001"]["sec_issuer_filing_candidates"]))
        self.assertEqual(r["NCT00000001"]["source_review_stage"],
                         "SOURCE_TEXT_AVAILABLE_NO_EXACT_TERM_LEAD")
        self.assertEqual(r["NCT00000003"]["source_review_stage"],
                         "SEC_PRIMARY_DOCUMENT_NOT_YET_AVAILABLE")

    def test_lexical_source_leads_rank_review_not_rights(self):
        row = next(r for r in self.join["items"] if r["nct_id"] == "NCT00000001")
        source = row["issuer_primary_document_sources"][0]
        row["exact_registry_term_sec_text_leads"] = [{
            "term_kind": "REGISTERED_CONDITION", "registered_term": "Disease Beta",
            "source_url": source["url"], "source_sha256": source["sha256"],
            "review_status": "LEXICAL_ONLY_NOT_VERIFIED_LEGAL_RIGHTS",
            "context_excerpt": "Disease Beta mentioned in the filing.",
            "normalized_text_offset": 54,
        }]
        result = self.report()
        self.assertEqual(result["trials_with_trial_exact_term_lexical_lead"], 1)
        x = next(r for r in result["items"] if r["nct_id"] == "NCT00000001")
        self.assertEqual(x["source_review_stage"], "SOURCE_TEXT_TERM_LEADS_FOR_MANUAL_CHECK")
        self.assertFalse(x["commercial_rights_verified"])
        self.assertEqual(x["exact_lexical_term_source_leads"][0]["source_sha256"], source["sha256"])

    def test_duplicate_registry_identity_rejected(self):
        self.registry["original_source_records"][0]["nct_id"] = "NCT00000002"
        with self.assertRaises(ValueError):
            self.report()

    def test_missing_trial_in_join_rejected(self):
        self.join["items"].pop()
        with self.assertRaises(ValueError):
            self.report()

    def test_mismatched_sha256_rejected(self):
        self.registry["original_source_records"][0]["source_sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            self.report()

    def test_conflicting_issuer_cik_rejected(self):
        self.join["items"][0]["saved_sec_cik"] = "0000000909"
        with self.assertRaises(ValueError):
            self.report()

    def test_forced_rights_pass_rejected(self):
        self.ledger["records"][0]["gates"]["current_commercial_rights"] = "PASS"
        with self.assertRaises(ValueError):
            self.report()

    def test_fake_qualification_rejected(self):
        self.join["items"][0]["qualified_pipeline"] = True
        with self.assertRaises(ValueError):
            self.report()

    def test_cross_issuer_primary_document_url_rejected(self):
        first = self.join["items"][0]["issuer_primary_document_sources"][0]
        first["url"] = "https://www.sec.gov/Archives/edgar/data/42/wrong.htm"
        with self.assertRaises(ValueError):
            self.report()

    def test_forged_document_text_match_rejected(self):
        row = self.join["items"][0]
        source = row["issuer_primary_document_sources"][0]
        row["exact_registry_term_sec_text_leads"] = [{
            "source_url": source["url"], "source_sha256": "f" * 64,
            "registered_term": "Disease Beta",
            "review_status": "LEXICAL_ONLY_NOT_VERIFIED_LEGAL_RIGHTS",
        }]
        with self.assertRaises(ValueError):
            self.report()

    def test_no_source_fetch_is_not_proof_of_no_rights(self):
        for row in self.join["items"]:
            row["issuer_primary_document_sources"] = []
            row["issuer_sec_primary_documents_retrieved"] = 0
            row["exact_registry_term_sec_text_leads"] = []
        result = self.report()
        self.assertEqual(result["trials_with_issuer_primary_document_text"], 0)
        self.assertEqual(result["independently_verified_current_rights"], 0)
        self.assertEqual(result["source_review_stage_counts"]["SEC_PRIMARY_DOCUMENT_NOT_YET_AVAILABLE"], 741)

    def test_registry_status_change_priority_forces_review(self):
        source = self.registry["original_source_records"][0]
        source["status_matches_dated_census"] = False
        source["current_registry_status"] = "RECRUITING"
        result = self.report()
        record = next(r for r in result["items"] if r["nct_id"] == "NCT00000001")
        self.assertEqual(record["research_priority"], "P2_REGISTRY_STATUS_OR_PHASE_REVIEW")

    def test_unknown_registry_phase_flag_rejected(self):
        self.registry["original_source_records"][0]["phase3_in_current_registry"] = "yes"
        with self.assertRaises(ValueError):
            self.report()

    def test_spreadsheet_ready_csv_has_741_rows_and_six_unverified_proofs(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "rights.csv"
            write_review_csv(report, output)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 741)
        self.assertEqual([x["review_position"] for x in rows], [str(i) for i in range(1, 742)])
        self.assertTrue(all(x["commercial_rights_verified"] == "False" for x in rows))
        self.assertTrue(all(x["qualified_pipeline"] == "" for x in rows))
        self.assertTrue(all(all(x[check] == "NOT_VERIFIED" for check in REQUIRED_REVIEW)
                            for x in rows))

    def test_csv_guards_against_formula_in_registered_source_name(self):
        self.assertEqual(safe_csv_value("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(safe_csv_value("   +SUM(1,2)"), "'   +SUM(1,2)")
        self.assertEqual(safe_csv_value("@evil"), "'@evil")
        self.assertEqual(safe_csv_value("Ordinary Trial"), "Ordinary Trial")

    def test_csv_never_exports_forged_rights_verified(self):
        report = self.report()
        report["independently_verified_current_rights"] = 1
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                write_review_csv(report, Path(temp) / "unsafe.csv")


if __name__ == "__main__":
    unittest.main()
