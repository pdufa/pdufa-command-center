"""The Level 6 provisional scoring / blind evaluation contract fails closed."""
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pdufa_scoring_replay_guard import (score_trials, validate_freeze, evaluate,
                                        write_json, read_json)


def trial(scores=None):
    return {
        "ticker": "TICK", "nct": "NCT12345678",
        "registry_status": "COMPLETED",
        "phase_evidence": "Phase 3 results publicly posted, independently pending source review",
        "snapshot_date": "2026-11-12",
        "source_url": "https://clinicaltrials.gov/study/NCT12345678",
        "clinical_components": scores if scores is not None else [75, 50, 75, 50, 50],
    }


def prediction(category="PROSPECTIVE_CANDIDATE"):
    return {
        "application_id": "TICK|NDA-2026|indication-A",
        "ncts": ["NCT12345678", "NCT87654321"],
        "model_version": "candidate-v0",
        "phase_verification": "source snapshotted from clinical trial registry",
        "validation_class": category,
        "evidence_cutoff_utc": "2026-11-12T18:00:00Z",
        "freeze_utc": "2026-11-12T18:10:00Z",
        "evidence_receipts": [{
            "sha256": "c" * 64,
            "published_utc": "2026-11-10T00:00:00Z",
            "accessed_utc": "2026-11-12T18:05:00Z",
        }],
        "direction": "APPROVAL",
        "approval_probability": 0.70,
    }


def outcome(reviewed=False):
    return {
        "application_id": "TICK|NDA-2026|indication-A",
        "outcome": "APPROVAL",
        "decision_utc": "2026-12-10T18:00:00Z",
        "verified_fda_source_url": "https://www.fda.gov/drugs",
        "independent_blind_freeze_audit": reviewed,
        "freeze_proof_reference": "https://github.com/pdufa/pdufa-command-center/commit/example",
    }


class ProvisionalScoreTests(unittest.TestCase):
    def test_full_score_no_fda_prediction(self):
        out = score_trials([trial([75, 50, 75, 50, 50])])
        self.assertEqual((out["five_of_five"], out["partial"], out["not_scoreable"]), (1, 0, 0))
        row = out["trials"][0]
        self.assertEqual(row["fully_observed_clinical_five_100"], 60)
        self.assertEqual(row["observed_only_mean_100"], 60)
        self.assertIsNone(row["fda_approval_probability"])
        self.assertFalse(row["complete_level6_scientific_assessment"])
        self.assertEqual((row["theoretical_min_100"], row["theoretical_max_100"]), (60, 60))

    def test_incomplete_not_imputed_as_five_of_five(self):
        out = score_trials([trial([75, None, 75, 50, 50])])
        self.assertEqual(out["partial"], 1)
        row = out["trials"][0]
        self.assertEqual(row["component_coverage"], "4/5")
        self.assertEqual(row["observed_only_mean_100"], 62.5)
        self.assertIsNone(row["fully_observed_clinical_five_100"])
        self.assertEqual((row["theoretical_min_100"], row["theoretical_max_100"]), (50, 70))
        self.assertEqual(row["missing_component_indices"], [2])

    def test_zero_coverage_not_fabricated_zero_score(self):
        out = score_trials([trial([None] * 5)])
        self.assertEqual(out["not_scoreable"], 1)
        self.assertIsNone(out["trials"][0]["observed_only_mean_100"])
        self.assertIsNone(out["trials"][0]["theoretical_min_100"])
        self.assertIsNone(out["trials"][0]["theoretical_max_100"])

    def test_unknown_phase_and_evidence_rejected(self):
        r = trial()
        r["phase_evidence"] = ""
        with self.assertRaises(ValueError):
            score_trials([r])

    def test_no_actual_outcomes_in_score_input(self):
        r = trial()
        r["fda_outcome"] = "APPROVAL"
        with self.assertRaisesRegex(ValueError, "Outcome leakage"):
            score_trials([r])

    def test_nct_dedup(self):
        with self.assertRaises(ValueError):
            score_trials([trial(), trial()])


class FreezeTests(unittest.TestCase):
    def test_frozen_is_hash_pinned_and_outcome_free(self):
        lock = validate_freeze([prediction()])
        self.assertEqual(lock["body"]["mode"], "FROZEN_PREDICTIONS_NO_OUTCOMES_INCLUDED")
        self.assertEqual(len(lock["sha256"]), 64)
        self.assertFalse(lock["body"]["automatic_scientific_signoff"])

    def test_future_published_evidence_fails(self):
        r = prediction()
        r["evidence_receipts"][0]["published_utc"] = "2026-11-12T19:00:00Z"
        with self.assertRaisesRegex(ValueError, "Post-cutoff"):
            validate_freeze([r])

    def test_future_access_evidence_fails(self):
        r = prediction()
        r["evidence_receipts"][0]["accessed_utc"] = "2026-11-12T19:00:00Z"
        with self.assertRaisesRegex(ValueError, "Post-freeze"):
            validate_freeze([r])

    def test_outcome_leakage_fails(self):
        r = prediction()
        r["outcome"] = "APPROVAL"
        with self.assertRaisesRegex(ValueError, "Outcome leakage"):
            validate_freeze([r])

    def test_duplicate_fda_application_is_not_two_cases(self):
        with self.assertRaisesRegex(ValueError, "unique FDA application"):
            validate_freeze([prediction(), prediction()])

    def test_abstention_cannot_claim_probability(self):
        r = prediction()
        r["direction"] = "ABSTAIN"
        with self.assertRaises(ValueError):
            validate_freeze([r])

    def test_frozen_manifest_is_create_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frozen.json"
            lock = validate_freeze([prediction()])
            write_json(path, lock, exclusive=True)
            self.assertEqual(read_json(path), lock)
            with self.assertRaises(FileExistsError):
                write_json(path, lock, exclusive=True)


class EvaluationTests(unittest.TestCase):
    def test_outcome_aware_retrospective_excluded_even_with_audit_flag(self):
        lock = validate_freeze([prediction("RETROSPECTIVE_REPLAY")])
        result = evaluate(lock, [outcome(reviewed=True)])
        self.assertEqual(result["valid_blind_cases"], 0)
        self.assertIsNone(result["blind_accuracy"])
        self.assertIn("REPLAY_EXCLUDED", result["records"][0]["class"])

    def test_no_unverified_blind_accuracy(self):
        lock = validate_freeze([prediction()])
        result = evaluate(lock, [outcome(reviewed=False)])
        self.assertEqual(result["valid_blind_cases"], 0)
        self.assertIsNone(result["blind_accuracy"])
        self.assertIn("UNVERIFIED", result["records"][0]["class"])

    def test_audited_prospective_correct_scores_once_per_application(self):
        lock = validate_freeze([prediction()])
        result = evaluate(lock, [outcome(reviewed=True)])
        self.assertEqual(result["valid_blind_cases"], 1)
        self.assertEqual(result["blind_accuracy"], 1.0)
        self.assertEqual(result["always_approve_baseline"], 1.0)
        self.assertAlmostEqual(result["brier_score"], 0.09)

    def test_freeze_after_decision_rejected_from_blind_accuracy(self):
        lock = validate_freeze([prediction()])
        case = outcome(reviewed=True)
        case["decision_utc"] = "2026-11-12T18:08:00Z"
        result = evaluate(lock, [case])
        self.assertEqual(result["valid_blind_cases"], 0)
        self.assertIn("NOT_FROZEN", result["records"][0]["class"])

    def test_tampered_freeze_rejected(self):
        lock = validate_freeze([prediction()])
        lock["body"]["predictions"][0]["direction"] = "CRL"
        with self.assertRaisesRegex(ValueError, "tampered"):
            evaluate(lock, [outcome(reviewed=True)])

    def test_zero_valid_cases_has_no_accuracy_or_brier(self):
        lock = validate_freeze([prediction()])
        r = evaluate(lock, [])
        self.assertEqual(r["valid_blind_cases"], 0)
        self.assertIsNone(r["blind_accuracy"])
        self.assertIsNone(r["brier_score"])
        self.assertIsNone(r["always_approve_baseline"])

    def test_duplicate_outcomes_rejected(self):
        lock = validate_freeze([prediction()])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(lock, [outcome(), outcome()])


if __name__ == "__main__":
    unittest.main()
