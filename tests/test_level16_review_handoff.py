"""Fail-closed tests for the 32-trial, six-level scientific review handoff."""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/medical"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


handoff = load("level16_review_handoff")
chronology = load("level16_orca2_statistical_timeline")


def inputs():
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    return (
        read(handoff.COVERAGE), read(handoff.ROSTER), read(handoff.APPLICATIONS),
        chronology.assess(read(handoff.ORCA2)),
    )


class Level16ReviewHandoffTests(unittest.TestCase):
    def setUp(self):
        self.coverage, self.roster, self.applications, self.chronology = inputs()

    def build(self):
        return handoff.build(self.coverage, self.roster, self.applications, self.chronology)

    def test_32_exact_focus_and_192_levels_remain_unreviewed(self):
        packet = self.build()
        self.assertEqual(packet["focusTrialCount"], 32)
        self.assertEqual(packet["provisionalApplicationCycleCount"], 23)
        self.assertEqual(packet["provisionallyMappedTrialCount"], 29)
        self.assertEqual(packet["unmappedTrialCount"], 3)
        self.assertEqual(packet["reviewPacketsPrepared"], 32)
        self.assertEqual(packet["independentlyAuthenticatedSources"], 0)
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(packet["actualApprovalProbabilities"], 0)
        self.assertFalse(packet["stagingActivated"])
        self.assertEqual(sum(len(t["levels"]) for t in packet["trials"]), 192)
        for trial in packet["trials"]:
            self.assertEqual(trial["actualCompletedLevels"], 0)
            self.assertEqual(trial["actualIndependentScientificReviews"], 0)
            self.assertFalse(trial["readyForIndependentFinalAdjudication"])
            self.assertIsNone(trial["approvalProbability"])
            for level in trial["levels"]:
                self.assertFalse(level["completionPermitted"])
                self.assertIsNone(level["score"])
                self.assertIsNone(level["approvalProbability"])
                self.assertIsNone(level["fdaOutcomeJudgment"])
                self.assertEqual(level["independentScientificReviewStatus"], "NOT_ADJUDICATED")
                self.assertEqual(level["sourceAuthenticationStatus"],
                                 "NOT_INDEPENDENTLY_AUTHENTICATED")

    def test_publication_outcomes_only_enter_orca2_levels_3_4_and_6_as_unreviewed(self):
        publication = json.loads(handoff.ORCA2_PUBLICATION.read_text(encoding="utf-8"))
        packet = handoff.build(self.coverage, self.roster, self.applications,
                               self.chronology, orca_publication=publication)
        trial = next(t for t in packet["trials"] if t["nct"] == "NCT04576949")
        self.assertIsNone(trial["levels"][0]["publicationFindingsUnreviewed"])
        self.assertIsNone(trial["levels"][1]["publicationFindingsUnreviewed"])
        self.assertIsNone(trial["levels"][4]["publicationFindingsUnreviewed"])
        for level in (2, 3, 5):
            report = trial["levels"][level]["publicationFindingsUnreviewed"]
            self.assertFalse(report["scientificallyAdjudicated"])
            self.assertFalse(report["sourceIndependentlyAuthenticated"])
            self.assertEqual(report["publicationUrl"],
                             "https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/")
            self.assertFalse(trial["levels"][level]["completionPermitted"])
        self.assertEqual(len(trial["levels"][2]["publicationFindingsUnreviewed"][
            "reportedEfficacyComparisons"]), 4)
        self.assertEqual(trial["levels"][2]["publicationFindingsUnreviewed"][
            "reportedSafetyObservations"]["seriousAdverseEvents"]["cytisinicline"], 18)
        self.assertTrue(trial["levels"][5]["publicationFindingsUnreviewed"][
            "reportedClinicalLimitations"])
        self.assertIsNone(trial["fdaOutcomeJudgment"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        other = next(t for t in packet["trials"] if t["nct"] != "NCT04576949")
        self.assertTrue(all(x["publicationFindingsUnreviewed"] is None for x in other["levels"]))

    def test_forged_publication_results_cannot_enter_the_review_packet(self):
        publication = json.loads(handoff.ORCA2_PUBLICATION.read_text(encoding="utf-8"))
        publication["efficacy"][0]["activePct"] = 100.0
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, orca_publication=publication)
        publication = json.loads(handoff.ORCA2_PUBLICATION.read_text(encoding="utf-8"))
        publication["sourceIndependentlyAuthenticated"] = True
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, orca_publication=publication)

    def test_orca3_original_replication_research_is_unreviewed_not_cross_trial(self):
        publication = json.loads(handoff.ORCA3_PUBLICATION.read_text(encoding="utf-8"))
        packet = handoff.build(self.coverage, self.roster, self.applications, self.chronology,
                               orca3_publication=publication)
        trial = next(x for x in packet["trials"] if x["nct"] == "NCT05206370")
        level3 = trial["levels"][2]["publicationFindingsUnreviewed"]
        self.assertEqual(len(level3["reportedEfficacyComparisons"]), 4)
        self.assertEqual(level3["reportedEfficacyComparisons"][0]["activeAbstinent"], 39)
        self.assertEqual(level3["reportedEfficacyComparisons"][1]["activePct"], 30.3)
        self.assertEqual(len(level3["publicationTextDiscrepanciesUnreviewed"]), 2)
        self.assertEqual(level3["reportedSafetyObservations"]["seriousAdverseEvents"]["cytisinicline"], 16)
        self.assertIn("confidence-interval", " ".join(trial["levels"][2]["openReviewQuestions"]))
        for idx in (2, 3, 5):
            self.assertFalse(trial["levels"][idx]["completionPermitted"])
            self.assertFalse(trial["levels"][idx]["publicationFindingsUnreviewed"]["scientificallyAdjudicated"])
        self.assertIsNone(trial["levels"][4]["publicationFindingsUnreviewed"])
        self.assertEqual(trial["actualCompletedLevels"], 0)
        orca2 = next(x for x in packet["trials"] if x["nct"] == "NCT04576949")
        self.assertIsNone(orca2["levels"][2]["publicationFindingsUnreviewed"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)

    def test_orca3_source_content_swap_or_forged_approval_rejected(self):
        pub = json.loads(handoff.ORCA3_PUBLICATION.read_text(encoding="utf-8"))
        pub["sourceIndependentlyAuthenticated"] = True
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications, self.chronology,
                          orca3_publication=pub)
        pub = json.loads(handoff.ORCA3_PUBLICATION.read_text(encoding="utf-8"))
        pub["endpoints"][0]["activeCount"] = 999
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications, self.chronology,
                          orca3_publication=pub)

    def test_maple_hcm_continuous_outcomes_not_abstinence_or_cross_trial(self):
        maple = json.loads(handoff.MAPLE_HCM.read_text(encoding="utf-8"))
        packet = handoff.build(self.coverage, self.roster, self.applications,
                               self.chronology, maple_publication=maple)
        trial = next(x for x in packet["trials"] if x["nct"] == "NCT05767346")
        self.assertEqual(trial["ticker"], "CYTK")
        self.assertEqual(trial["phaseUnreviewed"], ["PHASE3"])
        clinical = trial["levels"][2]["publicationFindingsUnreviewed"]
        self.assertEqual(clinical["endpointDataType"],
                         "CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE")
        self.assertEqual(clinical["continuousPrimaryEndpointUnreviewed"][
            "adjustedBetweenGroupMeanDifference"], 2.3)
        self.assertEqual(clinical["continuousPrimaryEndpointUnreviewed"]["unit"],
                         "mL/kg/min")
        self.assertEqual(len(clinical["secondaryContinuousComparisonsUnreviewed"]), 6)
        self.assertEqual(clinical["reportedEfficacyComparisons"], [])
        self.assertEqual(clinical["reportedSafetyObservations"][
            "seriousAdverseEvents"]["aficamten"], 7)
        for index in (2, 3, 5):
            item = trial["levels"][index]
            self.assertIsNotNone(item["publicationFindingsUnreviewed"])
            self.assertFalse(item["completionPermitted"])
            self.assertFalse(item["publicationFindingsUnreviewed"]["scientificallyAdjudicated"])
            self.assertIsNone(item["score"])
            self.assertIsNone(item["approvalProbability"])
        self.assertIsNone(trial["levels"][4]["publicationFindingsUnreviewed"])
        self.assertIsNone(trial["levels"][0]["publicationFindingsUnreviewed"])
        self.assertEqual(trial["actualCompletedLevels"], 0)
        orca3 = next(x for x in packet["trials"] if x["nct"] == "NCT05206370")
        self.assertIsNone(orca3["levels"][2]["publicationFindingsUnreviewed"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        md = handoff.markdown(packet)
        self.assertIn("REPORTED CONTINUOUS PRIMARY ENDPOINT", md)
        self.assertIn("NOT the original NEJM study report", md)
        self.assertIn("2.3 mL/kg/min", md)

    def test_maple_hcm_forged_original_source_review_and_wrong_units_rejected(self):
        maple = json.loads(handoff.MAPLE_HCM.read_text(encoding="utf-8"))
        maple["sourceIndependentlyAuthenticated"] = True
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, maple_publication=maple)
        maple = json.loads(handoff.MAPLE_HCM.read_text(encoding="utf-8"))
        maple["primaryEndpoint"]["unit"] = "%"
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, maple_publication=maple)
        maple = json.loads(handoff.MAPLE_HCM.read_text(encoding="utf-8"))
        maple["nct"] = "NCT04576949"
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, maple_publication=maple)

    def test_origin3_interim_primary_and_final_secondary_renal_evidence_are_distinct(self):
        renal = json.loads(handoff.ORIGIN3_RENAL.read_text(encoding="utf-8"))
        packet = handoff.build(self.coverage, self.roster, self.applications,
                               self.chronology, origin3_renal=renal)
        trial = next(x for x in packet["trials"] if x["nct"] == "NCT04716231")
        self.assertEqual(trial["ticker"], "VERA")
        self.assertEqual(trial["phaseUnreviewed"], ["PHASE3"])
        self.assertEqual(len(trial["levels"]), 6)
        for level in trial["levels"]:
            pub = level["renalEvidenceUnreviewed"]
            self.assertIsNotNone(pub)
            self.assertEqual(pub["nct"], "NCT04716231")
            self.assertEqual(len(pub["sourceLinks"]), 2)
            self.assertFalse(pub["historicalBlindBacktestPermitted"])
            self.assertFalse(pub["scientificallyAdjudicated"])
            self.assertFalse(pub["originalSourcesIndependentlyAuthenticated"])
            self.assertEqual(level["independentScientificReviewStatus"], "NOT_ADJUDICATED")
            self.assertIsNone(level["score"])
            self.assertFalse(level["completionPermitted"])
        clinical = trial["levels"][2]["renalEvidenceUnreviewed"]
        self.assertEqual(clinical["interimPrimaryProteinuriaUnreviewed"]["denominator"][
            "prespecifiedInterimAnalysisTotal"], 203)
        self.assertEqual(clinical["interimPrimaryProteinuriaUnreviewed"]["primary"][
            "publishedBetweenGroupDifferencePercentagePoints"], 41.8)
        self.assertEqual(clinical["laterSecondaryKidneyFunctionUnreviewed"]["denominator"][
            "randomized"], 431)
        self.assertEqual(clinical["laterSecondaryKidneyFunctionUnreviewed"][
            "secondaryEfficacy"][0]["reportedBetweenGroupDifference"], 5.58)
        self.assertEqual(clinical["laterSecondaryKidneyFunctionUnreviewed"][
            "secondaryEfficacy"][1]["reportedBetweenGroupDifference"], 5.00)
        self.assertIsNone(trial["levels"][4]["publicationFindingsUnreviewed"])
        self.assertIsNone(trial["approvalProbability"])
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        other = next(t for t in packet["trials"] if t["nct"] == "NCT05767346")
        self.assertTrue(all(l["renalEvidenceUnreviewed"] is None for l in other["levels"]))
        md = handoff.markdown(packet)
        self.assertIn("PRIMARY INTERIM: week-36", md)
        self.assertIn("LATER SECONDARY: eGFR change at week 52", md)
        self.assertIn("ONE Phase 3 trial", md)

    def test_origin3_rejects_forged_science_and_historical_cutoff(self):
        data = json.loads(handoff.ORIGIN3_RENAL.read_text(encoding="utf-8"))
        data["blindHistoricalPredictionPermitted"] = True
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, origin3_renal=data)
        data = json.loads(handoff.ORIGIN3_RENAL.read_text(encoding="utf-8"))
        data["reports"][1]["secondaryEfficacy"][0][
            "reportedBetweenGroupDifference"] = 0.0
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, origin3_renal=data)
        data = json.loads(handoff.ORIGIN3_RENAL.read_text(encoding="utf-8"))
        data["nct"] = "NCT04576949"
        with self.assertRaises(ValueError):
            handoff.build(self.coverage, self.roster, self.applications,
                          self.chronology, origin3_renal=data)

    def test_orca2_first_for_collected_evidence_not_highest_approval_chance(self):
        packet = self.build()
        self.assertEqual(packet["trials"][0]["nct"], "NCT04576949")
        self.assertIn("NOT_APPROVAL_LIKELIHOOD", packet["sortDefinition"])
        level = packet["trials"][0]["levels"][4]
        self.assertIn("UNRESOLVED", level["statisticalChronology"][
            "finalSapPrespecificationRelativeToUnblinding"])
        self.assertFalse(level["statisticalChronology"]["statisticalDeficiencyEstablished"])
        self.assertIn("database-lock", " ".join(level["openReviewQuestions"]).lower())
        self.assertFalse(packet["researchIsOutcomeExposed"] is False)

    def test_unmapped_three_are_visible_with_no_invented_application(self):
        packet = self.build()
        unlinked = {t["nct"] for t in packet["trials"]
                    if t["applicationMappingStatus"] == "NOT_MAPPED_APPLICATION_CYCLE"}
        self.assertEqual(unlinked, {"NCT05031780", "NCT06747468", "NCT06553768"})
        self.assertTrue(all(t["independentReviewerAccess"] == "NOT_APPROVED_OR_ACTIVATED"
                            for t in packet["trials"]))

    def test_missing_posted_result_not_interpreted_as_failed_trial(self):
        packet = self.build()
        trial = next(t for t in packet["trials"] if t["nct"] == "NCT05031780")
        self.assertEqual(trial["levels"][2]["evidenceCollectionStatus"],
                         "NOT_COLLECTED_AVAILABILITY_UNRESOLVED")
        self.assertTrue(any("do not presume failure" in q
                            for q in trial["levels"][2]["openReviewQuestions"]))
        self.assertEqual(trial["levels"][2]["scientificReviewStatus"]
                         if "scientificReviewStatus" in trial["levels"][2]
                         else trial["levels"][2]["independentScientificReviewStatus"],
                         "NOT_ADJUDICATED")

    def test_mixed_phase_requires_applicability_not_future_phase_proof(self):
        packet = self.build()
        for nct in ("NCT05031780", "NCT04871282"):
            trial = next(t for t in packet["trials"] if t["nct"] == nct)
            self.assertEqual(trial["levels"][2]["applicability"],
                             "MIXED_PHASE2_PHASE3_REQUIRES_APPLICABILITY_REVIEW")
            self.assertEqual(trial["levels"][4]["applicability"],
                             "MIXED_PHASE2_PHASE3_REQUIRES_APPLICABILITY_REVIEW")

    def test_missing_roster_and_cross_trial_ticker_swaps_are_rejected(self):
        self.roster["records"].pop()
        with self.assertRaises(ValueError):
            self.build()
        self.coverage, self.roster, self.applications, self.chronology = inputs()
        self.coverage["trials"][0]["ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            self.build()

    def test_unmapped_cannot_be_silently_mapped(self):
        target = next(x for x in self.coverage["trials"] if x["nct"] == "NCT05031780")
        target["mappingStatus"] = "PROVISIONAL_NOT_VERIFIED"
        with self.assertRaises(ValueError):
            self.build()

    def test_cannot_promote_source_or_scientific_review_flags(self):
        for key, value in (
            ("independentlyAuthenticatedSources", 1),
            ("independentlyAdjudicatedAssessments", 1),
            ("historicalPredictionInputPermitted", True),
            ("approvalProbability", 0.99),
        ):
            params = inputs()
            data = copy.deepcopy(params[0])
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                handoff.build(data, *params[1:])
        self.coverage["trials"][0]["independentlyAdjudicatedAssessments"] = 1
        with self.assertRaises(ValueError):
            self.build()

    def test_cannot_forge_orca_chronology_review_or_forecast(self):
        for key, value in (
            ("finalSapPrespecificationRelativeToUnblinding", "VERIFIED_BEFORE_LOCK"),
            ("scientificReviewStatus", "ADJUDICATED"),
            ("fdaPredictionPermitted", True),
            ("approvalProbability", 0.9),
            ("sourceIndependentlyAuthenticated", True),
            ("databaseLockDateVerified", True),
        ):
            params = inputs()
            changed = copy.deepcopy(params[3])
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                handoff.build(*params[:3], changed)

    def test_markdown_handoff_lists_original_questions_without_scores(self):
        text = handoff.markdown(self.build())
        self.assertIn("NCT04576949", text)
        self.assertIn("OWNER_NOT_REVIEWED", text)
        self.assertIn("UNRESOLVED", text)
        self.assertEqual(text.count("### Level "), 192)
        self.assertNotIn("FDA approval probability:", text)

    def test_cli_produces_read_only_orca2_packet(self):
        command = [sys.executable, str(SCRIPTS / "level16_review_handoff.py"),
                   "--nct", "NCT04576949", "--format", "json"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   check=True, timeout=20)
        packet = json.loads(completed.stdout)
        self.assertEqual(packet["selectedNctOnly"], "NCT04576949")
        self.assertEqual(len(packet["trials"]), 1)
        self.assertEqual(packet["reviewPacketsPrepared"], 32)
        self.assertEqual(packet["independentlyAdjudicatedLevels"], 0)
        self.assertEqual(packet["trials"][0]["levels"][4]["scientificReviewStatus"]
                         if "scientificReviewStatus" in packet["trials"][0]["levels"][4]
                         else packet["trials"][0]["levels"][4]["independentScientificReviewStatus"],
                         "NOT_ADJUDICATED")

    def test_altered_phase_and_collection_status_do_not_autoadjudicate(self):
        trial = next(x for x in self.coverage["trials"] if x["nct"] == "NCT04576949")
        trial["phaseUnreviewed"] = ["PHASE1"]
        packet = self.build()
        row = next(x for x in packet["trials"] if x["nct"] == "NCT04576949")
        self.assertEqual(row["levels"][4]["applicability"],
                         "FUTURE_PIVOTAL_PHASE3_PACKAGE_NOT_YET_EXPECTED")
        self.assertFalse(row["readyForIndependentFinalAdjudication"])
        trial["protocol"] = "verified"
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
