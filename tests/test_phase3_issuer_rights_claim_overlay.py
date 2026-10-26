"""Guardrails for source-linked issuer rights-claim research across 741 original NCTs."""
import csv
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_phase3_issuer_rights_claim_overlay as rights


class RightsEvidenceOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = rights.build()
        cls.by_id = {r["nct_id"]: r for r in cls.report["trials"]}

    def test_full_denominators_and_correct_claim_scoping(self):
        r = self.report
        self.assertEqual(r["denominator_trials"], 741)
        self.assertEqual(r["denominator_issuers"], 130)
        self.assertEqual(len(r["trials"]), 741)
        self.assertEqual(len(self.by_id), 741)
        self.assertEqual(len({x["ticker"] for x in r["trials"]}), 130)
        self.assertEqual(r["issuer_rights_claim_evidence_linked_trials"], 19)
        self.assertEqual(r["claim_evidence_missing_or_unreviewed_trials"], 722)
        self.assertEqual(r["issuers_with_rights_claim_dossiers"], 6)
        self.assertEqual(r["asset_program_dossiers"], 7)

    def test_exact_19_nct_claim_links_and_no_other_unearned_claims(self):
        expected = {
            "ABVX": {"NCT05507203", "NCT05507216", "NCT05535946"},
            "ACHV": {"NCT04576949", "NCT05206370", "NCT06435221", "NCT07392125"},
            "MIRM": {"NCT06553768", "NCT06907290", "NCT07200908", "NCT07454837"},
            "CYTK": {"NCT04848506", "NCT05186818", "NCT05767346", "NCT06081894", "NCT06412666"},
            "ACAD": {"NCT04776746", "NCT04988867"},
            "IOVA": {"NCT05727904"},
        }
        for ticker, ids in expected.items():
            actual = {x["nct_id"] for x in self.report["trials"]
                      if x["ticker"] == ticker
                      and x["research_claim_status"] == "ISSUER_DISCLOSED_ASSET_RIGHTS_CLAIM_LINKED"}
            self.assertEqual(actual, ids)
            for nct in ids:
                self.assertTrue(self.by_id[nct]["source_document_links_cataloged"])
        self.assertEqual(sum(not x["source_document_links_cataloged"]
                             for x in self.report["trials"]), 722)

    def test_no_trial_has_unearned_legal_or_fda_promotion(self):
        r = self.report
        self.assertEqual(r["independently_adjudicated_current_legal_rights_count"], 0)
        self.assertEqual(r["independently_verified_current_fda_pdufa_count"], 0)
        self.assertIsNone(r["qualified_pipeline_count"])
        self.assertTrue(all(
            x["independently_verified_current_legal_rights"] is False
            and x["independent_fda_pdufa_target_verified"] is False
            and x["current_pdufa_target_date"] is None
            and x["qualified_pipeline"] is None for x in r["trials"]
        ))

    def test_achv_material_dispute_and_historical_not_current_target(self):
        for nct in ("NCT04576949", "NCT05206370", "NCT06435221", "NCT07392125"):
            x = self.by_id[nct]
            self.assertIn("SOPHARMA_ARBITRATION_CONTRACT_DISPUTE", x["material_risk_flags"])
            self.assertIn("FDA_2026_CRL_MANUFACTURING", x["material_risk_flags"])
            self.assertEqual(x["linked_asset"], "cytisinicline")
        for nct in ("NCT04576949", "NCT05206370"):
            x = self.by_id[nct]
            self.assertEqual(x["historical_issuer_reported_pdufa_target"], "2026-06-20")
            self.assertIsNone(x["current_pdufa_target_date"])
        self.assertIsNone(self.by_id["NCT07392125"]["historical_issuer_reported_pdufa_target"])

    def test_mirm_indication_licensing_and_planned_submission_not_pdufa(self):
        expand = self.by_id["NCT06553768"]
        self.assertEqual(expand["linked_asset"], "maralixibat")
        self.assertIn("SNDA_EXPAND_PLANNED", expand["regulatory_context"])
        self.assertIn("TAKEDA_JAPAN_TERRITORY_PARTNERSHIP_AND_INDICATION_LICENSE",
                      expand["material_risk_flags"])
        for nct in ("NCT06907290", "NCT07200908", "NCT07454837"):
            x = self.by_id[nct]
            self.assertEqual(x["linked_asset"], "brelovitug")
            self.assertIn("NOVARTIS_LICENSE_ROYALTIES_AND_MILESTONES", x["material_risk_flags"])
            self.assertIsNone(x["current_pdufa_target_date"])

    def test_cytk_maple_upcoming_snda_is_indication_specific_issuer_reported_only(self):
        r = self.report
        self.assertEqual(r["issuer_reported_future_pdufa_event_count"], 1)
        self.assertEqual(len(r["issuer_reported_future_pdufa_events"]), 1)
        e = r["issuer_reported_future_pdufa_events"][0]
        self.assertEqual(e["nct_id"], "NCT05767346")
        self.assertEqual(e["ticker"], "CYTK")
        self.assertEqual(e["asset"], "aficamten")
        self.assertIn("obstructive", e["indication"])
        self.assertNotIn("non-obstructive", e["indication"])
        self.assertEqual(e["issuer_reported_target_date"], "2026-11-14")
        self.assertTrue(e["issuer_reported_accepted_application"])
        self.assertIn("ir.cytokinetics.com", e["issuer_primary_source_url"])
        self.assertFalse(e["agency_independent_verification"])
        maple = self.by_id["NCT05767346"]
        self.assertTrue(maple["issuer_reported_fda_acceptance"])
        self.assertIsNone(maple["current_pdufa_target_date"])
        for nct in ("NCT05186818", "NCT06081894", "NCT06412666", "NCT04848506"):
            item = self.by_id[nct]
            self.assertEqual(item["linked_asset"], "aficamten")
            self.assertIsNone(item["issuer_reported_upcoming_pdufa_target"])
            self.assertFalse(item["issuer_reported_fda_acceptance"])
            self.assertIsNone(item["current_pdufa_target_date"])
        self.assertIn("CHINA_TAIWAN_EXCLUSIVE_LICENSE_TO_SANOFI", maple["material_risk_flags"])
        self.assertIn("JAPAN_EXCLUSIVE_LICENSE_TO_BAYER_WITH_RESERVED_CLINICAL_STUDY_RIGHTS", maple["material_risk_flags"])

    def test_cytk_fake_or_stale_pdufa_claim_is_rejected(self):
        original = rights.collect_cases()
        self.assertEqual(len(original), 7)
        bad = [dict(p) for p in original]
        cy_index = next(i for i, p in enumerate(bad) if p["issuerTicker"] == "CYTK")
        cy = dict(bad[cy_index])
        links = [dict(x) for x in cy["trialLinks"]]
        maple = next(x for x in links if x["nctId"] == "NCT05767346")
        maple["issuerReportedCurrentPdufaDate"] = "2026-09-01"
        cy["trialLinks"] = links
        bad[cy_index] = cy
        with patch.object(rights, "collect_cases", return_value=bad):
            with self.assertRaisesRegex(ValueError, "PDUFA"):
                rights.build()

    def test_acad_terminated_rett_studies_are_not_future_pdufa_candidates(self):
        for nct in ("NCT04776746", "NCT04988867"):
            x = self.by_id[nct]
            self.assertEqual(x["ticker"], "ACAD")
            self.assertEqual(x["linked_asset"], "trofinetide")
            self.assertEqual(x["saved_registry_status"], "TERMINATED")
            self.assertIn("TERMINATED", x["regulatory_context"])
            self.assertIn("NEUREN_WORLDWIDE_EXCLUSIVE_LICENSE_WITH_MILESTONE_AND_ROYALTY_OBLIGATIONS", x["material_risk_flags"])
            self.assertIsNone(x["issuer_reported_upcoming_pdufa_target"])
            self.assertIsNone(x["current_pdufa_target_date"])
            self.assertIsNone(x["qualified_pipeline"])

    def test_iova_tilvance_active_trial_has_mixed_nih_rights_and_no_pdufa(self):
        x = self.by_id["NCT05727904"]
        self.assertEqual(x["ticker"], "IOVA")
        self.assertEqual(x["linked_asset"], "lifileucel")
        self.assertEqual(x["saved_registry_status"], "RECRUITING")
        self.assertIn("FRONTLINE_MELANOMA", x["regulatory_context"])
        self.assertIn("NIH_TIL_LICENSE_MIXED_EXCLUSIVE_COEXCLUSIVE_NONEXCLUSIVE_SCOPES", x["material_risk_flags"])
        self.assertIn("FRONTLINE_MELANOMA_COMBINATION_REQUIRES_SEPARATE_FDA_EVIDENCE", x["material_risk_flags"])
        self.assertIsNone(x["issuer_reported_upcoming_pdufa_target"])
        self.assertIsNone(x["current_pdufa_target_date"])
        self.assertIsNone(x["qualified_pipeline"])

    def test_acad_iova_saved_registry_status_cannot_be_falsified(self):
        original = rights.collect_cases()
        changed = [dict(p) for p in original]
        affected = dict(changed[-2])
        trial_links = [dict(x) for x in affected["trialLinks"]]
        trial_links[0]["expectedRegistryStatus"] = "RECRUITING"
        affected["trialLinks"] = trial_links
        changed[-2] = affected
        with patch.object(rights, "collect_cases", return_value=changed):
            with self.assertRaisesRegex(ValueError, "PDUFA evidence check failed"):
                rights.build()

    def test_wrong_source_identity_and_duplicate_nct_are_blocked(self):
        original = rights.collect_cases()
        wrong = [dict(x) for x in original]
        wrong[1] = dict(wrong[1], issuerCik="0000000000")
        with patch.object(rights, "collect_cases", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "Issuer asset CIK"):
                rights.build()
        duplicate = [dict(x) for x in original]
        duplicate[1] = dict(duplicate[1], trialLinks=original[1]["trialLinks"] + [
            dict(original[1]["trialLinks"][0])])
        with patch.object(rights, "collect_cases", return_value=duplicate):
            with self.assertRaisesRegex(ValueError, "Duplicate NCT"):
                rights.build()

    def test_attempted_rights_or_pdufa_promotion_is_rejected(self):
        original = rights.collect_cases()
        changed = [dict(x) for x in original]
        changed[1] = dict(changed[1], rightsIndependentlyAdjudicated=True)
        with patch.object(rights, "collect_cases", return_value=changed):
            with self.assertRaisesRegex(ValueError, "independently adjudicate"):
                rights.build()
        changed = [dict(x) for x in original]
        changed[1] = dict(changed[1], trialLinks=[
            dict(original[1]["trialLinks"][0], currentPdufaTargetVerified="2027-07-01")
        ] + original[1]["trialLinks"][1:])
        with patch.object(rights, "collect_cases", return_value=changed):
            with self.assertRaisesRegex(ValueError, "PDUFA evidence"):
                rights.build()


if __name__ == "__main__":
    unittest.main()
