import unittest
import json
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch
from scripts.avenue1_pool_evidence_collector import find_ncts, study_evidence

class CollectorTests(unittest.TestCase):
    def test_only_trial_records_in_whole_pool(self):
        snapshot = {
            "sourceHealth": {"state": "FRESH", "clinicalRows": 3, "regulatoryRows": 1, "pipelineSourceParity": {"exactPrograms": 4}},
            "pipeline": [
                {"id": "TRIAL|NCT05507203", "ticker": "ABVX"},
                {"id": "RESULT|NCT05507216", "ticker": "ABVX"},
                {"id": "TRIAL|NCT05507216", "ticker": "ABVX"},
                {"id": "FDA|NCT05507203", "ticker": "ABVX"}
            ]
        }
        self.assertEqual(find_ncts(snapshot), ["NCT05507203", "NCT05507216"])

    def test_fails_closed_on_source_drift(self):
        with self.assertRaises(RuntimeError):
            find_ncts({"pipeline": [{"id": "TRIAL|NCT05507203"}],
                       "sourceHealth": {"state": "STALE", "pipelineSourceParity": {"exactPrograms": 1}}})

    def test_rejects_unknown_freshness(self):
        snapshot = {"pipeline": [{"id": "TRIAL|NCT05507203"}],
                    "sourceHealth": {"state": "UNKNOWN", "clinicalRows": 1,
                                     "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 1}}}
        with self.assertRaises(RuntimeError):
            find_ncts(snapshot)

    def test_rejects_source_count_mismatch(self):
        snapshot = {"pipeline": [{"id": "TRIAL|NCT05507203"}],
                    "sourceHealth": {"state": "FRESH", "clinicalRows": 0,
                                     "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 1}}}
        with self.assertRaises(RuntimeError):
            find_ncts(snapshot)

    def test_duplicate_trial_identity_rejected(self):
        snapshot = {
            "sourceHealth": {"state": "FRESH", "clinicalRows": 2,
                             "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 2}},
            "pipeline": [{"id": "TRIAL|NCT05507203"}, {"id": "TRIAL|NCT05507203"}],
        }
        with self.assertRaisesRegex(RuntimeError, "Duplicate POOL trial identity"):
            find_ncts(snapshot)

    def test_non_trial_rows_are_not_mistaken_for_trials(self):
        snapshot = {
            "sourceHealth": {"state": "FRESH", "clinicalRows": 1,
                             "regulatoryRows": 1, "pipelineSourceParity": {"exactPrograms": 2}},
            "pipeline": [{"id": "FDA|NCT05507203"}, {"id": "RESULT|NCT05507216"}],
        }
        self.assertEqual(find_ncts(snapshot), [])

    def test_results_not_inferred_when_missing(self):
        payload = {"protocolSection": {"statusModule": {"overallStatus": "COMPLETED"},
                   "outcomesModule": {"primaryOutcomes": [{"measure": "Clinical remission"}]}}}
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        self.assertFalse(result["results_posted"])
        self.assertEqual(result["ten_category_scoring"], "PENDING_EVIDENCE_REVIEW")

    def test_extracts_ten_dimensions_without_assigning_scores(self):
        payload = {
            "protocolSection": {
                "designModule": {"designInfo": {"allocation": "RANDOMIZED"}},
                "outcomesModule": {"primaryOutcomes": [{"measure": "Response"}]},
                "armsInterventionsModule": {"armGroups": [{"label": "Placebo"}]},
            },
            "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
                {"title": "Response", "analyses": [{"pValue": "0.01"}]},
            ]}},
        }
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        dimensions = result["clinical_dimensions"]
        self.assertEqual(len(dimensions), 10)
        self.assertEqual(dimensions["statistical_reliability"][0]["pValue"], "0.01")
        self.assertEqual(dimensions["standard_of_care_comparator"][0]["label"], "Placebo")
        self.assertEqual(result["ten_category_scoring"], "PENDING_EVIDENCE_REVIEW")

    def test_significant_p_value_and_placebo_do_not_prove_soc_superiority(self):
        payload = {
            "protocolSection": {
                "armsInterventionsModule": {"armGroups": [
                    {"label": "Investigational treatment"},
                    {"label": "Placebo", "type": "PLACEBO_COMPARATOR"},
                ]},
            },
            "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
                {"title": "Response", "analyses": [{"pValue": "0.001"}]},
            ]}},
        }
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        self.assertEqual(result["superiority_to_active_soc"], "NOT_ESTABLISHED_WITHOUT_COMPARATOR_REVIEW")
        self.assertEqual(result["ten_category_scoring"], "PENDING_EVIDENCE_REVIEW")
        self.assertEqual(result["clinical_dimensions"]["statistical_reliability"][0]["pValue"], "0.001")

    def test_null_registry_results_lists_are_safe(self):
        payload = {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": None}}}
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        self.assertEqual(result["clinical_dimensions"]["effect_magnitude"], [])
        self.assertEqual(result["clinical_dimensions"]["statistical_reliability"], [])


    def test_malformed_outcome_analyses_fail_closed(self):
        for bad in ({"pValue": "0.01"}, ["not-an-analysis"], [None]):
            payload = {"resultsSection": {"outcomeMeasuresModule": {
                "outcomeMeasures": [{"title": "Response", "analyses": bad}],
            }}}
            with self.subTest(bad=bad), patch(
                "scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload
            ):
                with self.assertRaisesRegex(ValueError, "Invalid ClinicalTrials.gov outcome analysis"):
                    study_evidence("NCT05507203")

    def test_malformed_outcome_measures_fail_closed(self):
        for bad in ({"unexpected": "mapping"}, [None], ["not-a-measure"]):
            payload = {"resultsSection": {"outcomeMeasuresModule": {
                "outcomeMeasures": bad,
            }}}
            with self.subTest(bad=bad), patch(
                "scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload
            ):
                with self.assertRaisesRegex(ValueError, "Invalid ClinicalTrials.gov"):
                    study_evidence("NCT05507203")

    def test_null_design_info_is_not_scored_as_evidence(self):
        payload = {"protocolSection": {"designModule": {"designInfo": None}}}
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        quality = result["clinical_dimensions"]["evidence_quality"]
        self.assertIsNone(quality["allocation"])
        self.assertIsNone(quality["masking"])
        self.assertEqual(result["ten_category_scoring"], "PENDING_EVIDENCE_REVIEW")

    def test_null_registry_arm_and_reference_lists_are_safe(self):
        payload = {"protocolSection": {
            "armsInterventionsModule": {"armGroups": None},
            "referencesModule": {"references": None},
        }}
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        self.assertEqual(result["clinical_dimensions"]["standard_of_care_comparator"], [])
        self.assertEqual(result["clinical_dimensions"]["evidence_quality"]["references"], [])

    def test_inventory_and_status_share_stable_source_digest(self):
        from scripts.avenue1_pool_evidence_collector import main
        import hashlib
        snapshot = {
            "asOf": "2026-11-18",
            "sourceHealth": {"state": "FRESH", "clinicalRows": 1,
                "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 1}},
            "pipeline": [{"id": "TRIAL|NCT05507203"}],
        }
        expected = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.avenue1_pool_evidence_collector.pool_records", return_value=snapshot), \
                 patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value={}), \
                 patch("scripts.avenue1_pool_evidence_collector.time.sleep"), \
                 patch.object(sys, "argv", ["collector", "--output-dir", directory]):
                self.assertEqual(main(), 0)
            inventory = json.loads((Path(directory) / "pool-source-inventory.json").read_text())
            status = json.loads((Path(directory) / "collection-status.json").read_text())
            self.assertEqual(inventory["source_sha256"], expected)
            self.assertEqual(status["pool_source_sha256"], expected)
            self.assertEqual(inventory["source_as_of"], "2026-11-18")
            evidence = json.loads((Path(directory) / "clinical-evidence.jsonl").read_text().strip())
            self.assertEqual(evidence["pool_source_sha256"], expected)

    def test_collection_partial_failure_does_not_claim_completion(self):
        from scripts.avenue1_pool_evidence_collector import main
        snapshot = {
            "asOf": "2026-11-17",
            "sourceHealth": {"state": "FRESH", "clinicalRows": 2,
                "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 2}},
            "pipeline": [{"id": "TRIAL|NCT05507203"}, {"id": "TRIAL|NCT05507216"}],
        }
        def fake_fetch(url):
            if url.endswith("NCT05507216"):
                raise RuntimeError("simulated source failure")
            return {"protocolSection": {"outcomesModule": {"primaryOutcomes": [{"measure": "Response"}]}}}
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.avenue1_pool_evidence_collector.pool_records", return_value=snapshot), \
                 patch("scripts.avenue1_pool_evidence_collector.fetch_json", side_effect=fake_fetch), \
                 patch("scripts.avenue1_pool_evidence_collector.time.sleep"), \
                 patch.object(sys, "argv", ["collector", "--output-dir", directory]):
                self.assertEqual(main(), 2)
            status = json.loads((Path(directory) / "collection-status.json").read_text())
            self.assertEqual(status["attempted"], 2)
            self.assertEqual(status["collected"], 1)
            self.assertEqual(status["error_count"], 1)
            self.assertEqual(status["coverage_percent"], 50.0)
            self.assertTrue(status["full_pool_run"])
            self.assertFalse(status["full_pool_collection_complete"])

    def test_limited_smoke_run_never_claims_full_pool(self):
        from scripts.avenue1_pool_evidence_collector import main
        snapshot = {
            "asOf": "2026-11-17",
            "sourceHealth": {"state": "FRESH", "clinicalRows": 2,
                "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 2}},
            "pipeline": [{"id": "TRIAL|NCT05507203"}, {"id": "TRIAL|NCT05507216"}],
        }
        payload = {"protocolSection": {"outcomesModule": {"primaryOutcomes": [{"measure": "Response"}]}}}
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.avenue1_pool_evidence_collector.pool_records", return_value=snapshot), \
                 patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload), \
                 patch("scripts.avenue1_pool_evidence_collector.time.sleep"), \
                 patch.object(sys, "argv", ["collector", "--output-dir", directory, "--limit", "1"]):
                self.assertEqual(main(), 0)
            status = json.loads((Path(directory) / "collection-status.json").read_text())
            self.assertEqual(status["attempted"], 1)
            self.assertEqual(status["collected"], 1)
            self.assertEqual(status["coverage_percent"], 100.0)
            self.assertFalse(status["full_pool_run"])
            self.assertFalse(status["full_pool_collection_complete"])

    def test_collection_coverage_and_missing_fields_are_reported(self):
        from scripts.avenue1_pool_evidence_collector import main
        snapshot = {
            "asOf": "2026-11-16",
            "sourceHealth": {"state": "FRESH", "clinicalRows": 1,
                "regulatoryRows": 0, "pipelineSourceParity": {"exactPrograms": 1}},
            "pipeline": [{"id": "TRIAL|NCT05507203", "ticker": "ABVX"}],
        }
        payload = {"protocolSection": {"outcomesModule": {
            "primaryOutcomes": [{"measure": "Clinical remission"}]}}}
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.avenue1_pool_evidence_collector.pool_records", return_value=snapshot), \
                 patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload), \
                 patch("scripts.avenue1_pool_evidence_collector.time.sleep"), \
                 patch.object(sys, "argv", ["collector", "--output-dir", directory]):
                self.assertEqual(main(), 0)
            status = json.loads((Path(directory) / "collection-status.json").read_text())
            self.assertEqual(status["collected"], 1)
            self.assertEqual(status["attempted"], 1)
            self.assertEqual(status["error_count"], 0)
            self.assertEqual(status["coverage_percent"], 100.0)
            self.assertTrue(status["full_pool_run"])
            self.assertTrue(status["full_pool_collection_complete"])
            self.assertEqual(status["dimension_evidence_counts"]["primary_endpoint"], 1)
            self.assertEqual(status["dimension_evidence_counts"]["effect_magnitude"], 0)
            self.assertIn("effect_magnitude", status["missing_dimensions_by_trial"][0]["missing_dimensions"])
            self.assertEqual(len((Path(directory) / "clinical-evidence.jsonl").read_text().splitlines()), 1)

if __name__ == "__main__":
    unittest.main()
