"""Tests for read-only phase-first Levels 1–6 FOCUS evidence readiness."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/medical/phase_first_levels_1_6.py"
spec = importlib.util.spec_from_file_location("phase_first_levels_1_6", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in (
        module.ROSTER_PATH, module.APPLICATIONS_PATH, module.DEFINITION_PATH))


def captured(nct, phase="PHASE3", status="RECRUITING", **fields):
    items = {
        "phase": {"status": "CAPTURED_UNREVIEWED", "value": [phase]},
        "studyOverallStatus": {"status": "CAPTURED_UNREVIEWED", "value": status},
        "primaryEndpoints": {"status": "CAPTURED_UNREVIEWED",
                             "value": [{"measure": "Registered endpoint only"}]},
    }
    items.update(fields)
    return {"status": "CAPTURED_UNREVIEWED", "evidence": {
        "nct": nct,
        "source": "https://clinicaltrials.gov/study/" + nct,
        "sha256": "a" * 64,
        "status": "SOURCE_EXTRACTED_NOT_ADJUDICATED",
        "fields": items,
    }}


class PhaseFirstLevels16Tests(unittest.TestCase):
    def setUp(self):
        self.roster, self.apps, self.definition = fixture()
        self.nct = self.roster["records"][0]["nct"]

    def build(self, results=None):
        return module.build(self.roster, self.apps, {"results": results or {}}, self.definition)

    def test_canonical_29_and_23_provisional_cycles_without_predictions(self):
        report = self.build()
        self.assertEqual(report["focusTrialCount"], 29)
        self.assertEqual(report["provisionalApplicationCycleCount"], 23)
        self.assertEqual(report["scientificallyAdjudicatedLevels"], 0)
        self.assertEqual(report["calibratedFdaPredictions"], 0)
        self.assertEqual(len(report["trials"]), 29)
        self.assertEqual([x["level"] for x in report["trials"][0]["levels"]], list(range(1, 7)))
        for trial in report["trials"]:
            self.assertEqual(trial["phaseGroup"], "UNRESOLVED")
            self.assertEqual(trial["scientificReviews"], 0)
            self.assertIsNone(trial["fdaOutcomeJudgment"])
            self.assertIsNone(trial["fdaTimingJudgment"])
            for level in trial["levels"]:
                self.assertFalse(level["assessmentCompleted"])
                self.assertIsNone(level["score"])
                self.assertIsNone(level["approvalProbability"])

    def test_phase_two_does_not_require_future_phase_three_readout(self):
        report = self.build({self.nct: captured(self.nct, "PHASE2")})
        trial = report["trials"][0]
        self.assertEqual(trial["phaseGroup"], "EARLIER_PHASE")
        self.assertEqual(trial["levels"][1]["currentStatusReview"],
                         "REGISTRY_STATUS_CAPTURED_NOT_VERIFIED")
        self.assertEqual(trial["levels"][2]["pivotalReadoutRequirement"],
                         "NOT_YET_EXPECTED_AT_EARLIER_PHASE")
        self.assertEqual(trial["levels"][4]["pivotalSAPRequirement"],
                         "NOT_YET_EXPECTED_AT_EARLIER_PHASE")
        self.assertEqual(trial["levels"][2]["scientificReviewStatus"], "NOT_ADJUDICATED")
        self.assertTrue(trial["levels"][2]["registeredEndpointsAreNotResults"])

    def test_phase_three_requires_separate_statistical_and_results_review(self):
        report = self.build({self.nct: captured(self.nct)})
        trial = report["trials"][0]
        self.assertEqual(trial["phaseGroup"], "POTENTIAL_PIVOTAL_PHASE3")
        self.assertEqual(trial["levels"][2]["pivotalReadoutRequirement"],
                         "REVIEW_PHASE3_RESULTS_AVAILABILITY")
        self.assertEqual(trial["levels"][4]["pivotalSAPRequirement"],
                         "PIVOTAL_SAP_AND_MULTIPLICITY_REVIEW_REQUIRED")
        self.assertIn("primaryEndpoints", trial["levels"][2]["registryFieldsCapturedUnreviewed"])
        self.assertIsNone(trial["levels"][2]["scientificConclusion"])

    def test_missing_status_and_design_fields_are_not_assumed_deficiencies(self):
        item = captured(self.nct, "PHASE3")
        del item["evidence"]["fields"]["studyOverallStatus"]
        result = self.build({self.nct: item})["trials"][0]
        self.assertEqual(result["levels"][1]["currentStatusReview"], "STATUS_UNRESOLVED")
        self.assertEqual(result["levels"][3]["designFieldAbsence"],
                         "REVIEW_NOT_AUTOMATIC_DEFICIENCY")
        self.assertIn("allocation", result["levels"][3]["registryFieldsNotCaptured"])

    def test_phase_four_not_automatically_new_pivotal_trial(self):
        result = self.build({self.nct: captured(self.nct, "PHASE4")})["trials"][0]
        self.assertEqual(result["phaseGroup"], "POSTMARKETING_PHASE4")
        self.assertEqual(result["levels"][2]["pivotalReadoutRequirement"],
                         "NOT_AUTOMATICALLY_REQUIRED_FOR_PHASE4")

    def test_invalid_phase_or_unverified_field_status_cannot_be_promoted(self):
        entry = captured(self.nct, "PHASE3")
        entry["evidence"]["fields"]["phase"]["status"] = "INDEPENDENTLY_VERIFIED"
        result = self.build({self.nct: entry})["trials"][0]
        self.assertEqual(result["phaseGroup"], "UNRESOLVED")
        self.assertFalse(result["levels"][1]["assessmentCompleted"])

    def test_rejects_cross_trial_source_and_spoofed_digest(self):
        entry = captured(self.nct)
        entry["evidence"]["nct"] = self.roster["records"][1]["nct"]
        with self.assertRaises(ValueError):
            self.build({self.nct: entry})
        entry = captured(self.nct)
        entry["evidence"]["sha256"] = "not-a-digest"
        with self.assertRaises(ValueError):
            self.build({self.nct: entry})

    def test_rejects_checkpoint_from_another_roster(self):
        with self.assertRaises(ValueError):
            self.build({"NCT99999999": captured("NCT99999999")})

    def test_rejects_roster_or_application_crosswalk_changes(self):
        records = self.roster["records"]
        original = records[1]["nct"]
        records[1]["nct"] = records[0]["nct"]
        with self.assertRaises(ValueError):
            self.build()
        records[1]["nct"] = original
        apps = copy.deepcopy(self.apps)
        apps["records"][0]["candidateApplications"][0]["ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            module.build(self.roster, apps, {"results": {}}, self.definition)

    def test_retry_unreviewed_and_outcome_exposed_claims_do_not_create_reviews(self):
        entry = captured(self.nct)
        entry["evidence"]["fdaPrediction"] = {"outcome": "APPROVAL", "probability": 1.0}
        entry["evidence"]["scientificReview"] = {"accepted": True}
        report = self.build({self.nct: entry})
        self.assertEqual(report["scientificallyAdjudicatedLevels"], 0)
        self.assertTrue(all(x["approvalProbability"] is None
                            for x in report["trials"][0]["levels"]))
        self.assertIsNone(report["trials"][0]["fdaOutcomeJudgment"])
        retry = self.build({self.nct: {"status": "RETRY_REQUIRED"}})["trials"][0]
        self.assertEqual(retry["phaseGroup"], "UNRESOLVED")
        self.assertEqual(retry["registryCaptureStatus"], "RETRY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
