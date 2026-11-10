import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("gaps", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_evidence_gap_report.py")
gaps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gaps)

class GapReportTests(unittest.TestCase):
    def test_all_29_unreviewed_and_missingness_counted(self):
        dossiers = [{"nct": f"NCT{i:08d}", "dimensions": {
            f"dimension_{j}": {"registryEvidenceLeads": [{"sourceUrl": "https://example.org"}] if j == 0 else []}
            for j in range(8)}} for i in range(29)]
        result = gaps.summarize({"status": "UNREVIEWED_REGISTRY_EVIDENCE_LEADS", "dossiers": dossiers})
        self.assertEqual(result["dimensionsWithRegistryLeads"], 29)
        self.assertEqual(result["dimensionsNeedingAdditionalEvidence"], 203)
        self.assertEqual(result["scientificallyAdjudicated"], 0)

    def test_reject_incomplete_population(self):
        with self.assertRaises(ValueError):
            gaps.summarize({"status": "UNREVIEWED_REGISTRY_EVIDENCE_LEADS", "dossiers": []})

if __name__ == "__main__":
    unittest.main()
