import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_retrieval_coverage_audit.py"
spec = importlib.util.spec_from_file_location("stage4_retrieval_coverage_audit", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixtures():
    ids = [f"NCT{i:08d}" for i in range(1, 30)]
    roster = {"records": [{"nct": nct} for nct in ids]}
    registry = {"scientific_adjudications": 0, "trials": [
        {"nct": nct, "status": "retrieved", "prediction": None} for nct in ids]}
    triage = {"verified_scientific_adjudications": 0, "trials": [
        {"nct": nct, "readiness": "phase_appropriate_results_present",
         "endpoint_evidence": "primary_outcome_review_required",
         "verified": False, "prediction": None} for nct in ids]}
    return registry, triage, roster


class CoverageAuditTests(unittest.TestCase):
    def test_counts_endpoint_evidence_without_verification(self):
        a, b, roster = fixtures()
        b["trials"][0]["endpoint_evidence"] = "posted_primary_outcome_missing"
        b["trials"][1]["endpoint_evidence"] = "registered_primary_endpoint_missing"
        a["trials"][2]["status"] = "retrieval_failed"
        b["trials"][2] = {"nct": a["trials"][2]["nct"], "readiness": "retrieval_failed",
                          "verified": False, "prediction": None}
        report = module.audit(a, b, roster)
        self.assertEqual(report["retrieved"], 28)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["endpoint_evidence_counts"]["primary_outcome_review_required"], 25)
        self.assertEqual(report["endpoint_evidence_counts"]["posted_primary_outcome_missing"], 1)
        self.assertEqual(report["prediction_count"], 0)
        self.assertFalse(report["scientific_verification_complete"])

    def test_missing_endpoint_classification_fails_closed(self):
        a, b, roster = fixtures()
        del b["trials"][0]["endpoint_evidence"]
        with self.assertRaises(ValueError):
            module.audit(a, b, roster)

    def test_unverified_prediction_is_rejected(self):
        a, b, roster = fixtures()
        b["trials"][0]["prediction"] = {"approval_probability": 0.99}
        with self.assertRaises(ValueError):
            module.audit(a, b, roster)

    def test_roster_order_mismatch_is_rejected(self):
        a, b, roster = fixtures()
        b["trials"][0], b["trials"][1] = b["trials"][1], b["trials"][0]
        with self.assertRaises(ValueError):
            module.audit(a, b, roster)


if __name__ == "__main__":
    unittest.main()
