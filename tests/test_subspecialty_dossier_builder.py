import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("dossier", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_dossier_builder.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DossierBuilderTests(unittest.TestCase):
    def matrix(self):
        return {"status": "EVIDENCE_READINESS_ONLY", "trials": [
            {"nct": f"NCT{i:08d}", "source": "https://clinicaltrials.gov/study/NCT00000001",
             "subspecialty": {"specialtyCandidates": ["oncology"], "registryConditions": ["Melanoma"],
                              "sourceSha256": "abc", "routingStatus": "PROVISIONAL_SINGLE_SPECIALTY"}}
            for i in range(29)]}

    def test_all_dossiers_are_unreviewed(self):
        result = module.build(self.matrix())
        self.assertEqual(result["trialCount"], 29)
        self.assertEqual(result["scientificallyAdjudicated"], 0)
        self.assertEqual(result["ownerReviewedDossiers"], 0)
        self.assertEqual(result["externalReviewerRequirements"], 0)
        for dossier in result["dossiers"]:
            self.assertEqual(dossier["dossierStatus"], "OWNER_NOT_REVIEWED")
            for dimension in dossier["dimensions"].values():
                self.assertEqual(dimension["ownerReviewStatus"], "OWNER_NOT_REVIEWED")
                self.assertFalse(dimension["externalReviewerRequired"])
                self.assertNotIn("independentReview", dimension)
        self.assertTrue(all(len(d["dimensions"]) == 8 for d in result["dossiers"]))
        self.assertTrue(all(d["outcomePrediction"] is None for d in result["dossiers"]))

    def test_reject_missing_source(self):
        m = self.matrix()
        m["trials"][0]["subspecialty"]["sourceSha256"] = None
        with self.assertRaises(ValueError):
            module.build(m)

    def test_reject_duplicate_nct(self):
        m = self.matrix()
        m["trials"][1]["nct"] = m["trials"][0]["nct"]
        with self.assertRaises(ValueError):
            module.build(m)

if __name__ == "__main__":
    unittest.main()
