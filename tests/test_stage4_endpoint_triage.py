import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_phase_first_triage.py"
spec = importlib.util.spec_from_file_location("stage4_phase_first_triage", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def roster_trial(n):
    return {
        "nct": f"NCT{n:08d}", "status": "retrieved",
        "phase": ["PHASE3"], "results_submitted": True,
        "registered_primary_outcomes": [{"measure": "Outcome"}],
        "posted_primary_outcomes": [{"title": "Outcome"}],
    }


class EndpointTriageTests(unittest.TestCase):
    def test_distinguishes_missing_posted_outcomes(self):
        trials = [roster_trial(i) for i in range(1, 30)]
        trials[0]["posted_primary_outcomes"] = []
        trials[1].pop("posted_primary_outcomes")
        trials[2]["registered_primary_outcomes"] = []
        report = module.triage({"trials": trials})
        self.assertEqual(report["trials"][0]["endpoint_evidence"], "posted_primary_outcome_missing")
        self.assertEqual(report["trials"][1]["endpoint_evidence"], "endpoint_metadata_unavailable")
        self.assertEqual(report["trials"][2]["endpoint_evidence"], "registered_primary_endpoint_missing")
        self.assertEqual(report["trials"][3]["endpoint_evidence"], "primary_outcome_review_required")
        self.assertTrue(all(x["verified"] is False and x["prediction"] is None for x in report["trials"]))
        self.assertEqual(report["verified_scientific_adjudications"], 0)


if __name__ == "__main__":
    unittest.main()
