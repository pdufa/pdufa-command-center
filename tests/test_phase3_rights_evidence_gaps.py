import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_phase3_rights_evidence_gaps import build

class TrialRightsEvidenceGapTests(unittest.TestCase):
    def test_all_741_trial_rights_gaps_are_explicit(self):
        report = build()
        self.assertEqual(report["trial_count"], 741)
        self.assertEqual(report["issuer_count"], 130)
        self.assertEqual(report["exact_saved_sponsor_pointers"], 741)
        self.assertEqual(report["independently_verified_current_development_rights"], 0)
        self.assertEqual(report["rights_not_established"], 741)
        self.assertEqual(len({r["nct_id"] for r in report["trials"]}), 741)
        self.assertEqual(len({r["ticker"] for r in report["trials"]}), 130)
        self.assertIsNone(report["qualified_pipeline_count"])
        self.assertTrue(all(r["current_rights_primary_source"] is None and r["qualified_pipeline"] is None for r in report["trials"]))
    def test_all_have_research_source_and_rights_evidence_requirements(self):
        report = build()
        self.assertTrue(all(r["registry_record_url"] == "https://clinicaltrials.gov/study/" + r["nct_id"] for r in report["trials"]))
        self.assertTrue(all(r["issuer_sec_submissions_url"].startswith("https://data.sec.gov/submissions/CIK") for r in report["trials"]))
        self.assertTrue(all("CURRENT_LICENSE_OR_OWNERSHIP" in r["required_evidence"] for r in report["trials"]))
if __name__ == "__main__":
    unittest.main()
