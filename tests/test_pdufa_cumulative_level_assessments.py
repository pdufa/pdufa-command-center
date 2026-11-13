"""Real phase-first PDUFA scoring contract tests (synthetic fixtures, no FDA outcome data)."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pdufa_cumulative_level_assessments as A

MANIFEST = json.loads((ROOT / "automation/scientific-level-completion-queue.json").read_text())
ROSTER = json.loads((ROOT / "automation/focus-assessment-roster-snapshot-20261112.json").read_text())
DATE = date(2026, 11, 12)
NCT = "NCT05507203"


def source(url="https://clinicaltrials.gov/study/NCT05507203", published="2026-11-11"):
    return {"url": url, "sha256": "a"*64, "published_on": published,
            "retrieved_at_utc": "2026-11-12T00:00:00Z"}


def scored_trial(level=6):
    criteria = A.criteria_for_level(A.validated_manifest(MANIFEST), level)
    trial = {
        "nct": NCT, "phase": "PHASE3", "application_stage": "UNDER_REVIEW",
        "phase_source": source(),
        "application_source": source("https://www.fda.gov/drugs/drug-approvals-and-databases"),
        "evidence": {
            name: {"status": "VERIFIED", "rubric_score": 80,
                   "reason": f"Prespecified criterion {name} independently sourced",
                   "source": source()}
            for name in criteria
        }
    }
    return trial


class Assessments(unittest.TestCase):
    def test_focus_source_is_32_unique_records_and_not_score_proof(self):
        self.assertEqual(len(A.validated_roster(ROSTER)), 32)
        self.assertEqual(len({r["nct"] for r in ROSTER["trials"]}), 32)
        self.assertTrue(ROSTER["legacy_research_scores_are_not_level4_to20_scores"])
        self.assertTrue(ROSTER["source"]["canonical_live_membership_not_guaranteed"])

    def test_all_17_levels_cumulative_each_adds_new_scientific_criteria(self):
        rows = A.validated_manifest(MANIFEST)
        self.assertEqual([x["level"] for x in rows], list(range(4, 21)))
        prior = set()
        for level in range(4, 21):
            criteria = set(A.criteria_for_level(rows, level))
            self.assertTrue(criteria > prior)
            if level == 6:
                self.assertTrue({"efficacy", "safety", "trial_quality",
                                 "benefit_risk", "manufacturing_cmc"} <= criteria)
            prior = criteria

    def test_dated_32_trial_17_level_coverage_does_not_invent_scores(self):
        output = A.build(MANIFEST, ROSTER, None)
        self.assertEqual(output["focus_trials"], 32)
        self.assertEqual(output["assessment_records"], 32 * 17)
        self.assertEqual(len(output["per_level"]), 17)
        self.assertTrue(all(v["provisional_numeric_scores"] == 0
                            for v in output["per_level"]))
        self.assertTrue(all(v["complete_scientific_assessments"] == 0
                            for v in output["per_level"]))
        self.assertTrue(all(x["score_out_of_100"] is None
                            for x in output["assessments"]))
        self.assertTrue(all(x["fda_approval_probability"] is None
                            for x in output["assessments"]))
        self.assertFalse(output["scientific_acceptance_automated"])

    def test_when_real_phase_criteria_scored_cumulative_level4_to6_score(self):
        trial = scored_trial(6)
        rows = A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        self.assertEqual([r["score_out_of_100"] for r in rows[:3]], [80, 80, 80])
        self.assertEqual(rows[2]["assessment_status"],
                         "PROVISIONAL_RESEARCH_SCORE_REVIEW_REQUIRED")
        self.assertIsNone(rows[3]["score_out_of_100"])  # Level 7 adds actual model evidence
        self.assertFalse(rows[2]["science_complete"])
        self.assertIsNone(rows[2]["fda_approval_probability"])
        self.assertEqual(len(rows[2]["score_reasons"]),
                         len(A.criteria_for_level(A.validated_manifest(MANIFEST), 6)))

    def test_missing_domain_never_gets_default_or_partial_full_level_score(self):
        trial = scored_trial(6)
        trial["evidence"]["safety"] = {
            "status": "UNPUBLISHED", "reason": "No independently verified safety source"}
        rows = A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        self.assertEqual(rows[0]["score_out_of_100"], 80)
        self.assertEqual(rows[1]["score_out_of_100"], 80)
        self.assertIsNone(rows[2]["score_out_of_100"])
        self.assertIn("safety", [x["criterion"] for x in rows[2]["evidence_gaps"]])
        self.assertEqual(rows[2]["assessment_status"],
                         "UNSCORED_PHASE_APPROPRIATE_EVIDENCE_INCOMPLETE")

    def test_phase2_can_exempt_application_only_items_but_not_safety(self):
        trial = scored_trial(6)
        trial["phase"] = "PHASE2"
        trial["application_stage"] = "PRE_APPLICATION"
        trial.pop("application_source")
        for field in ("regulatory_sources", "manufacturing_cmc"):
            trial["evidence"][field] = {"status": "NOT_YET_EXPECTED"}
        rows = A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        self.assertEqual(rows[2]["score_out_of_100"], 80)
        self.assertEqual(rows[2]["phase_not_yet_expected_criteria"], 2)
        trial["evidence"]["safety"] = {"status": "NOT_YET_EXPECTED"}
        with self.assertRaisesRegex(ValueError, "Cannot exempt"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)

    def test_unverified_phase_never_score_and_filing_needs_primary_receipt(self):
        trial = scored_trial(6)
        trial["phase"] = "UNKNOWN_OR_NOT_APPLICABLE"
        self.assertTrue(all(x["score_out_of_100"] is None for x in
                            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)))
        trial = scored_trial(6)
        trial.pop("application_source")
        with self.assertRaisesRegex(ValueError, "original-source receipt"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)

    def test_source_cutoff_no_future_leakage_or_unbounded_urls(self):
        trial = scored_trial(6)
        trial["evidence"]["efficacy"]["source"]["published_on"] = "2026-11-13"
        with self.assertRaisesRegex(ValueError, "cutoff"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        trial = scored_trial(6)
        trial["phase_source"]["url"] = "http://clinicaltrials.gov/study/NCT05507203"
        with self.assertRaises(ValueError):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)

    def test_actual_fda_outcome_blinding(self):
        trial = scored_trial(6)
        trial["actual_outcome"] = "approved"
        with self.assertRaisesRegex(ValueError, "Known final FDA outcome"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)

    def test_rubric_score_finite_and_reasoned_not_proven_by_label(self):
        trial = scored_trial(6)
        trial["evidence"]["efficacy"]["rubric_score"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        trial = scored_trial(6)
        trial["evidence"]["efficacy"]["reason"] = "positive"
        with self.assertRaisesRegex(ValueError, "explanation"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)
        trial = scored_trial(6)
        trial["evidence"]["efficacy"]["source"]["sha256"] = "madeup"
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            A.assessment_for_trial(trial, A.validated_manifest(MANIFEST), DATE)

    def test_duplicate_ids_and_extra_trial_fail_closed(self):
        roster = copy.deepcopy(ROSTER)
        roster["trials"].append(roster["trials"][0])
        roster["trial_count"] += 1
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            A.build(MANIFEST, roster, None)
        evidence = {"schema_version": 1, "as_of": "2026-11-12",
                    "trials": [dict(scored_trial(), nct="NCT00000000")]}
        with self.assertRaisesRegex(ValueError, "not in dated FOCUS"):
            A.build(MANIFEST, ROSTER, evidence)

    def test_partial_32_focus_build_keeps_no_false_scientific_acceptance(self):
        item = scored_trial(6)
        output = A.build(MANIFEST, ROSTER, {
            "schema_version": 1, "as_of": "2026-11-12", "trials": [item]})
        self.assertEqual(output["per_level"][0]["provisional_numeric_scores"], 1)
        self.assertEqual(output["per_level"][2]["provisional_numeric_scores"], 1)
        self.assertEqual(output["per_level"][3]["provisional_numeric_scores"], 0)
        self.assertEqual(output["per_level"][2]["complete_scientific_assessments"], 0)
        self.assertFalse(output["per_level"][2]["all_focus_trials_scored"])
        self.assertTrue(output["per_level"][2]["review_required"])

    def test_coverage_gate_rejects_synthetic_score_count_without_32_source_rows(self):
        # One score must never satisfy the stage, even if summary JSON is falsified.
        result = A.build(MANIFEST, ROSTER, {
            "schema_version": 1, "as_of": "2026-11-12", "trials": [scored_trial(6)]})
        result["per_level"][2]["provisional_numeric_scores"] = 32
        result["per_level"][2]["unscored"] = 0
        result["per_level"][2]["all_focus_trials_scored"] = True
        with self.assertRaises(ValueError):
            A.audit_level_coverage(result, ROSTER, 6)

    def test_coverage_gate_all_32_synthetic_source_scored_ready_not_accepted(self):
        evidence = {"schema_version": 1, "as_of": "2026-11-12", "trials": []}
        for entry in ROSTER["trials"]:
            item = scored_trial(6)
            item["nct"] = entry["nct"]
            item["phase_source"]["url"] = "https://clinicaltrials.gov/study/"+entry["nct"]
            evidence["trials"].append(item)
        result = A.build(MANIFEST, ROSTER, evidence)
        audited = A.audit_level_coverage(result, ROSTER, 6)
        self.assertEqual(audited["provisional_scored"], 32)
        self.assertTrue(audited["ready_for_independent_review"])
        self.assertFalse(audited["scientific_level_accepted"])
        self.assertTrue(all(a["fda_approval_probability"] is None for a in
                            result["assessments"]))

    def test_coverage_gate_rejects_missing_score_rationale_and_future_source(self):
        evidence = {"schema_version": 1, "as_of": "2026-11-12", "trials": []}
        for entry in ROSTER["trials"]:
            item = scored_trial(6)
            item["nct"] = entry["nct"]
            item["phase_source"]["url"] = "https://clinicaltrials.gov/study/"+entry["nct"]
            evidence["trials"].append(item)
        result = A.build(MANIFEST, ROSTER, evidence)
        target = next(x for x in result["assessments"] if x["level"] == 6)
        target["verified_source_ratings"][0]["reason"] = ""
        with self.assertRaises(ValueError):
            A.audit_level_coverage(result, ROSTER, 6)
        target["verified_source_ratings"][0]["reason"] = "Sourced prespecified trial design evidence"
        target["verified_source_ratings"][0]["source"]["published_on"] = "2026-11-13"
        with self.assertRaises(ValueError):
            A.audit_level_coverage(result, ROSTER, 6)

    def test_output_atomic_json_and_no_automatic_publication(self):
        result = A.build(MANIFEST, ROSTER, None)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "assessment.json"
            A.safe_write(path, result)
            restored = json.loads(path.read_text())
        self.assertEqual(restored["assessment_records"], 544)
        self.assertFalse(restored["production_publication"])


if __name__ == "__main__":
    unittest.main()
