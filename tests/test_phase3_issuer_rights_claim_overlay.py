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
        self.assertEqual(r["issuer_rights_claim_evidence_linked_trials"], 11)
        self.assertEqual(r["claim_evidence_missing_or_unreviewed_trials"], 730)
        self.assertEqual(r["issuers_with_rights_claim_dossiers"], 3)
        self.assertEqual(r["asset_program_dossiers"], 4)

    def test_exact_11_nct_claim_links_and_no_other_unearned_claims(self):
        expected = {
            "ABVX": {"NCT05507203", "NCT05507216", "NCT05535946"},
            "ACHV": {"NCT04576949", "NCT05206370", "NCT06435221", "NCT07392125"},
            "MIRM": {"NCT06553768", "NCT06907290", "NCT07200908", "NCT07454837"},
        }
        for ticker, ids in expected.items():
            actual = {x["nct_id"] for x in self.report["trials"]
                      if x["ticker"] == ticker
                      and x["research_claim_status"] == "ISSUER_DISCLOSED_ASSET_RIGHTS_CLAIM_LINKED"}
            self.assertEqual(actual, ids)
            for nct in ids:
                self.assertTrue(self.by_id[nct]["source_document_links_cataloged"])
        self.assertEqual(sum(not x["source_document_links_cataloged"]
                             for x in self.report["trials"]), 730)

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

    def test_wrong_source_identity_and_duplicate_nct_are_blocked(self):
        original = rights.collect_cases()
        wrong = [dict(x) for x in original]
        wrong[1] = dict(wrong[1], issuerCik="0000000000")
        with patch.object(rights, "collect_cases", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "issuer"):
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
