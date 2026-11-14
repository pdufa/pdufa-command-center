"""Source extraction tests: no cross-trial evidence or unreviewed conclusions."""
import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/medical/level4_registry_extraction.py"
spec = importlib.util.spec_from_file_location("level4_registry_extraction", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RegistryExtractionTests(unittest.TestCase):
    def test_fields_have_provenance_and_are_unreviewed(self):
        packet = {"protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "designModule": {"phases": ["PHASE3"]},
            "statusModule": {"overallStatus": "RECRUITING"},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Endpoint"}]}
        }}
        raw = json.dumps(packet).encode()
        result = mod.extract(packet, "NCT00000001", raw)
        self.assertEqual(result["fields"]["phase"]["value"], ["PHASE3"])
        self.assertEqual(result["fields"]["primaryEndpoints"]["status"], "CAPTURED_UNREVIEWED")
        self.assertEqual(result["fields"]["studyOverallStatus"]["value"], "RECRUITING")
        self.assertEqual(result["fields"]["eligibility"]["status"], "NOT_IN_SOURCE")
        self.assertEqual(len(result["sha256"]), 64)
        self.assertIsNone(result["fdaPrediction"])

    def test_cross_trial_packet_is_rejected(self):
        packet = {"protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}}
        with self.assertRaises(ValueError):
            mod.extract(packet, "NCT00000001", b"{}")

    def test_missing_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.extract({}, "NCT00000001", b"{}")

if __name__ == "__main__":
    unittest.main()
