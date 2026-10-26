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
        self.assertEqual(r["issuer_rights_claim_evidence_linked_trials"], 32)
        self.assertEqual(r["claim_evidence_missing_or_unreviewed_trials"], 709)
        self.assertEqual(r["issuers_with_rights_claim_dossiers"], 8)
        self.assertEqual(r["asset_program_dossiers"], 10)

    def test_exact_32_nct_claim_links_and_no_other_unearned_claims(self):
        expected = {
            "ABVX": {"NCT05507203", "NCT05507216", "NCT05535946"},
            "ACHV": {"NCT04576949", "NCT05206370", "NCT06435221", "NCT07392125"},
            "MIRM": {"NCT06553768", "NCT06907290", "NCT07200908", "NCT07454837"},
            "CYTK": {"NCT04848506", "NCT05186818", "NCT05767346", "NCT06081894", "NCT06412666"},
            "ACAD": {"NCT04181723", "NCT04279314", "NCT04776746", "NCT04988867"},
            "IOVA": {"NCT05727904"},
            "BCRX": {"NCT03472040", "NCT03485911", "NCT03873116", "NCT04933721", "NCT05453968"},
            "AXSM": {"NCT03226522", "NCT04797715", "NCT04947553", "NCT06736509",
                     "NCT05059223", "NCT05113745"},
        }
        for ticker, ids in expected.items():
            actual = {x["nct_id"] for x in self.report["trials"]
                      if x["ticker"] == ticker
                      and x["research_claim_status"] == "ISSUER_DISCLOSED_ASSET_RIGHTS_CLAIM_LINKED"}
            self.assertEqual(actual, ids)
            for nct in ids:
                self.assertTrue(self.by_id[nct]["source_document_links_cataloged"])
        self.assertEqual(sum(not x["source_document_links_cataloged"]
                             for x in self.report["trials"]), 709)

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
        self.assertEqual(r["issuer_reported_future_pdufa_event_count"], 2)
        self.assertEqual(len(r["issuer_reported_future_pdufa_events"]), 2)
        e = next(x for x in r["issuer_reported_future_pdufa_events"] if x["ticker"] == "CYTK")
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
        self.assertEqual(len(original), 10)
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
        acad_index = next(i for i, p in enumerate(changed) if p["issuerTicker"] == "ACAD")
        affected = dict(changed[acad_index])
        trial_links = [dict(x) for x in affected["trialLinks"]]
        trial_links[0]["expectedRegistryStatus"] = "RECRUITING"
        affected["trialLinks"] = trial_links
        changed[acad_index] = affected
        with patch.object(rights, "collect_cases", return_value=changed):
            with self.assertRaisesRegex(ValueError, "PDUFA evidence check failed"):
                rights.build()

    def test_acad_lavender_and_lilac_are_existing_approval_studies(self):
        for nct, status in (("NCT04181723", "COMPLETED"),
                            ("NCT04279314", "COMPLETED")):
            row = self.by_id[nct]
            self.assertEqual(row["ticker"], "ACAD")
            self.assertEqual(row["linked_asset"], "trofinetide")
            self.assertEqual(row["saved_registry_status"], status)
            self.assertIn("RETT", row["regulatory_context"])
            self.assertIn("NEUREN_WORLDWIDE_EXCLUSIVE_LICENSE_WITH_MILESTONE_AND_ROYALTY_OBLIGATIONS",
                          row["material_risk_flags"])
            self.assertIn("EU_2026_DAYBU_AUTHORIZATION_NOT_PENDING_US_FDA_PDUFA",
                          row["material_risk_flags"])
            self.assertIsNone(row["issuer_reported_upcoming_pdufa_target"])
            self.assertIsNone(row["current_pdufa_target_date"])
            self.assertIsNone(row["qualified_pipeline"])

    def test_bcrx_apex_studies_and_europe_sale_do_not_create_new_us_pdufa(self):
        expected = {
            "NCT03485911": "COMPLETED",
            "NCT03472040": "COMPLETED",
            "NCT03873116": "COMPLETED",
            "NCT04933721": "ENROLLING_BY_INVITATION",
            "NCT05453968": "ACTIVE_NOT_RECRUITING",
        }
        for nct, status in expected.items():
            row = self.by_id[nct]
            self.assertEqual(row["ticker"], "BCRX")
            self.assertEqual(row["linked_asset"], "berotralstat")
            self.assertEqual(row["saved_registry_status"], status)
            self.assertIn("ORLADEYO_EU_BUSINESS_SOLD_TO_NEOPHARMED_OCTOBER_2025",
                          row["material_risk_flags"])
            self.assertIn("ORLADEYO_2026_10_21_US_ADULT_PELLET_APPROVAL_IS_COMPLETED_EVENT",
                          row["material_risk_flags"])
            self.assertIsNone(row["historical_issuer_reported_pdufa_target"])
            self.assertIsNone(row["issuer_reported_upcoming_pdufa_target"])
            self.assertFalse(row["issuer_reported_fda_acceptance"])
            self.assertIsNone(row["current_pdufa_target_date"])
            self.assertIsNone(row["qualified_pipeline"])
        self.assertIn("PEDIATRIC", self.by_id["NCT05453968"]["regulatory_context"])
        self.assertIn("JAPAN", self.by_id["NCT03873116"]["regulatory_context"])

    def test_bcrx_fake_registry_status_and_duplicate_asset_blocked(self):
        originals = rights.collect_cases()
        b_index = next(i for i, p in enumerate(originals) if p["issuerTicker"] == "BCRX")
        changed = [dict(p) for p in originals]
        bcrx = dict(changed[b_index])
        links = [dict(x) for x in bcrx["trialLinks"]]
        links[0]["expectedRegistryStatus"] = "RECRUITING"
        bcrx["trialLinks"] = links
        changed[b_index] = bcrx
        with patch.object(rights, "collect_cases", return_value=changed):
            with self.assertRaisesRegex(ValueError, "PDUFA evidence check failed"):
                rights.build()
        same_asset = list(originals) + [dict(originals[b_index])]
        with patch.object(rights, "collect_cases", return_value=same_asset):
            with self.assertRaisesRegex(ValueError, "duplicate program"):
                rights.build()

    def test_axsm_completed_official_fda_event_not_2026_upcoming_pdufa(self):
        report = self.report
        self.assertEqual(report["official_fda_confirmed_completed_historical_action_count"], 1)
        self.assertEqual(report["official_fda_confirmed_completed_historical_action_supporting_trial_count"], 2)
        events = report["official_fda_confirmed_completed_historical_actions"]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["issuer_ticker"], "AXSM")
        self.assertEqual(event["asset"], "AXS-05")
        self.assertEqual(event["action_date"], "2026-04-30")
        self.assertEqual(event["action_type"], "APPROVED_SUPPLEMENTAL_INDICATION")
        self.assertFalse(event["is_current_pending_fda_action"])
        self.assertIn("fda.gov", event["fda_primary_source_url"])
        self.assertEqual(set(event["fda_press_explicit_supporting_nct_ids"]),
                         {"NCT03226522", "NCT04947553"})
        for nct in event["fda_press_explicit_supporting_nct_ids"]:
            trial = self.by_id[nct]
            self.assertEqual(trial["linked_asset"], "AXS-05")
            self.assertTrue(trial["official_fda_confirmed_completed_historical_action"])
            self.assertEqual(trial["historical_fda_action_date"], "2026-04-30")
            self.assertIsNone(trial["issuer_reported_upcoming_pdufa_target"])
            self.assertIsNone(trial["current_pdufa_target_date"])
        for nct in ("NCT04797715", "NCT06736509"):
            trial = self.by_id[nct]
            self.assertEqual(trial["linked_asset"], "AXS-05")
            self.assertFalse(trial["official_fda_confirmed_completed_historical_action"])
            self.assertIsNone(trial["historical_fda_action_date"])
            self.assertIsNone(trial["current_pdufa_target_date"])
        self.assertEqual(report["issuer_reported_future_pdufa_event_count"], 2)
        self.assertEqual({x["ticker"] for x in report["issuer_reported_future_pdufa_events"]}, {"AXSM", "CYTK"})
        self.assertEqual(report["independently_verified_current_fda_pdufa_count"], 0)
        self.assertIsNone(report["qualified_pipeline_count"])

    def test_axsm_axs12_narcolepsy_novel_future_nda_is_distinct_from_axs05_past_approval(self):
        r = self.report
        by_ticker = [e for e in r["issuer_reported_future_pdufa_events"]
                     if e["ticker"] == "AXSM"]
        self.assertEqual(len(by_ticker), 1)
        e = by_ticker[0]
        self.assertEqual(e["nct_id"], "NCT05059223")
        self.assertEqual(e["asset"], "AXS-12")
        self.assertEqual(e["issuer_reported_target_date"], "2027-05-01")
        self.assertEqual(e["supporting_trial_nct_ids"], ["NCT05059223", "NCT05113745"])
        self.assertTrue(e["issuer_reported_accepted_application"])
        self.assertIn("www.sec.gov", e["issuer_primary_source_url"])
        self.assertFalse(e["agency_independent_verification"])
        self.assertEqual(len(r["official_fda_confirmed_completed_historical_actions"]), 1)
        for nct, study in (("NCT05059223", "SYMPHONY"), ("NCT05113745", "ENCORE")):
            t = self.by_id[nct]
            self.assertEqual(t["ticker"], "AXSM")
            self.assertEqual(t["linked_asset"], "AXS-12")
            self.assertTrue(any(study in src["assertion"] for src in t["source_document_links_cataloged"]))
            self.assertEqual(t["issuer_reported_application_supporting_nct_ids"],
                             ["NCT05059223", "NCT05113745"])
            self.assertFalse(t["official_fda_confirmed_completed_historical_action"])
            self.assertFalse(t["independent_fda_pdufa_target_verified"])
            self.assertIsNone(t["current_pdufa_target_date"])
            self.assertIsNone(t["qualified_pipeline"])
            self.assertIn("PFIZER_EXCLUSIVE_US_DATA_IP_LICENSE_NOT_UNENCUMBERED_GLOBAL_RIGHTS",
                          t["material_risk_flags"])
            self.assertIn("PFIZER_MILESTONES_UP_TO_323M_AND_TIERED_ROYALTIES",
                          t["material_risk_flags"])
        self.assertEqual(self.by_id["NCT05059223"]["issuer_reported_upcoming_pdufa_target"],
                         "2027-05-01")
        self.assertIsNone(self.by_id["NCT05113745"]["issuer_reported_upcoming_pdufa_target"])

    def test_axsm_fake_extra_pdufa_or_external_supporting_nct_is_rejected(self):
        originals = rights.collect_cases()
        ai = next(i for i, p in enumerate(originals)
                  if p["issuerTicker"] == "AXSM" and p["asset"] == "AXS-12")
        for modification in ("BAD_SUPPORTING_ID", "FALSE_FDA_ACCEPTANCE"):
            cases = [dict(p) for p in originals]
            target = dict(cases[ai])
            if modification == "BAD_SUPPORTING_ID":
                target["issuerReportedNdaEvidenceSupportingNctIds"] = [
                    "NCT05059223", "NCT09999999"]
                expected = "supporting trial identities"
            else:
                linked = [dict(x) for x in target["trialLinks"]]
                linked[0]["issuerReportedFdaAcceptance"] = False
                target["trialLinks"] = linked
                expected = "PDUFA needs dated primary-source"
            cases[ai] = target
            with patch.object(rights, "collect_cases", return_value=cases):
                with self.assertRaisesRegex(ValueError, expected):
                    rights.build()

    def test_fake_or_future_official_fda_approval_is_rejected(self):
        programs = rights.collect_cases()
        original = next(i for i, p in enumerate(programs) if p["issuerTicker"] == "AXSM")
        for update in ({"actionDate": "2026-12-01"},
                       {"agencyPrimarySourceUrl": "https://example.com/no-fda-source"},
                       {"currentPendingFDAAction": True},
                       {"agencyPressExplicitSupportingNctIds": ["NCT09999999"]}):
            altered = [dict(p) for p in programs]
            changed = dict(altered[original])
            changed["officialFdaHistoricalAction"] = dict(
                changed["officialFdaHistoricalAction"], **update)
            altered[original] = changed
            with patch.object(rights, "collect_cases", return_value=altered):
                with self.assertRaisesRegex(ValueError, "Official completed FDA historical action"):
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
