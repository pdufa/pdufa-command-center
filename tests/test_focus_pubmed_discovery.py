import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pubmed", Path(__file__).resolve().parents[1] / "scripts/medical/focus_pubmed_discovery.py")
pubmed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pubmed)

class PubMedDiscoveryTests(unittest.TestCase):
    def roster(self):
        return {"records": [{"nct": f"NCT{i:08d}"} for i in range(29)]}

    def test_all_29_unreviewed(self):
        def fake(nct):
            return {"nct": nct, "publicationLeads": [{"pmid": "123", "reviewStatus": "UNREVIEWED"}]}
        result = pubmed.build(self.roster(), fake, sleep=lambda _: None)
        self.assertEqual(result["publicationLeadsFound"], 29)
        self.assertEqual(result["scientificAssessmentsCompleted"], 0)

    def test_reject_invalid_roster(self):
        roster = self.roster()
        roster["records"][0]["nct"] = "NCT-invalid"
        with self.assertRaises(ValueError):
            pubmed.build(roster, lambda nct: {})

    def test_retry_single_failure(self):
        def fake(nct):
            if nct == "NCT00000000":
                raise TimeoutError()
            return {"nct": nct, "publicationLeads": []}
        result = pubmed.build(self.roster(), fake)
        self.assertEqual(result["rows"][0]["status"], "RETRY_REQUIRED")
        self.assertEqual(result["queriesFailed"], 1)
        self.assertEqual(result["status"], "PARTIAL_RETRY_REQUIRED")
        self.assertEqual(len(result["rows"]), 29)

if __name__ == "__main__":
    unittest.main()
