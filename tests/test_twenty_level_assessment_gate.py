"""No outside challenger, clinic or external signature in owner scientific Levels 1–20."""
import importlib.util
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate", root/"scripts/medical/twenty_level_assessment_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def valid(level=20):
    return {
        "nct":"NCT00000001","applicationId":"app1","reviewCycle":"2026",
        "assessmentLevel":level,
        "evidence":[{"sourceUrl":"https://example.org","sourceDate":"2026-01-01",
                     "claim":"documented","locator":"p.1"}],
        "limitations":"Scientific interpretation not independently certified",
        "ownerReviewStatus":"OWNER_ACCEPTED_WITH_LIMITATIONS",
        "outcomeJudgment":"ABSTAIN","timingJudgment":"UNKNOWN",
        "frozenAt":"2026-11-10T00:00:00Z","predictionHistoryAppendOnly":True,
    }


class AssessmentGateTests(unittest.TestCase):
    def test_empty_and_readiness_only_rejected(self):
        self.assertFalse(gate.validate({})["accepted"])
        self.assertFalse(gate.validate({"assessmentLevel":20,"nct":"NCT00000001"})["accepted"])

    def test_one_owner_suffices_for_every_level_without_external_reviewer(self):
        for level in range(1,21):
            with self.subTest(level=level):
                report=gate.validate(valid(level))
                self.assertTrue(report["accepted"],report["errors"])
                self.assertEqual(report["status"],"OWNER_REVIEWED_STRUCTURE_ONLY")
                self.assertEqual(report["externalReviewersRequired"],0)
                self.assertEqual(report["externalSignoffsRequired"],0)
                self.assertTrue(report["ownerOnly"])
                self.assertFalse(report["scientificAccuracyVerified"])
                self.assertFalse(report["independentlyCertified"])

    def test_legacy_second_person_neither_required_nor_used_as_approval(self):
        package=valid()
        package["reviewer"]="same-owner"
        package["independentChallenge"]={"reviewer":"same-owner","critique":"Owner considers risks"}
        self.assertTrue(gate.validate(package)["accepted"])
        package.pop("ownerReviewStatus")
        self.assertIn("OWNER_DECISION_REQUIRED",gate.validate(package)["errors"])

    def test_owner_cannot_be_falsely_marked_as_accepting_review(self):
        for value in (None,"OWNER_NOT_REVIEWED","OWNER_REVIEW_IN_PROGRESS",
                      "OWNER_NEEDS_EVIDENCE","OWNER_REJECTED","EXTERNALLY_APPROVED"):
            package=valid()
            package["ownerReviewStatus"]=value
            self.assertFalse(gate.validate(package)["accepted"])

    def test_invalid_probability_and_historical_blinding_rejected(self):
        package=valid()
        package["outcomeProbability"]=1.5
        self.assertIn("INVALID_PROBABILITY",gate.validate(package)["errors"])
        package=valid()
        package["prospective"]=True
        self.assertIn("PROSPECTIVE_BLINDING_UNVERIFIED",gate.validate(package)["errors"])
        package=valid()
        package["historicalOutcomeExposed"]=True
        self.assertIn("OUTCOME_EXPOSED_NOT_PROSPECTIVE",gate.validate(package)["errors"])

    def test_uncalibrated_probability_rejected_without_external_review(self):
        package=valid()
        package["outcomeProbability"]=0.9
        self.assertIn("UNCALIBRATED_PROBABILITY",gate.validate(package)["errors"])
        package["calibrationReference"]="frozen prospective out-of-sample test"
        self.assertTrue(gate.validate(package)["accepted"])

    def test_no_fake_provenance_or_immutable_history(self):
        package=valid()
        package["evidence"]=[{"sourceUrl":"https://example.org"}]
        self.assertIn("EVIDENCE_PROVENANCE_INCOMPLETE",gate.validate(package)["errors"])
        package=valid()
        package["predictionHistoryAppendOnly"]=False
        self.assertIn("IMMUTABLE_HISTORY_NOT_ATTESTED",gate.validate(package)["errors"])

    def test_no_boolean_or_future_level(self):
        for value in (True,0,21,"20"):
            self.assertIn("INVALID_LEVEL",gate.validate(valid(value))["errors"])


if __name__=="__main__":
    unittest.main()
