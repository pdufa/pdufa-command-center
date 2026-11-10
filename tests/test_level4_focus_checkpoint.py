"""Offline regression tests for unattended FOCUS checkpoints."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

base = Path(__file__).resolve().parents[1] / "scripts" / "medical"
import sys
sys.path.insert(0, str(base))
spec = importlib.util.spec_from_file_location("level4_focus_checkpoint", base / "level4_focus_checkpoint.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FocusCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.roster = {"asOf": "2026-11-10", "records": [{"nct": f"NCT{i:08d}"} for i in range(1,30)]}

    def test_checkpoint_extracts_without_predictions(self):
        def fake(nct):
            return json.dumps({"protocolSection": {"identificationModule": {"nctId": nct}}}).encode()
        with tempfile.TemporaryDirectory() as folder, patch.object(mod.time, "sleep"):
            report = mod.run(self.roster, Path(folder)/"checkpoint.json", limit=2, fetch=fake)
            self.assertEqual(report["captured"], 2)
            self.assertEqual(report["scientificallyReviewed"], 0)
            self.assertIsNone(report["results"]["NCT00000001"]["evidence"]["fdaPrediction"])

    def test_mismatched_packet_is_retry_not_evidence(self):
        bad = lambda nct: json.dumps({"protocolSection": {"identificationModule": {"nctId": "NCT99999999"}}}).encode()
        with tempfile.TemporaryDirectory() as folder, patch.object(mod.time, "sleep"):
            report = mod.run(self.roster, Path(folder)/"checkpoint.json", limit=1, fetch=bad)
            self.assertEqual(report["retryRequired"], 1)

    def test_roster_count_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                mod.run({"records": self.roster["records"][:28]}, Path(folder)/"checkpoint.json", fetch=lambda _: b"{}")

if __name__ == "__main__":
    unittest.main()
