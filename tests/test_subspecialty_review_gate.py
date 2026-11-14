"""Owner-only disease-specialist review never requires another human."""
import copy
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location(
    "review",Path(__file__).resolve().parents[1]/"scripts/medical/subspecialty_review_gate.py")
review=importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def sample():
    dimension={
        "status":"REVIEWED","clinicalFinding":"Source-dated finding",
        "limitations":"Missing safety follow-up",
        "sourceCitations":[{"sourceUrl":"https://example.org","sourceDate":"2026-01-01",
                            "locator":"page 1","claim":"Source claim"}],
        "ownerReviewStatus":"OWNER_ACCEPTED_WITH_LIMITATIONS",
    }
    return {"nct":"NCT00000001","registrySourceSha256":"abc",
            "routingStatus":"PROVISIONAL_SINGLE_SPECIALTY","specialtyCandidates":["oncology"],
            "dimensions":{key:copy.deepcopy(dimension) for key in review.DIMENSIONS}}


class SpecialistReviewGateTests(unittest.TestCase):
    def test_unassessed_shell_rejected(self):
        row=sample()
        for dimension in row["dimensions"].values():
            dimension["status"]="EVIDENCE_REQUIRED"
            dimension.pop("ownerReviewStatus")
        self.assertFalse(review.validate(row)["accepted"])

    def test_single_owner_accepts_all_eight_specialty_dimensions(self):
        report=review.validate(sample())
        self.assertTrue(report["accepted"],report["errors"])
        self.assertTrue(report["ownerOnly"])
        self.assertEqual(report["externalReviewersRequired"],0)
        self.assertEqual(report["externalSignoffsRequired"],0)
        self.assertFalse(report["scientificAccuracyVerified"])

    def test_second_person_neither_required_nor_sufficient(self):
        row=sample()
        for dimension in row["dimensions"].values():
            dimension["reviewer"]="same-owner"
            dimension["independentReview"]={"reviewer":"same-owner",
                                             "critique":"Owner challenges their conclusion"}
        self.assertTrue(review.validate(row)["accepted"])
        row["dimensions"][review.DIMENSIONS[0]].pop("ownerReviewStatus")
        self.assertIn(review.DIMENSIONS[0]+":OWNER_REVIEW_NOT_ACCEPTED",
                      review.validate(row)["errors"])

    def test_no_false_completion_and_mandatory_source_citations_remain(self):
        row=sample()
        row["dimensions"][review.DIMENSIONS[1]]["ownerReviewStatus"]="OWNER_NOT_REVIEWED"
        self.assertFalse(review.validate(row)["accepted"])
        row=sample()
        row["dimensions"][review.DIMENSIONS[0]]["sourceCitations"]=[]
        self.assertIn(review.DIMENSIONS[0]+":INVALID_CITATIONS",
                      review.validate(row)["errors"])

    def test_probability_and_timing_are_not_silently_authorized(self):
        row=sample()
        row["outcomePrediction"]="APPROVAL"
        self.assertIn("PREDICTION_NOT_PERMITTED_IN_SPECIALTY_DOSSIER",
                      review.validate(row)["errors"])


if __name__=="__main__":
    unittest.main()
