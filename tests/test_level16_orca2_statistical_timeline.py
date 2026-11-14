"""Guard ORCA-2 statistical chronology against invented dates and signoff."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/medical/level16_orca2_statistical_timeline.py"
spec = importlib.util.spec_from_file_location("level16_orca2_statistical_timeline", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Orca2StatisticalChronologyTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads(module.INPUT.read_text(encoding="utf-8"))

    def event(self, ident):
        return next(row for row in self.case["events"] if row["eventId"] == ident)

    def test_documented_hochberg_precedes_completion_but_sap_timing_unresolved(self):
        result = module.assess(self.case)
        self.assertEqual(result["nct"], "NCT04576949")
        self.assertEqual(result["assessmentLevel"], 5)
        self.assertTrue(result["protocolVersionPredatesRegistryPrimaryCompletion"])
        self.assertTrue(result["preCompletionProtocolExplicitlyMentionsPrimaryHochberg"])
        self.assertTrue(result["sapVersionDateAfterRegistryPrimaryCompletion"])
        self.assertTrue(result["sapExplainsBonferroniForPowerAndHochbergForPrimaryTesting"])
        self.assertEqual(result["finalSapPrespecificationRelativeToUnblinding"], "UNRESOLVED")
        self.assertFalse(result["multiplicityInconsistencyEstablished"])
        self.assertFalse(result["statisticalDeficiencyEstablished"])
        self.assertFalse(result["databaseLockDateVerified"])
        self.assertFalse(result["unblindingDateVerified"])
        self.assertEqual(result["sourceEventCount"], 4)

    def test_study_is_current_source_outcome_exposed_not_blind_forecast(self):
        result = module.assess(self.case)
        self.assertFalse(result["currentResearchIsBlind"])
        self.assertFalse(result["sourceIndependentlyAuthenticated"])
        self.assertEqual(result["scientificReviewStatus"], "NOT_ADJUDICATED")
        self.assertFalse(result["fdaPredictionPermitted"])
        self.assertIsNone(result["approvalProbability"])
        self.assertIsNone(result["fdaOutcomeJudgment"])

    def test_forged_authentication_reviews_or_probabilities_rejected(self):
        mutations = {
            "sourceIndependentlyAuthenticated": True,
            "statisticallyAdjudicated": True,
            "fdaApplicationCycleVerified": True,
            "approvalProbability": 0.99,
            "fdaOutcomeJudgment": "APPROVAL",
            "priorSapVersionsReconciled": True,
            "protocolAmendmentHistoryReconciled": True,
            "finalSapApprovalRelativeToUnblinding": "BEFORE_UNBLINDING",
        }
        for key, value in mutations.items():
            changed = copy.deepcopy(self.case)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.assess(changed)

    def test_unverified_lock_unblinding_or_caller_reviewer_rejected(self):
        for key, value in (
            ("databaseLockDate", "2022-04-01"),
            ("unblindingDate", "2022-04-02"),
            ("reviewerId", "synthetic-admin"),
            ("independentlySigned", True),
            ("statisticalScore", 100),
        ):
            changed = copy.deepcopy(self.case)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.assess(changed)

    def test_rejects_protocol_substitution_or_claims_from_another_trial(self):
        for value in (
            "https://cdn.clinicaltrials.gov/large-docs/16/NCT05507216/Prot_000.pdf",
            "https://other.example.org/source.pdf",
        ):
            case = copy.deepcopy(self.case)
            next(e for e in case["events"] if e["eventId"] == "protocol_v4")["sourceUrl"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.assess(case)
        self.case["nct"] = "NCT05507216"
        with self.assertRaises(ValueError):
            module.assess(self.case)

    def test_fails_when_method_roles_or_factual_dates_tampered(self):
        changed = copy.deepcopy(self.case)
        next(e for e in changed["events"] if e["eventId"] == "protocol_v4")["methods"] = []
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.case)
        next(e for e in changed["events"] if e["eventId"] == "sap_v1")["methods"] = [
            "POWER_SIMULATION_BONFERRONI"
        ]
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.case)
        next(e for e in changed["events"] if e["eventId"] == "sap_v1")["date"] = "2021-03-25"
        with self.assertRaises(ValueError):
            module.assess(changed)

    def test_duplicate_missing_or_extra_source_events_are_rejected(self):
        changed = copy.deepcopy(self.case)
        changed["events"][-1] = copy.deepcopy(changed["events"][0])
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.case)
        changed["events"].pop()
        with self.assertRaises(ValueError):
            module.assess(changed)
        changed = copy.deepcopy(self.case)
        changed["events"][0]["sourceKindVerified"] = True
        with self.assertRaises(ValueError):
            module.assess(changed)

    def test_cutoff_and_cohort_quarantine_unchanged(self):
        for key, val in (
            ("evidenceCutoffDate", "2026-11-15"),
            ("context", "BLIND_PREDECISION_PREDICTION"),
            ("kind", "FDA_FORECAST"),
            ("studyCode", "ACH-CYT-04"),
            ("schemaVersion", True),
        ):
            changed = copy.deepcopy(self.case)
            changed[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.assess(changed)

    def test_documented_questions_remain_explicit(self):
        result = module.assess(self.case)
        joined = " ".join(result["needsIndependentEvidence"]).lower()
        for expected in ("database-lock", "unblinding", "sap", "amendment",
                         "statistical", "source"):
            self.assertIn(expected, joined)


if __name__ == "__main__":
    unittest.main()
