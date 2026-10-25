"""Contracts for two evidence-input grades and KEYNOTE-024 protocol time ordering."""
import copy
import unittest

from app.scientific_protocol_readiness import (
    BLOCKED, REVIEW_REQUIRED, SOURCE_SUPPORTED,
    PROTOCOL_URL, grade_review_inputs, keynote024_protocol_readiness,
)


def stub_dossier():
    return {
        "nct_id": "NCT02142738", "source_sha256": "a" * 64,
        "read_only": True, "overall_score": None, "fda_approval_probability": None,
    }


def stub_published():
    return {
        "nct_id": "NCT02142738", "randomized_population": 305,
        "overall_score": None, "fda_approval_probability": None,
        "analysis_snapshots": [
            {
                "analysis_id": "keynote024_initial_2016", "nct_id": "NCT02142738",
                "source_id": "27718847", "data_cutoff_date": "2016-05-09",
                "arm_counts_randomized": {"pembrolizumab": 154, "chemotherapy": 151},
                "effects": {
                    "progression_free_survival": {
                        "analysis_role": "prespecified_primary",
                        "hazard_ratio": 0.5, "hazard_ratio_95pct_ci": [0.37, 0.68],
                        "p_value": "<0.001",
                    },
                    "overall_survival": {
                        "hazard_ratio": 0.60, "hazard_ratio_95pct_ci": [0.41, 0.89],
                    },
                },
                "safety": {"treatment_related_adverse_events_grade_3_to_5_percent": {
                    "pembrolizumab": 26.6, "chemotherapy": 53.3,
                }},
            },
            {"analysis_id": "keynote024_pros_2017", "nct_id": "NCT02142738",
             "source_id": "29129441"},
            {"analysis_id": "keynote024_five_year_2021", "nct_id": "NCT02142738",
             "source_id": "33872070", "effective_crossover_percent_from_chemotherapy": 66.0},
        ],
    }


class ProtocolReadinessTests(unittest.TestCase):
    def test_incomplete_inputs_and_high_reluctance_are_not_success_grades(self):
        r = keynote024_protocol_readiness(stub_dossier(), stub_published())
        self.assertEqual(r["nctId"], "NCT02142738")
        self.assertEqual(r["inputReadiness"]["grade"], "FAIL")
        self.assertEqual(r["inputReadiness"]["status"], "NOT_READY_FOR_FULL_ANALYSIS")
        self.assertEqual(r["inputReadiness"]["criteriaTotal"], 12)
        self.assertEqual(r["inputReadiness"]["sourceSupported"], 5)
        self.assertEqual(r["inputReadiness"]["unresolved"], 7)
        self.assertEqual(r["reluctance"]["grade"], "HIGH")
        self.assertIn("pre_cutoff_protocol", r["reluctance"]["criticalBlockedIds"])
        self.assertIn("full_regulatory_cmc", r["reluctance"]["criticalBlockedIds"])
        self.assertEqual(r["protocol"]["documentDate"], "2017-12-20")
        self.assertEqual(r["protocol"]["interimDataCutoff"], "2016-05-09")
        self.assertIn("Japan-only", r["protocol"]["regionalScope"])
        self.assertTrue(r["protocol"]["afterInterimDataCutoff"])
        self.assertTrue(r["protocol"]["notProofOf2016Prespecification"])
        self.assertEqual(r["protocol"]["url"], PROTOCOL_URL)
        self.assertTrue(r["preliminarySourceReviewAllowed"])
        self.assertFalse(r["independentReanalysisPerformed"])
        self.assertIsNone(r["scientificScore"])
        self.assertIsNone(r["fdaApprovalProbability"])
        self.assertFalse(r["tradingActionsEnabled"])
        self.assertFalse(r["fsFaModified"])

    def test_2016_original_supplement_listing_does_not_unlock_preinterim_sap(self):
        r = keynote024_protocol_readiness(stub_dossier(), stub_published())
        source = r["original2016ProtocolSource"]
        self.assertEqual(source["listedFilename"], "nejmoa1606774_protocol.pdf")
        self.assertEqual(source["sourceUrl"],
                         "https://www.nejm.org/doi/full/10.1056/nejmoa1606774")
        self.assertTrue(source["listingVerified"])
        self.assertFalse(source["pdfContentReviewed"])
        self.assertFalse(source["effectiveAmendmentsVerified"])
        self.assertFalse(source["originalSignedSapVerified"])
        self.assertFalse(source["preInterimAlphaSpendingVerified"])
        self.assertTrue(source["blocking"])
        self.assertEqual(source["status"], "source_listed_not_adjudicated")
        pre = next(c for c in r["checks"] if c["id"] == "pre_cutoff_protocol")
        self.assertEqual(pre["status"], BLOCKED)
        self.assertTrue(pre["critical"])
        self.assertEqual(len(pre["sources"]), 3)
        self.assertTrue(any("Supplementary Material" in x["locator"]
                            for x in pre["sources"]))
        self.assertEqual(r["inputReadiness"]["grade"], "FAIL")
        self.assertEqual(r["reluctance"]["grade"], "HIGH")
        self.assertIsNone(r["scientificScore"])
        self.assertIsNone(r["fdaApprovalProbability"])

    def test_all_checks_have_vetted_links_and_locators(self):
        r = keynote024_protocol_readiness(stub_dossier(), stub_published())
        ids = [c["id"] for c in r["checks"]]
        self.assertEqual(len(set(ids)), len(ids))
        for check in r["checks"]:
            self.assertIn(check["status"], (SOURCE_SUPPORTED, BLOCKED, REVIEW_REQUIRED))
            self.assertTrue(check["sources"])
            for source in check["sources"]:
                self.assertTrue(source["url"].startswith("https://"))
                self.assertTrue(source["locator"])
        alpha = next(c for c in r["checks"] if c["id"] == "multiplicity_alpha")
        self.assertIn("0.0118", alpha["finding"])
        self.assertTrue(alpha["critical"])

    def test_grade_can_pass_only_when_all_inputs_are_source_supported(self):
        original = keynote024_protocol_readiness(stub_dossier(), stub_published())
        hypothetical = [{**c, "status": SOURCE_SUPPORTED} for c in original["checks"]]
        grade = grade_review_inputs(hypothetical)
        self.assertEqual(grade["inputReadiness"]["grade"], "PASS")
        self.assertEqual(grade["reluctance"]["grade"], "LOW")
        self.assertFalse(grade["fullTwentyLevelAnalysisCompleted"])
        self.assertIsNone(grade["scientificScore"])
        self.assertIsNone(grade["fdaApprovalProbability"])
        self.assertEqual(keynote024_protocol_readiness(
            stub_dossier(), stub_published()
        )["inputReadiness"]["grade"], "FAIL")

    def test_reluctance_is_separate_from_pass_fail(self):
        checks = keynote024_protocol_readiness(stub_dossier(), stub_published())["checks"]
        b_removed = [{**c, "status": SOURCE_SUPPORTED if c["status"] == BLOCKED
                      else c["status"]} for c in checks]
        self.assertEqual(grade_review_inputs(b_removed)["reluctance"]["grade"], "ELEVATED")
        critical_resolved = [{**c, "status": SOURCE_SUPPORTED if c["critical"]
                             else c["status"]} for c in checks]
        graded = grade_review_inputs(critical_resolved)
        self.assertEqual(graded["inputReadiness"]["grade"], "FAIL")
        self.assertEqual(graded["reluctance"]["grade"], "MODERATE")

    def test_tampered_identity_efficacy_safety_crossover_block_appraisal(self):
        mutations = [
            lambda a,b: a.__setitem__("nct_id", "NCT87654321"),
            lambda a,b: a.__setitem__("source_sha256", "bad"),
            lambda a,b: a.__setitem__("overall_score", 99),
            lambda a,b: b["analysis_snapshots"][0].__setitem__("source_id", "99999"),
            lambda a,b: b["analysis_snapshots"][0]["effects"]["progression_free_survival"].__setitem__("hazard_ratio", 0.85),
            lambda a,b: b["analysis_snapshots"][0]["safety"]["treatment_related_adverse_events_grade_3_to_5_percent"].__setitem__("chemotherapy", 1.0),
            lambda a,b: b["analysis_snapshots"][2].__setitem__("effective_crossover_percent_from_chemotherapy", 0),
        ]
        for change in mutations:
            d,p = stub_dossier(),stub_published()
            change(d,p)
            with self.subTest(change=repr(change)),self.assertRaises(ValueError):
                keynote024_protocol_readiness(d,p)

    def test_checklist_rejects_fake_sources_and_duplicate_items(self):
        checks = keynote024_protocol_readiness(stub_dossier(), stub_published())["checks"]
        with self.assertRaises(ValueError):
            grade_review_inputs([checks[0], checks[0]])
        fake = copy.deepcopy(checks)
        fake[0]["sources"][0]["url"] = "https://attacker.invalid/clinicaltrial"
        with self.assertRaises(ValueError):
            grade_review_inputs(fake)
        fake = copy.deepcopy(checks)
        fake[0]["status"] = "FDA_APPROVAL_LIKELY"
        with self.assertRaises(ValueError):
            grade_review_inputs(fake)
        with self.assertRaises(ValueError):
            grade_review_inputs([])


if __name__ == "__main__":
    unittest.main()
