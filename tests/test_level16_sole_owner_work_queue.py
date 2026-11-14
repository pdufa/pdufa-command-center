"""Sole-owner research path must never imply independent medical signoff."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/medical"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


single = load("level16_sole_owner_work_queue")
research = load("level16_research_handoff_bundle")


class SoleOwnerResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner = json.loads(single.INTENT.read_text(encoding="utf-8"))
        cls.bundle = research.build_bundle(ROOT)

    def owner_intent(self):
        return copy.deepcopy(self.owner)

    def bundle_case(self):
        return copy.deepcopy(self.bundle)

    def test_one_owner_preference_is_not_a_live_authorization(self):
        report = single.build(self.owner_intent(), self.bundle_case())
        self.assertEqual(report["trialCount"], 32)
        self.assertEqual(report["levelCount"], 192)
        self.assertTrue(report["ownerOnly"])
        self.assertEqual(report["authorizedOperatorSlotsRequested"], 1)
        self.assertEqual(report["authenticatedOwnerAccountsVerified"], 0)
        self.assertEqual(report["ownerReviewsCompleted"], 0)
        self.assertEqual(report["independentReviewsCompleted"], 0)
        self.assertFalse(report["siteLive"])
        self.assertFalse(report["sourceIndependentlyAuthenticated"])
        self.assertFalse(report["fdaForecastPublished"])
        self.assertTrue(report["legacyOutsideReviewerWorkflowInactive"])
        self.assertEqual(report["externalReviewerRequirementsForOwnerAssessments"], 0)
        self.assertEqual(report["externalSignoffsRequiredForOwnerAssessments"], 0)
        self.assertTrue(report["ownerAssessmentCanProceedWithoutExternalVerification"])
        self.assertEqual(report["ownerAssessmentAppliesThroughLevel"], 20)
        self.assertFalse(report["levels7To20EngineeringComplete"])
        self.assertEqual(len(report["ownerOnlyReviewRequirements"]), 20)
        self.assertTrue(all(item["outsidePeopleRequired"] == 0
                            for item in report["ownerOnlyReviewRequirements"]))
        self.assertTrue(report["blockedOn"])

    def test_phases_indications_ncts_unmapped_and_levels_remain(self):
        report = single.build(self.owner_intent(), self.bundle_case())
        self.assertEqual(len({x["nct"] for x in report["trials"]}), 32)
        self.assertEqual({x["nct"] for x in report["trials"]
                          if x["provisionalApplicationMapping"] == "NOT_MAPPED_APPLICATION_CYCLE"},
                         {"NCT05031780", "NCT06747468", "NCT06553768"})
        for trial in report["trials"]:
            self.assertEqual([x["level"] for x in trial["ownerOnlyTasks"]], [1, 2, 3, 4, 5, 6])
            self.assertFalse(trial["outsidePeopleRequiredForOwnerResearch"])
            self.assertEqual(trial["ownerResearchProgress"], "NOT_STARTED_OWNER_REVIEW")
            self.assertTrue(trial["phaseUnreviewed"])
            for task in trial["ownerOnlyTasks"]:
                self.assertEqual(task["ownerAssessmentStatus"], "NOT_ENTERED")
                self.assertEqual(task["ownerSelfReviewStatus"], "OWNER_NOT_REVIEWED")
                self.assertFalse(task["externalVerificationRequired"])
                self.assertEqual(task["outsideReviewerCountRequired"], 0)
                self.assertTrue(task["ownerCheckCanProceedWithoutIndependentSignoff"])
                self.assertFalse(task["independentlyAuthenticated"])
                self.assertFalse(task["independentlyAdjudicated"])
                self.assertIsNone(task["validatedFdaProbability"])
                self.assertTrue(task["ownerResearchQuestions"])

    def test_owner_can_assess_all_levels_without_external_certification_gate(self):
        report = single.build(self.owner_intent(), self.bundle_case())
        self.assertEqual(report["externalReviewerRequirementsForOwnerAssessments"], 0)
        self.assertEqual(report["externalSignoffsRequiredForOwnerAssessments"], 0)
        self.assertTrue(report["ownerAssessmentCanProceedWithoutExternalVerification"])
        self.assertTrue(report["legacyOutsideReviewerWorkflowInactive"])
        self.assertTrue(all(x["ownerCheckOnly"] and
                            x["externalSignoffsRequired"] == 0 and
                            x["outsidePeopleRequired"] == 0
                            for x in report["ownerOnlyReviewRequirements"]))
        self.assertEqual(report["ownerOnlyReviewRequirements"][19]["level"], 20)
        for trial in report["trials"]:
            self.assertTrue(trial["ownerAssessmentNotBlockedByExternalVerification"])
            for task in trial["ownerOnlyTasks"]:
                self.assertFalse(task["externalVerificationRequired"])
                self.assertEqual(task["ownerSelfReviewStatus"], "OWNER_NOT_REVIEWED")
                self.assertTrue(task["ownerCheckCanProceedWithoutIndependentSignoff"])

    def test_no_owner_identity_account_or_staging_can_be_invented(self):
        cases = (
            ("ownerPrincipalId", "owner-user-id"),
            ("ownerIssuer", "https://example.org"),
            ("ownerIdentityVerificationStatus", "VERIFIED"),
            ("sourceAuthenticity", "AUTHENTICATED"),
            ("independentScientificAdjudications", 192),
            ("ownerLevelReviewsEntered", 192),
            ("publishedPredictions", 32),
            ("noLiveReleaseAuthorization", False),
            ("noPurchaseOrBillingAuthorization", False),
            ("ownerPreferenceConfirmedByConversation", False),
        )
        for key, value in cases:
            data = self.owner_intent()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                single.build(data, self.bundle_case())

    def test_owner_only_avoids_outside_users_and_shared_credentials(self):
        cases = (
            ("authorizedOperatorSlots", 2),
            ("soleHumanOperator", False),
            ("allowExternalEditorAccounts", True),
            ("allowOutsideReviewerAccounts", True),
            ("allowSharedAdminCredentials", True),
            ("requiredMfaForSoleOwner", False),
            ("existingIndependentWorkflow", "BYPASSED"),
            ("researchReviewLabel", "INDEPENDENTLY_REVIEWED"),
        )
        for key, value in cases:
            data = self.owner_intent()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                single.build(data, self.bundle_case())

    def test_approval_ledger_not_implicitly_filled_by_blanket_statement(self):
        self.assertEqual(self.owner["kind"],
                         "LEVEL16_SOLE_OWNER_RESEARCH_INTENT_NOT_RUNTIME_AUTHORIZATION")
        self.assertTrue(self.owner["noPurchaseOrBillingAuthorization"])
        self.assertTrue(self.owner["noLiveReleaseAuthorization"])
        self.assertIn("DEPLOY", self.owner["protectedActionsStillDisabled"])
        self.assertIn("CREATE_REVIEWER", self.owner["protectedActionsStillDisabled"])
        self.assertIn("MINT_IDENTITY", self.owner["protectedActionsStillDisabled"])
        self.assertIn("PUBLISH_UNCALIBRATED_FDA_PROBABILITY",
                      self.owner["protectedActionsStillDisabled"])

    def test_unsigned_bundle_tampering_does_not_grant_owner_privileges(self):
        for mutate in (
            lambda b: b["packet"].update(independentlyAdjudicatedLevels=1),
            lambda b: b["packet"]["trials"][0]["levels"][0].update(
                independentScientificReviewStatus="ADJUDICATED"),
            lambda b: b["packet"]["trials"][0].update(
                nct="NCT99999999"),
            lambda b: b.update(packetSha256="0" * 64),
        ):
            b = self.bundle_case()
            mutate(b)
            with self.assertRaises(ValueError):
                single.build(self.owner_intent(), b)

    def test_owner_queue_is_read_only_and_deterministic(self):
        a = single.build(self.owner_intent(), self.bundle_case())
        b = single.build(self.owner_intent(), self.bundle_case())
        self.assertEqual(a, b)
        self.assertEqual(a["sourceMetadataSha256"], self.bundle["sourceSha256"])
        self.assertEqual(a["researchPacketSha256"], self.bundle["packetSha256"])

    def test_cli_can_show_orca2_but_not_unknown_trial(self):
        cmd = [sys.executable, str(SCRIPTS / "level16_sole_owner_work_queue.py"),
               "--nct", "NCT04576949"]
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                                timeout=30, check=True)
        obj = json.loads(result.stdout)
        self.assertEqual(obj["trialCount"], 32)
        self.assertEqual(obj["selectedNctOnly"], "NCT04576949")
        self.assertEqual(len(obj["trials"]), 1)
        self.assertEqual(len(obj["trials"][0]["ownerOnlyTasks"]), 6)
        invalid = subprocess.run(cmd[:-1] + ["NCT99999999"], cwd=ROOT, text=True,
                                 capture_output=True, timeout=30)
        self.assertNotEqual(invalid.returncode, 0)

    def test_unknown_config_and_owner_privileges_fail_closed(self):
        for mutation in (
            lambda c: c.update(approvalReference="synthetic-approved"),
            lambda c: c.update(status="AUTHENTICATED"),
            lambda c: c.update(schemaVersion=True),
            lambda c: c["allowedNow"].append("DEPLOY"),
            lambda c: c["protectedActionsStillDisabled"].remove("DEPLOY"),
        ):
            c = self.owner_intent()
            mutation(c)
            with self.assertRaises(ValueError):
                single.validate_intent(c)


if __name__ == "__main__":
    unittest.main()
