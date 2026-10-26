import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_qualification_ledger import GATES
from phase3_sponsor_rights_triage import build_queue

class SponsorRightsTriageTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "records": [
            {"nct_id": f"NCT{i:08d}", "ticker": "TEST", "company": "Test Inc",
             "gates": {g: "PASS" if g == "registry_identity" else "REVIEW" for g in GATES}}
            for i in range(1, 742)]}
        self.registry = {"census_total": 741, "source_errors": [], "original_source_records": [
            {"nct_id": f"NCT{i:08d}", "census_ticker": "TEST", "census_company": "Test Inc",
             "source": f"https://clinicaltrials.gov/api/v2/studies/NCT{i:08d}",
             "currently_registered_lead_sponsor": "Sponsor",
             "source_sha256": "a" * 64, "fetched_at_utc": "2026-10-26T00:00:00Z"}
            for i in range(1, 742)]}
    def test_full_queue_never_confirms_rights(self):
        result = build_queue(self.ledger, self.registry)
        self.assertEqual((result["review_required"], result["total"]), (741, 741))
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertTrue(all(not x["commercial_rights_verified"] for x in result["items"]))
    def test_missing_source_fails_closed(self):
        self.registry["original_source_records"].pop()
        with self.assertRaises(ValueError):
            build_queue(self.ledger, self.registry)
    def test_ticker_mismatch_fails_closed(self):
        self.registry["original_source_records"][0]["census_ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            build_queue(self.ledger, self.registry)
    def test_prequalified_rights_fails_closed(self):
        self.ledger["records"][0]["gates"]["current_commercial_rights"] = "PASS"
        with self.assertRaises(ValueError):
            build_queue(self.ledger, self.registry)
if __name__ == "__main__":
    unittest.main()
