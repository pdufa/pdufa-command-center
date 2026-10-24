import unittest
from scientific_assessment import DOMAINS, assess

class ScientificAssessmentTests(unittest.TestCase):
    def test_empty_evidence_never_scores(self):
        result = assess({})
        self.assertIsNone(result["overall_score"])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(len(result["domains"]), 6)

    def test_partial_evidence_does_not_score(self):
        result = assess({"efficacy.primary_endpoint": {"status": "verified", "value": 90, "source_url": "https://clinicaltrials.gov/study/NCT00000000"}})
        self.assertIsNone(result["domains"]["efficacy"]["score"])

    def test_complete_verified_evidence_scores(self):
        evidence = {f"{domain}.{field}": {"status": "verified", "value": 75, "source_url": "https://example.org/evidence"}
                    for domain, fields in DOMAINS.items() for field in fields}
        result = assess(evidence)
        self.assertEqual(result["overall_score"], 75)
        self.assertEqual(result["status"], "complete")

    def test_unverified_and_out_of_range_never_score(self):
        evidence = {f"{domain}.{field}": {"status": "verified", "value": 101, "source_url": "https://example.org"}
                    for domain, fields in DOMAINS.items() for field in fields}
        self.assertIsNone(assess(evidence)["overall_score"])

if __name__ == "__main__":
    unittest.main()
