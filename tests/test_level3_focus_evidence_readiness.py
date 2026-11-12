"""Level 3 phase-first research readiness: original source facts are not verdicts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from level3_focus_evidence_readiness import build_readiness, extract_study_context
from windows_local_agent_live_focus_registry import atomic_json, make_envelope

NOW = datetime(2026, 11, 11, 22, 0, tzinfo=timezone.utc)
NCT = "NCT00000001"


def registry(phase="PHASE3", results=False):
    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT},
            "designModule": {"phases": [phase]},
            "statusModule": {"overallStatus": "COMPLETED"},
            "conditionsModule": {"conditions": ["Synthetic condition"]},
            "armsInterventionsModule": {
                "interventions": [{"name": "Synthetic treatment"}]
            },
            "outcomesModule": {
                "primaryOutcomes": [
                    {"measure": "Synthetic primary endpoint", "timeFrame": "Week 12"}
                ]
            },
        }
    }
    if results:
        payload["resultsSection"] = {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [{"title": "Reported measure"}]
            },
            "participantFlowModule": {"preAssignmentDetails": "Source supplied"},
            "adverseEventsModule": {"timeFrame": "13 weeks"},
        }
    return payload


def fake_meta(nct=NCT, time=NOW):
    return {
        "nct": nct,
        "source_url": "https://clinicaltrials.gov/api/v2/studies/" + nct,
        "source_type": "PRIMARY_REGISTRY",
        "retrieved_at_utc": time.isoformat(),
        "sha256": hashlib.sha256(("synthetic:" + nct).encode()).hexdigest(),
        "scientific_adjudication": "NOT_ADJUDICATED",
        "fda_probability": None,
    }


class LevelThreeEvidenceReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.roster = {
            "schemaVersion": 1,
            "asOf": "2026-11-11",
            "records": [
                {"nct": f"NCT{i:08d}", "ticker": "TEST", "company": "Synthetic"}
                for i in range(1, 30)
            ],
        }
        self.raw = json.dumps(self.roster).encode("utf-8")
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def cache_one(self, content=None, time=NOW):
        envelope = make_envelope(
            NCT, self.digest, content or registry(),
            fake_meta(time=time),
        )
        atomic_json(self.directory / f"{NCT}.json", envelope)

    def report(self, now=NOW):
        return build_readiness(self.raw, self.directory, now)

    def test_29_missing_sources_do_not_create_assessments(self):
        report = self.report()
        self.assertEqual(report["trial_count"], 29)
        self.assertEqual(report["fresh_source_contexts"], 0)
        self.assertEqual(report["sources_without_usable_fresh_context"], 29)
        self.assertEqual(report["scientific_reviews_completed"], 0)
        self.assertEqual(report["calibrated_fda_predictions_created"], 0)
        self.assertFalse(report["production_modified"])
        self.assertTrue(all(
            row["registry_evidence"] is None
            and row["fda_prediction"] is None
            and row["scientific_signoff"] is False
            for row in report["records"]
        ))

    def test_one_valid_primitive_source_produces_readiness_not_prediction(self):
        self.cache_one()
        report = self.report()
        self.assertEqual(report["fresh_source_contexts"], 1)
        self.assertEqual(report["sources_without_usable_fresh_context"], 28)
        row = report["records"][0]
        evidence = row["registry_evidence"]
        self.assertEqual(evidence["nct"], NCT)
        self.assertEqual(evidence["phase_group"], "PHASE3_OR_LATER_SOURCE_REPORTED")
        self.assertEqual(evidence["registry_reported_phase"], ["PHASE3"])
        self.assertEqual(
            evidence["registry_reported_primary_endpoints"][0]["source_reported_measure"],
            "Synthetic primary endpoint",
        )
        self.assertIn("pivotal_result_measures_not_found_in_registry", evidence["missing_registry_source_fields"])
        self.assertFalse(evidence["source_facts_independently_adjudicated"])
        self.assertFalse(evidence["scientific_signoff"])
        self.assertIsNone(row["fda_prediction"])
        self.assertIsNone(row["approval_probability"])
        self.assertIsNone(row["clinical_score"])
        self.assertIsNone(evidence["clinical_score"])

    def test_posted_results_are_not_statistical_significance_or_approval(self):
        source = extract_study_context(NCT, registry(results=True))
        self.assertEqual(source["registry_result_measure_count"], 1)
        self.assertTrue(source["registry_adverse_events_module_present"])
        self.assertTrue(source["registry_participant_flow_module_present"])
        self.assertNotIn("pivotal_result_measures_not_found_in_registry", source["missing_registry_source_fields"])
        self.assertFalse(source["clinical_efficacy_established"])
        self.assertFalse(source["scientific_signoff"])
        self.assertIsNone(source["fda_prediction"])
        self.assertIsNone(source["approval_probability"])

    def test_early_phase_does_not_require_phase3_data(self):
        for phase in ("EARLY_PHASE1", "PHASE1", "PHASE2"):
            with self.subTest(phase=phase):
                result = extract_study_context(NCT, registry(phase=phase))
                self.assertEqual(result["phase_group"], "EARLIER_PHASE_SOURCE_REPORTED")
                self.assertNotIn("pivotal_result_measures_not_found_in_registry", result["missing_registry_source_fields"])
                self.assertTrue(any("Do not require Phase 3" in q for q in result["phase_appropriate_review_questions"]))

    def test_unresolved_phase_cannot_imply_phase3_failed(self):
        payload = registry()
        payload["protocolSection"]["designModule"]["phases"] = []
        result = extract_study_context(NCT, payload)
        self.assertEqual(result["phase_group"], "PHASE_UNRESOLVED_OR_NOT_APPLICABLE")
        self.assertIn("phase_not_resolved_from_registry", result["missing_registry_source_fields"])
        self.assertNotIn("pivotal_result_measures_not_found_in_registry", result["missing_registry_source_fields"])

    def test_unknown_phase_or_malformed_registry_input_rejected(self):
        invalid = registry()
        invalid["protocolSection"]["designModule"]["phases"] = ["PHASE99"]
        with self.assertRaises(ValueError):
            extract_study_context(NCT, invalid)
        with self.assertRaises(ValueError):
            extract_study_context(NCT, {"protocolSection": "bad source"})

    def test_registry_exact_nct_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_study_context("NCT99999999", registry())
        with self.assertRaises(ValueError):
            extract_study_context("NCT1", registry())

    def test_tampered_cache_is_not_counted_as_usable_source(self):
        self.cache_one()
        path = self.directory / f"{NCT}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["record"]["protocolSection"]["statusModule"]["overallStatus"] = "RECRUITING"
        path.write_text(json.dumps(data), encoding="utf-8")
        report = self.report()
        self.assertEqual(report["fresh_source_contexts"], 0)
        self.assertEqual(report["records"][0]["source_status"], "FRESH_EXACT_NCT_REGISTRY_CAPTURE_NOT_AVAILABLE")

    def test_expired_receipt_not_promoted_to_current_evidence(self):
        self.cache_one()
        tomorrow = NOW + timedelta(days=2)
        report = self.report(now=tomorrow)
        self.assertEqual(report["fresh_source_contexts"], 0)
        self.assertEqual(report["scientific_reviews_completed"], 0)

    def test_unrelated_results_and_fda_claims_not_copied_from_source(self):
        payload = registry(results=True)
        payload["fda_prediction"] = "APPROVE"
        payload["approval_probability"] = 1.0
        payload["clinical_score"] = 100
        result = extract_study_context(NCT, payload)
        self.assertNotIn("approval", result)
        self.assertIsNone(result["fda_prediction"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["clinical_score"])
        self.assertFalse(result["mechanism_validated"])

    def test_duplicate_focus_identity_is_rejected_before_source_processing(self):
        roster = json.loads(self.raw)
        roster["records"][1]["nct"] = roster["records"][0]["nct"]
        with self.assertRaises(ValueError):
            build_readiness(json.dumps(roster).encode(), self.directory, NOW)

    def test_live_32_roster_compatible_without_fictitious_cached_proof(self):
        roster = json.loads(self.raw)
        for index in range(30, 33):
            roster["records"].append({"nct": f"NCT{index:08d}", "ticker": "TEST"})
        result = build_readiness(json.dumps(roster).encode(), self.directory, NOW)
        self.assertEqual(result["trial_count"], 32)
        self.assertEqual(result["fresh_source_contexts"], 0)
        self.assertEqual(result["calibrated_fda_predictions_created"], 0)


if __name__ == "__main__":
    unittest.main()
