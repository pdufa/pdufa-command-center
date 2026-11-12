"""Scheduled Level 2 source-research report integrity: never promote observations."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from level2_focus_registry_research import build_source_research
from windows_local_agent_focus_validation import verify_registry_research_report


class ScheduledRegistryResearchValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster_bytes = (ROOT / "new-platform/frontend/data/p3PostDataActive.json").read_bytes()
        cls.scan_bytes = (ROOT / "new-platform/frontend/data/focus-29-registry-source-scan-20261108.json").read_bytes()
        cls.report = build_source_research(
            json.loads(cls.roster_bytes), json.loads(cls.scan_bytes)
        )
        cls.report["roster_sha256"] = hashlib.sha256(cls.roster_bytes).hexdigest()
        cls.report["saved_scan_sha256"] = hashlib.sha256(cls.scan_bytes).hexdigest()
        cls.report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()

    def verify(self, report=None):
        return verify_registry_research_report(
            self.report if report is None else report,
            self.roster_bytes,
            self.scan_bytes,
        )

    def test_exact_145_source_fields_validate(self):
        self.assertTrue(self.verify())
        self.assertEqual(self.report["saved_registry_facts"], 145)
        self.assertEqual(self.report["trial_count"], 29)

    def test_false_science_or_fda_prediction_is_rejected(self):
        for key, value in (
            ("level2_scientific_assessments_completed", 29),
            ("fda_predictions", 29),
            ("live_registry_fetched", True),
            ("study_records_retrieved_in_run", 29),
            ("production_modified", True),
        ):
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report[key] = value
                self.assertFalse(self.verify(report))

    def test_changed_snapshot_or_false_digest_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["saved_scan_sha256"] = "0" * 64
        self.assertFalse(self.verify(report))
        modified_source = self.roster_bytes.replace(b"Abivax S.A.", b"Abivax Inc.", 1)
        self.assertNotEqual(modified_source, self.roster_bytes)
        self.assertFalse(
            verify_registry_research_report(
                self.report, modified_source, self.scan_bytes
            )
        )

    def test_changed_fact_or_reordered_identity_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["records"][0]["saved_registry_facts"][0]["independently_verified"] = True
        self.assertFalse(self.verify(report))
        report = copy.deepcopy(self.report)
        report["records"][0]["nct"] = "NCT00000000"
        self.assertFalse(self.verify(report))
        report = copy.deepcopy(self.report)
        report["generated_at_utc"] = "NOT_A_TIME"
        self.assertFalse(self.verify(report))


if __name__ == "__main__":
    unittest.main()
