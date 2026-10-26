"""SEC source-text exact registered trial term research: no legal-rights inference."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_sec_exact_term_leads import prepare_program_terms, exact_text_mentions
from phase3_sec_rights_documents_pilot import build_report as build_pilot
from phase3_sec_trial_rights_join import build_join
from test_phase3_sec_rights_documents_pilot import mock_sources


class TrialTermSecTextTests(unittest.TestCase):
    def setUp(self):
        self.casebook, self.leads = mock_sources()
        self.program = {
            "report_type": "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY",
            "total_trials": 741,
            "total_saved_issuer_pointers": 130,
            "independently_verified_program_identities": 0,
            "independently_verified_commercial_rights": 0,
            "qualified_pipeline_total": None,
            "items": [],
        }
        for row in self.casebook["items"]:
            ticker = row["ticker"]
            drug = f"DRUG-{ticker}"
            condition = f"Disease-{ticker}"
            self.program["items"].append({
                "nct_id": row["nct_id"], "ticker": ticker,
                "original_registry_source_url": row["original_registry_api_url"],
                "original_registry_source_sha256": row["original_registry_sha256"],
                "registry_interventions": [
                    {"type": "DRUG", "name": drug},
                    {"type": "DRUG", "name": "Placebo"},
                ],
                "provisional_drug_or_biologic_names": [drug],
                "registry_conditions": [condition],
                "identity_review_status": "REGISTRY_TERMS_REQUIRE_INDEPENDENT_REVIEW",
                "drug_indication_qualified": False,
                "commercial_rights_verified": False, "qualified_pipeline": None,
                "original_registry_study_title": "Trial source title",
                "conditions_field_status": "PRESENT",
                "interventions_field_status": "PRESENT",
            })
        self.requests = []

    def fetched(self, url):
        self.requests.append(url)
        if "/data/1/" in url:
            return (b"<html><body>Issuer licenses unrelated DRUG-TEST001"
                    b" for Disease-TEST001 in the United States, "
                    b"but this is not verified commercial rights.</body></html>")
        return b"<html><body>Unrelated generic corporate filing with licensing</body></html>"

    def pilot(self, **kw):
        return build_pilot(self.casebook, self.leads, fetch=self.fetched,
                           program=self.program, max_issuers=2, **kw)

    def test_complete_original_nct_ticker_provenance(self):
        prepared = prepare_program_terms(self.program, self.casebook)
        self.assertEqual(len(prepared), 130)
        self.assertEqual(len(prepared["TEST001"]), 12)
        self.assertEqual(prepared["TEST001"][0][0], "NCT00000001")

    def test_real_source_text_pilot_provides_only_issuer_specific_mentions(self):
        result = self.pilot()
        self.assertEqual(result["total_trials"], 741)
        self.assertEqual(result["documents_retrieved"], 4)
        self.assertEqual(result["documents_with_exact_registered_trial_term_mentions"], 2)
        self.assertEqual(result["trials_with_exact_registered_term_text_leads"], 6)
        self.assertEqual(result["trial_term_scan_scope"],
                         "BOUNDED_ISSUER_PRIMARY_FILINGS_REGISTERED_TERMS_LEXICAL_ONLY")
        self.assertEqual(result["trials_with_issuer_primary_text_scanned"], 12)
        self.assertEqual(result["trials_without_issuer_primary_text_scanned"], 729)
        self.assertEqual(result["scanned_trials_without_exact_registered_term_text_leads"], 6)
        self.assertEqual(result["independently_verified_current_rights"], 0)
        self.assertIsNone(result["qualified_pipeline_total"])
        for doc in result["issuers"][0]["documents"]:
            self.assertTrue(all(hit["nct_id"] in
                                {x["nct_id"] for x in self.casebook["items"]
                                 if x["ticker"] == "TEST001"}
                                for hit in doc["trial_registered_term_lexical_mentions"]))
            self.assertFalse(doc["verified_trial_development_rights"])

    def test_join_attaches_hash_and_url_to_exact_trial_not_other_issuer(self):
        pilot = self.pilot()
        report = build_join(self.program, self.casebook, self.leads, pilot)
        self.assertEqual(report["trials_with_exact_registered_term_sec_lexical_leads"], 6)
        self.assertEqual(report["verified_current_commercial_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        rows = {x["nct_id"]: x for x in report["items"]}
        match = rows["NCT00000001"]
        self.assertTrue(match["exact_registry_term_sec_text_leads"])
        self.assertEqual(match["trial_drug_sec_document_match"], "NOT_REVIEWED")
        self.assertFalse(match["current_rights_verified"])
        self.assertRegex(match["exact_registry_term_sec_text_leads"][0]["source_sha256"],
                         r"^[a-f0-9]{64}$")
        self.assertEqual(rows["NCT00000002"]["exact_registry_term_sec_text_leads"], [])

    def test_exact_word_boundaries_prevent_partial_drug_match(self):
        found = exact_text_mentions("AXB-1234", [
            ("NCT00000001", "REGISTERED_DRUG_OR_BIOLOGIC", "AXB-123"),
            ("NCT00000001", "REGISTERED_DRUG_OR_BIOLOGIC", "AXB-1234"),
        ])
        self.assertEqual([x["registered_term"] for x in found], ["AXB-1234"])

    def test_placebo_and_generic_study_drug_never_become_search_targets(self):
        self.program["items"][0]["provisional_drug_or_biologic_names"] = ["Placebo"]
        prepared = prepare_program_terms(self.program, self.casebook)
        self.assertFalse(any(x[2] == "Placebo" for x in prepared["TEST001"]))
        self.assertEqual(exact_text_mentions("placebo DRUG-TEST001", [
            ("NCT00000001", "REGISTERED_CONDITION", "Disease-TEST001")
        ]), [])

    def test_unattempted_documents_have_no_trial_text_leads(self):
        pilot = build_pilot(self.casebook, self.leads, max_issuers=1,
                            agent="", program=self.program)
        self.assertEqual(pilot["documents_attempted"], 0)
        self.assertEqual(pilot["trials_with_exact_registered_term_text_leads"], 0)
        self.assertEqual(pilot["trials_with_issuer_primary_text_scanned"], 0)
        self.assertEqual(pilot["trials_without_issuer_primary_text_scanned"], 741)
        self.assertEqual(pilot["trial_term_scan_scope"], "NO_PRIMARY_DOCUMENT_TEXT_AVAILABLE")
        self.assertEqual(pilot["documents_not_attempted_missing_agent"], 2)

    def test_mismatched_program_issuer_fails_closed_before_fetch(self):
        self.program["items"][0]["ticker"] = "TEST002"
        with self.assertRaises(ValueError):
            self.pilot()
        self.assertEqual(self.requests, [])

    def test_mismatched_program_source_hash_fails_closed_before_fetch(self):
        self.program["items"][0]["original_registry_source_sha256"] = "9"*64
        with self.assertRaises(ValueError):
            self.pilot()
        self.assertEqual(self.requests, [])

    def test_cross_issuer_forged_mention_rejected_on_join(self):
        pilot = self.pilot()
        pilot["issuers"][0]["documents"][0]["trial_registered_term_lexical_mentions"][0]["nct_id"] = "NCT00000002"
        with self.assertRaises(ValueError):
            build_join(self.program, self.casebook, self.leads, pilot)

    def test_unregistered_term_mention_rejected_on_join(self):
        pilot = self.pilot()
        pilot["issuers"][0]["documents"][0]["trial_registered_term_lexical_mentions"][0]["registered_term"] = "INVENTED-99"
        with self.assertRaises(ValueError):
            build_join(self.program, self.casebook, self.leads, pilot)

    def test_forged_rights_status_still_rejected(self):
        pilot = self.pilot()
        pilot["issuers"][0]["documents"][0]["verified_trial_development_rights"] = True
        with self.assertRaises(ValueError):
            build_join(self.program, self.casebook, self.leads, pilot)

    def test_unavailable_source_cannot_have_lexical_match(self):
        pilot = self.pilot()
        first = pilot["issuers"][0]["documents"][0]
        first["retrieval_status"] = "SOURCE_UNAVAILABLE"
        first["source_sha256"] = None
        with self.assertRaises(ValueError):
            build_join(self.program, self.casebook, self.leads, pilot)

    def test_duplicate_program_nct_fails_closed(self):
        self.program["items"][1]["nct_id"] = self.program["items"][0]["nct_id"]
        with self.assertRaises(ValueError):
            prepare_program_terms(self.program, self.casebook)

    def test_empty_issuer_scan_does_not_claim_no_commercial_rights(self):
        result = build_pilot(self.casebook, self.leads, fetch=lambda _: b"Unrelated company text",
                             program=self.program, max_issuers=1)
        self.assertEqual(result["trials_with_exact_registered_term_text_leads"], 0)
        self.assertEqual(result["independently_verified_current_rights"], 0)


if __name__ == "__main__":
    unittest.main()
