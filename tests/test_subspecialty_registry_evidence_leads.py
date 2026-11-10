import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("leads", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_registry_evidence_leads.py")
leads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(leads)

class EvidenceLeadTests(unittest.TestCase):
    def fixtures(self):
        dossiers = [{"nct": f"NCT{i:08d}", "dimensions": {k: {"status": "EVIDENCE_REQUIRED"} for k in leads.FIELD_DIMENSIONS}} for i in range(29)]
        checkpoint = {"results": {"NCT00000000": {"status": "CAPTURED_UNREVIEWED", "evidence": {
            "nct": "NCT00000000", "source": "https://clinicaltrials.gov/study/NCT00000000", "sha256": "abc",
            "fields": {"primaryEndpoints": {"status": "CAPTURED_UNREVIEWED", "locator": "protocolSection.outcomesModule.primaryOutcomes", "value": ["test"]}}}}}}
        return {"status": "DOSSIER_SHELLS_ONLY", "dossiers": dossiers}, checkpoint

    def test_leads_do_not_become_findings(self):
        dossier, checkpoint = self.fixtures()
        result = leads.enrich(dossier, checkpoint)
        self.assertEqual(result["registryEvidenceLeadCount"], 2)
        self.assertEqual(result["scientificallyAdjudicated"], 0)
        self.assertEqual(result["dossiers"][0]["dimensions"]["endpoint_validity_and_clinical_meaning"]["status"], "EVIDENCE_REQUIRED")

    def test_cross_trial_evidence_rejected(self):
        dossier, checkpoint = self.fixtures()
        checkpoint["results"]["NCT00000000"]["evidence"]["nct"] = "NCT99999999"
        with self.assertRaises(ValueError):
            leads.enrich(dossier, checkpoint)

if __name__ == "__main__":
    unittest.main()
