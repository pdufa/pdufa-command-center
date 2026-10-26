import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_live_registry_metadata import extract, run

class LiveRegistryMetadataTests(unittest.TestCase):
    def test_extract_registry_fields_and_exact_identity(self):
        p = {"protocolSection":{"identificationModule":{"nctId":"NCT12345678"},
             "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Example"}},
             "statusModule":{"overallStatus":"COMPLETED"},
             "designModule":{"phases":["PHASE3"]}}}
        self.assertEqual(extract("NCT12345678",p)["live_registry_lead_sponsor"],"Example")
        with self.assertRaises(ValueError):
            extract("NCT12345679",p)
    def test_all_741_failures_remain_unresolved(self):
        def fail(nct):
            raise ValueError("offline")
        report = run(fail)
        self.assertEqual(report["historical_trial_count"],741)
        self.assertEqual(report["registry_metadata_unresolved"],741)
        self.assertEqual(report["registry_metadata_retrieved"],0)
        self.assertEqual(report["current_legal_rights_verified"],0)
        self.assertEqual(report["fda_pdufa_verified"],0)
        self.assertIsNone(report["qualified_pipeline_count"])
if __name__ == "__main__":
    unittest.main()
