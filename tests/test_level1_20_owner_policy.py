"""Owner directives: all 20 assessment levels, exactly one owner, zero external gates."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/level1_20_owner_policy.py"
spec = importlib.util.spec_from_file_location("level1_20_owner_policy", SCRIPT)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)


class OwnerPolicyLevels1To20Tests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(owner.POLICY.read_text(encoding="utf-8"))

    def test_all_twenty_levels_have_zero_outside_signoffs(self):
        self.assertTrue(owner.validate(self.policy))
        requirements = [owner.requirements_for_level(self.policy, i) for i in range(1,21)]
        self.assertEqual([r["level"] for r in requirements], list(range(1,21)))
        self.assertEqual(sum(r["externalSignoffsRequired"] for r in requirements), 0)
        self.assertTrue(all(r["ownerCheckOnly"] for r in requirements))
        self.assertTrue(all(r["outsidePeopleRequired"] == 0 for r in requirements))
        self.assertTrue(all(r["sourceChecks"] == "OWNER_AND_AUTOMATED_INTERNAL_ONLY"
                            for r in requirements))
        self.assertTrue(all(not r["independentCertificationRequired"]
                            for r in requirements))
        self.assertEqual(sum(x["engineeringImplementedByThisPolicy"] for x in requirements), 6)

    def test_five_person_review_and_outside_verifiers_cannot_reappear(self):
        for key in owner.OUTSIDE_GATES:
            d = copy.deepcopy(self.policy)
            d["humanRequirements"][key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.validate(d)
        for key in ("requiredHumanOperators", "ownerMayCheckAllEvidenceAndLevels"):
            d = copy.deepcopy(self.policy)
            d["humanRequirements"][key] = 5 if key == "requiredHumanOperators" else False
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.validate(d)

    def test_security_source_checks_and_phase_applicability_stay_internal(self):
        for key in owner.RETAINED_CHECKS:
            d = copy.deepcopy(self.policy)
            d["retainedControls"][key] = False
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.validate(d)

    def test_owner_self_check_cannot_be_mislabelled_independent(self):
        d = copy.deepcopy(self.policy)
        d["ownerStatusVocabulary"]["notIndependent"] = "INDEPENDENTLY_VERIFIED"
        with self.assertRaises(ValueError):
            owner.validate(d)
        d = copy.deepcopy(self.policy)
        d["ownerStatusVocabulary"]["acceptedWithLimitations"] = "MEDICALLY_APPROVED"
        with self.assertRaises(ValueError):
            owner.validate(d)

    def test_no_false_level7_20_completion_or_fda_accuracy(self):
        d = copy.deepcopy(self.policy)
        d["scope"]["levels7To20EngineeringComplete"] = True
        with self.assertRaises(ValueError):
            owner.validate(d)
        for key,val in (
            ("ownerReviewsCompletedClaimed", 192),
            ("externallySignedAssessmentsRequired", 1),
            ("externalReviewerGateCount", 5),
            ("siteDeploymentAuthorized", True),
        ):
            d = copy.deepcopy(self.policy)
            d["technicalStatus"][key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.validate(d)

    def test_scope_is_one_through_twenty_not_arbitrary_late_phase_subset(self):
        for key,val in (
            ("fromLevel", 2), ("toLevel", 6), ("ownerHumanSeats", 5),
            ("activeTrialPopulations", ["FOCUS"]),
        ):
            d = copy.deepcopy(self.policy)
            d["scope"][key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.validate(d)
        for val in (0,21,1.5,True,"20"):
            with self.subTest(level=val), self.assertRaises(ValueError):
                owner.requirements_for_level(self.policy, val)

    def test_legacy_external_policy_is_retired_not_a_gate(self):
        self.assertEqual(
            self.policy["legacyExternalWorkflow"],
            "RETIRED_FROM_ACTIVE_GATES_PRESERVED_ONLY_AS_DISABLED_HISTORICAL_ENGINEERING",
        )
        d = copy.deepcopy(self.policy)
        d["legacyExternalWorkflow"] = "REQUIRED_FOR_LEVEL7"
        with self.assertRaises(ValueError):
            owner.validate(d)

    def test_cli_produces_owner_only_mode_without_external_signoff(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--level", "20"], cwd=ROOT,
            capture_output=True, text=True, timeout=20, check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["level"], 20)
        self.assertEqual(data["outsidePeopleRequired"], 0)
        self.assertEqual(data["externalSignoffsRequired"], 0)
        self.assertFalse(data["engineeringImplementedByThisPolicy"])
        all_levels = subprocess.run(
            [sys.executable, str(SCRIPT)], cwd=ROOT,
            capture_output=True, text=True, timeout=20, check=True,
        )
        all_output = json.loads(all_levels.stdout)
        self.assertEqual(len(all_output["policyLevels"]), 20)
        self.assertEqual(all_output["outsideReviewerOrSignoffGates"], 0)


if __name__ == "__main__":
    unittest.main()
