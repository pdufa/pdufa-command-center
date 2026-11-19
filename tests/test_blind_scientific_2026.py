"""Synthetic contract fixtures only, never used as study evidence."""

from copy import deepcopy
import csv
import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import blind_scientific_2026 as engine
from app.scientific_levels_two_to_six import assess_levels_two_to_six


class HistoricalScientificExecutionTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "event_id": "UNIT-001", "application_number": "NDA000000",
            "review_cycle": "ORIG:1", "drug": "Fixture", "indication": "Fixture",
            "decision_date": "2026-04-30",
        }
        self.nct = "NCT00000000"
        self.receipt = {
            "source": "https://example.org/paper",
            "sourceDate": "2026-01-01",
            "sourceVersionUrl": "https://example.org/paper/rev-1",
            "sourceVersionDate": "2026-02-01",
            "sourceRetrievedAt": "2026-05-02",
            "sourceVerifiedAt": "2026-05-03",
            "sourceVerifiedBy": "Fixture",
            "reviewedAt": "2026-05-04",
            "reviewerId": "Fixture",
            "rationale": "Synthetic fixture tests execution only",
        }
        self.review = {
            **self.receipt, "status": "REVIEWED", "judgment": "SUPPORTS",
            "documentType": "PRIMARY_EVIDENCE", "evidenceExcerpt": "Synthetic excerpt",
            "sourceVerificationMethod": "DIRECT_DOCUMENT_REVIEW", "material_blocker": False,
        }
        self.package = {
            **{key: self.event[key] for key in ("event_id", "application_number", "review_cycle")},
            "outcome_exposure": "OUTCOME_UNEXPOSED",
            "trial_set_rationale": "Synthetic linkage for a prespecified pivotal trial",
            "trials": [self.make_trial(self.nct)],
        }

    def make_trial(self, nct):
        document = {"protocolSection": {
            "identificationModule": {"nctId": nct},
            "statusModule": {
                "lastUpdatePostDateStruct": {"date": "2026-02-01"},
                "overallStatus": "COMPLETED",
            },
            "designModule": {"phases": ["PHASE3"], "designInfo": {"allocation": "RANDOMIZED"}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Fixture", "timeFrame": "Week 8"}]},
        }}
        return {
            "nct_id": nct,
            "linkage": dict(self.receipt),
            "registry": {
                "document": document,
                "documentSha256": engine.canonical_digest(document),
                "sourceVersionUrl": f"https://clinicaltrials.gov/study/{nct}?tab=history&a=1",
                "sourceVersionDate": "2026-02-01",
                "sourceRetrievedAt": "2026-05-02",
            },
            "reviews": {key: dict(self.review) for key in engine.CRITERIA},
        }

    def lock(self):
        return engine.make_lock([self.event], [self.package], 30)

    def predictions(self, lock):
        return {row["level"]: row for row in engine.verify_canonical_lock(lock, lock["lock_sha256"])}

    def test_separate_science_and_direction_for_all_six_levels(self):
        lock = self.lock()
        scientific = lock["feature_snapshots"][0]["scientific_ratings"][0]
        self.assertEqual(scientific["L01"]["registryVersionAvailableAt"], "2026-02-01")
        self.assertEqual(scientific["L01"]["registryRetrievedAt"], "2026-05-02")
        self.assertEqual(scientific["L01"]["executionStatus"], "INTAKE_ONLY")
        self.assertEqual(scientific["L06"]["fdaPrediction"], "ABSTAIN")
        self.assertIsNone(scientific["L06"]["score"])
        self.assertEqual(
            scientific["L06"]["acceptedEvidence"]["manufacturingReadiness"]["reviewedAt"],
            "2026-05-04",
        )
        directions = {level: row["prediction"] for level, row in self.predictions(lock).items()}
        self.assertEqual(directions, {
            "L01": "ABSTAIN", "L02": "ABSTAIN", "L03": "APPROVE",
            "L04": "APPROVE", "L05": "APPROVE", "L06": "APPROVE",
        })
        self.assertEqual(
            {item["cutoff_date"] for item in self.predictions(lock).values()}, {"2026-03-31"}
        )

    def test_scoring_uses_verified_lock_and_exact_fda_cycle(self):
        from report_blind_six_levels_2026 import score
        from score_scientific_backtest_2026 import validate_ledger

        lock = self.lock()
        truth = {**self.event, "actual_outcome": "APPROVE",
                 "identity_status": "VERIFIED_ELIGIBLE", "fda_source_url": "https://fda.gov/fixture"}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            args = SimpleNamespace(
                output=base / "summary.json", locked=base / "locked.json",
                outcomes=base / "outcomes.csv", expected_lock_sha256=lock["lock_sha256"],
            )
            engine.write_new_lock(args.locked, lock)
            with args.outcomes.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=truth)
                writer.writeheader()
                writer.writerow(truth)
            with patch("builtins.print"):
                score(args, engine.verify_canonical_lock, engine.load_csv, validate_ledger)
            summary = json.loads(args.output.read_text())
        self.assertEqual([row["level"] for row in summary], list(engine.LEVELS))
        self.assertIsNone(summary[0]["accuracy"])
        self.assertEqual(summary[2]["correct"], 1)

    def test_material_blocker_and_unknown_have_different_dispositions(self):
        trial = self.package["trials"][0]
        trial["reviews"]["3.primaryEndpointResults"].update(
            judgment="CONCERNS", material_blocker=True,
        )
        trial["reviews"]["6.manufacturingReadiness"] = {
            "status": "UNKNOWN", "reviewedAt": "2026-05-04",
            "reviewerId": "Fixture", "rationale": "No eligible source was available.",
        }
        rows = self.predictions(self.lock())
        self.assertEqual(rows["L03"]["prediction"], "CRL")
        self.assertEqual(rows["L03"]["criterion_references"], [f"{self.nct}:primaryEndpointResults"])
        self.assertEqual(rows["L06"]["prediction"], "ABSTAIN")
        self.assertIn("manufacturingReadiness:NOT_ASSESSED", rows["L06"]["criterion_references"][0])

    def test_contradictory_pivotal_trials_abstain(self):
        trial = self.package["trials"][0]
        trial["reviews"]["3.primaryEndpointResults"].update(
            judgment="CONCERNS", material_blocker=True,
        )
        self.package["trials"].append(self.make_trial("NCT00000001"))
        result = self.predictions(self.lock())["L03"]
        self.assertEqual(result["prediction"], "ABSTAIN")
        self.assertEqual(result["reason"], "mixed_pivotal_trial_findings")

    def test_missing_reviews_exposed_case_and_outcome_fields_rejected(self):
        self.package["trials"][0]["reviews"].pop("2.protocol")
        with self.assertRaisesRegex(ValueError, "Expected fields"):
            self.lock()
        self.package["trials"][0]["reviews"]["2.protocol"] = dict(self.review)
        self.package["outcome_exposure"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "outcome exposure"):
            self.lock()
        self.package["outcome_exposure"] = "OUTCOME_UNEXPOSED"
        self.package["trials"][0]["registry"]["document"]["actualOutcome"] = "APPROVE"
        with self.assertRaisesRegex(ValueError, "Outcome-bearing evidence field"):
            self.lock()

    def test_latest_registry_endpoint_cannot_supply_a_post_cutoff_capture(self):
        self.package["trials"][0]["registry"]["sourceVersionUrl"] = (
            f"https://clinicaltrials.gov/api/v2/studies/{self.nct}"
        )
        with self.assertRaisesRegex(ValueError, "pinned registry revision"):
            self.lock()

    def test_registry_identity_and_evidence_versions_must_match_cutoff(self):
        trial = self.package["trials"][0]
        trial["registry"]["documentSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Registry document hash mismatch"):
            self.lock()
        trial["registry"]["documentSha256"] = engine.canonical_digest(trial["registry"]["document"])
        trial["reviews"]["2.protocol"]["sourceVersionDate"] = "2026-04-01"
        with self.assertRaisesRegex(ValueError, "chronology failed"):
            self.lock()

    def test_existing_scientific_contract_does_not_accept_late_review_by_default(self):
        lock = self.lock()
        intake = lock["feature_snapshots"][0]["scientific_ratings"][0]["L01"]
        evidence = {"2.protocol": {**self.review, "nctId": self.nct, "sourceVerified": True}}
        result = assess_levels_two_to_six(intake, trial_id=self.nct, evidence=evidence)
        self.assertEqual(result["2"]["criteria"]["protocol"], "REJECTED_EVIDENCE")

    def test_independent_digest_detects_rehashed_evidence_and_decision(self):
        lock = self.lock()
        frozen = lock["lock_sha256"]
        revised = deepcopy(lock)
        revised["predictions"][0]["prediction"] = "APPROVE"
        revised["predictions_sha256"] = engine.canonical_digest(revised["predictions"])
        revised.pop("lock_sha256")
        revised["lock_sha256"] = engine.canonical_digest(revised)
        with self.assertRaisesRegex(ValueError, "lock integrity failure"):
            engine.verify_canonical_lock(revised, frozen)

    def test_grid_verifier_rejects_duplicate_level_even_with_matching_digest(self):
        lock = self.lock()
        lock["predictions"][1] = dict(lock["predictions"][0])
        lock["predictions_sha256"] = engine.canonical_digest(lock["predictions"])
        lock.pop("lock_sha256")
        lock["lock_sha256"] = engine.canonical_digest(lock)
        with self.assertRaisesRegex(ValueError, "duplicate canonical prediction grid"):
            engine.verify_canonical_lock(lock, lock["lock_sha256"])
