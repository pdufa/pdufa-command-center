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


    def evidence_doc(self, records, cutoff="2026-11-12"):
        return {"schemaVersion": 1, "kind": "FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS",
                "cutoffDate": cutoff, "records": records}

    def submission(self, **overrides):
        item = {
            "submissionId": "source-lead-001", "nct": self.nct, "level": 3,
            "sourceKind": "JOURNAL_PUBLICATION",
            "sourceUrl": "https://journals.example.org/clinical-result",
            "sourceDate": "2026-11-08", "accessedDate": "2026-11-10",
            "documentSha256": "b" * 64, "locator": "Figure 1",
            "claim": "Authors report a clinical endpoint difference requiring independent review.",
            "role": "SUPPORTS", "submittedBy": "research-intake",
        }
        item.update(overrides)
        return item

    def report_with_submissions(self, submission_records, checkpoint=None, cutoff="2026-11-12"):
        return module.build(self.roster, self.apps, {"results": checkpoint or {}},
                            self.definition, self.evidence_doc(submission_records, cutoff))

    def test_source_submission_routes_to_exact_trial_level_without_certification(self):
        report = self.report_with_submissions([self.submission()])
        self.assertEqual(report["sourceSubmissionCount"], 1)
        first = report["trials"][0]
        self.assertEqual(first["sourceSubmissionCount"], 1)
        level3 = first["levels"][2]
        self.assertEqual(level3["sourceReviewQueueStatus"],
                         "AWAITING_INDEPENDENT_SOURCE_AUTHENTICATION")
        self.assertEqual(level3["readiness"], "SOURCE_METADATA_SUBMITTED_REVIEW_REQUIRED")
        self.assertEqual(level3["submittedEvidenceLeads"][0]["authenticationStatus"],
                         "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED")
        self.assertEqual(level3["scientificReviewStatus"], "NOT_ADJUDICATED")
        self.assertFalse(level3["assessmentCompleted"])
        self.assertIsNone(level3["score"])
        self.assertIsNone(first["fdaOutcomeJudgment"])
        self.assertEqual(report["scientificallyAdjudicatedLevels"], 0)
        self.assertEqual(report["trials"][1]["sourceSubmissionCount"], 0)

    def test_registry_submission_binds_original_source_digest_and_exact_locator(self):
        reg = captured(self.nct, phase="PHASE2")
        reg["evidence"]["fields"]["phase"]["locator"] = "protocolSection.designModule.phases"
        entry = self.submission(
            level=2, sourceKind="REGISTRY",
            sourceUrl="https://clinicaltrials.gov/study/" + self.nct,
            documentSha256="a" * 64, locator="protocolSection.designModule.phases",
            claim="Registry phase is Phase 2, pending independent source verification.")
        report = self.report_with_submissions([entry], {self.nct: reg})
        self.assertEqual(report["trials"][0]["levels"][1]["sourceSubmissionCount"], 1)
        self.assertEqual(report["trials"][0]["phaseGroup"], "EARLIER_PHASE")
        entry["documentSha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry], {self.nct: reg})
        entry["documentSha256"] = "a" * 64
        entry["locator"] = "protocolSection.madeUp"
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry], {self.nct: reg})

    def test_declared_cutoff_blocks_future_or_later_accessed_evidence(self):
        entry = self.submission(sourceDate="2026-11-13")
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry])
        entry = self.submission(accessedDate="2026-11-15")
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry])
        entry = self.submission(sourceDate="2026-11-11", accessedDate="2026-11-10")
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry])

    def test_fake_review_or_fda_prediction_field_is_rejected(self):
        for field, value in (("scientificReviewStatus", "INDEPENDENTLY_REVIEWED"),
                             ("outcomeProbability", 0.99),
                             ("reviewer", "invented reviewer"),
                             ("independentlyVerified", True)):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.report_with_submissions([self.submission(**{field: value})])

    def test_external_source_is_not_registry_and_cannot_override_phase(self):
        entry = self.submission(level=2, sourceKind="SPONSOR_DISCLOSURE",
                                claim="Sponsor says the study changed status.")
        report = self.report_with_submissions([entry])
        self.assertEqual(report["trials"][0]["phaseGroup"], "UNRESOLVED")
        self.assertEqual(report["trials"][0]["levels"][1]["currentStatusReview"],
                         "STATUS_UNRESOLVED")
        self.assertEqual(report["trials"][0]["levels"][1]["scientificReviewStatus"],
                         "NOT_ADJUDICATED")

    def test_rejects_wrong_application_cycle_or_mismatched_trial(self):
        wrong_cycle = "cycle-not-associated-with-trial"
        with self.assertRaises(ValueError):
            self.report_with_submissions([
                self.submission(candidateApplicationCycleId=wrong_cycle)])
        with self.assertRaises(ValueError):
            self.report_with_submissions([self.submission(nct="NCT99999999")])

    def test_rejects_duplicate_ids_unsafe_urls_and_invalid_levels(self):
        entry = self.submission()
        with self.assertRaises(ValueError):
            self.report_with_submissions([entry, entry])
        for bad in (0, 7, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.report_with_submissions([self.submission(level=bad)])
        for url in ("http://example.org/claim", "https://localhost/source",
                    "https://user:password@example.org/source"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.report_with_submissions([self.submission(sourceUrl=url)])


if __name__ == "__main__":
    unittest.main()
