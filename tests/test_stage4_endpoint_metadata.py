import importlib.util
import io
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_clinicaltrials_source.py"
spec = importlib.util.spec_from_file_location("stage4_clinicaltrials_source", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class EndpointMetadataTests(unittest.TestCase):
    def test_registered_and_posted_outcomes_are_not_adjudicated(self):
        payload = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT05507203"},
                "outcomesModule": {"primaryOutcomes": [
                    {"measure": "Primary outcome", "timeFrame": "Week 12"}]}
            },
            "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{"type": "PRIMARY", "title": "Observed endpoint", "timeFrame": "Week 12"}, {"type": "SECONDARY", "title": "Secondary"}]}}
        }
        output = module.fetch_study(
            "NCT05507203",
            opener=lambda request, timeout: Response(json.dumps(payload).encode()))
        self.assertEqual(output["registered_primary_outcomes"][0]["measure"], "Primary outcome")
        self.assertEqual(output["posted_outcome_measures_count"], 2)
        self.assertEqual(output["posted_primary_outcome_count"], 1)
        self.assertEqual(output["posted_primary_outcomes"][0]["title"], "Observed endpoint")
        self.assertEqual(output["endpoint_review_status"], "requires_independent_review")
        self.assertFalse(output["scientifically_verified"])
        self.assertIsNone(output["prediction"])

    def test_absent_outcome_results_are_not_zero_efficacy(self):
        payload = {"protocolSection": {"identificationModule": {"nctId": "NCT05507203"}}}
        output = module.fetch_study(
            "NCT05507203",
            opener=lambda request, timeout: Response(json.dumps(payload).encode()))
        self.assertEqual(output["posted_outcome_measures_count"], 0)
        self.assertEqual(output["posted_primary_outcomes"], [])
        self.assertFalse(output["results_submitted"])
        self.assertEqual(output["endpoint_review_status"], "requires_independent_review")


if __name__ == "__main__":
    unittest.main()
