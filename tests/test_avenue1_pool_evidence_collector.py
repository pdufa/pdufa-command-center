import unittest
from unittest.mock import patch
from scripts.avenue1_pool_evidence_collector import find_ncts, study_evidence

class CollectorTests(unittest.TestCase):
    def test_only_trial_records_in_whole_pool(self):
        snapshot = {
            "sourceHealth": {"state": "FRESH", "pipelineSourceParity": {"exactPrograms": 4}},
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

    def test_null_registry_results_lists_are_safe(self):
        payload = {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": None}}}
        with patch("scripts.avenue1_pool_evidence_collector.fetch_json", return_value=payload):
            result = study_evidence("NCT05507203")
        self.assertEqual(result["clinical_dimensions"]["effect_magnitude"], [])
        self.assertEqual(result["clinical_dimensions"]["statistical_reliability"], [])

if __name__ == "__main__":
    unittest.main()
