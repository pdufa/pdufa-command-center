#!/usr/bin/env python3
"""Validate SVA exception is evidence-only and never silently promoted."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SvaTradingHaltEvidenceTests(unittest.TestCase):
    def test_exception_is_explicit_and_not_pipeline_qualified(self):
        x = json.loads((ROOT / "data/research_sva_trading_halt_2026-10-26.json").read_text())
        self.assertEqual(x["issuer"], "SVA")
        self.assertEqual(x["status"], "TRADING_HALTED_MARKET_CAP_UNRESOLVED")
        self.assertEqual(x["marketCapGate"], "UNRESOLVED")
        self.assertTrue(x["doNotPromote"])
        self.assertIsNone(x["qualifiedPipeline"])
        self.assertGreaterEqual(len(x["sourceEvidence"]), 2)
        self.assertTrue(all(s["url"].startswith("https://") for s in x["sourceEvidence"]))

if __name__ == "__main__":
    unittest.main()
