"""Offline exact-NCT source grounding for Level 2 hypothesis worklists.

Tests do not use the internet or execute generated scientific assessments.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/level2_focus_registry_research.py"
SPEC = importlib.util.spec_from_file_location("level2_focus_registry_research", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LevelTwoRegistryResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = json.loads(
            (ROOT / "new-platform/frontend/data/p3PostDataActive.json").read_text(encoding="utf-8")
        )
        cls.scan = json.loads(
            (ROOT / "new-platform/frontend/data/focus-29-registry-source-scan-20261108.json").read_text(encoding="utf-8")
        )

    def test_all_29_exact_ncts_have_registry_grounded_fields(self):
        report = MODULE.build_source_research(self.roster, self.scan)
        self.assertEqual(report["trial_count"], 29)
        self.assertEqual(report["saved_registry_facts"], 145)
        self.assertEqual(
            {r["nct"] for r in report["records"]},
            {r["nct"] for r in self.roster["records"]},
        )
        self.assertEqual(
            [r["nct"] for r in report["records"]],
            [r["nct"] for r in self.roster["records"]],
        )
        for item in report["records"]:
            self.assertEqual(len(item["saved_registry_facts"]), 5)
            self.assertEqual(len(item["level2_research_questions"]), 5)
            self.assertIsNone(item["mechanism_of_action"])
            self.assertIsNone(item["hypothesis_adjudication"])
            self.assertIsNone(item["fda_prediction"])
            self.assertIsNone(item["approval_probability"])
            self.assertFalse(item["biological_target_validated"])
            self.assertFalse(item["phase_independently_verified"])
            self.assertEqual(item["source_documents_retrieved_in_this_run"], 0)
            for field in item["saved_registry_facts"]:
                self.assertEqual(field["source_url"], f'https://clinicaltrials.gov/study/{item["nct"]}')
                self.assertFalse(field["independently_verified"])
                self.assertEqual(field["status"], "CAPTURED_REGISTRY_FIELD_REQUIRES_PRIMARY_SOURCE_RECHECK")

    def test_five_registry_field_summaries_not_scientific_verdicts(self):
        report = MODULE.build_source_research(self.roster, self.scan)
        self.assertEqual(report["level2_scientific_assessments_completed"], 0)
        self.assertEqual(report["fda_predictions"], 0)
        self.assertFalse(report["live_registry_fetched"])
        self.assertFalse(report["production_modified"])
        self.assertEqual(report["study_records_retrieved_in_run"], 0)
        expected = set(MODULE.REQUIRED_TESTS.values())
        for item in report["records"]:
            self.assertEqual({r["field"] for r in item["saved_registry_facts"]}, expected)

    def test_mismatched_company_identity_rejected(self):
        changed = copy.deepcopy(self.scan)
        changed["rows"][0]["company"] = "Wrong sponsor identity"
        with self.assertRaises(ValueError):
            MODULE.build_source_research(self.roster, changed)

    def test_changed_or_duplicate_nct_rejected(self):
        for invalid in ("NCT00000000", "NCT١٢٣٤٥٦٧٨", "NCT1"):
            changed = copy.deepcopy(self.scan)
            changed["rows"][0]["nct"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                MODULE.build_source_research(self.roster, changed)
        duplicated = copy.deepcopy(self.scan)
        duplicated["rows"][1]["nct"] = duplicated["rows"][0]["nct"]
        with self.assertRaises(ValueError):
            MODULE.build_source_research(self.roster, duplicated)

    def test_different_or_untrusted_source_url_rejected(self):
        for source in (
            "https://clinicaltrials.gov/study/NCT00000000",
            "http://clinicaltrials.gov/study/NCT05507203",
            "https://fake.example.org/study/NCT05507203",
        ):
            changed = copy.deepcopy(self.scan)
            changed["rows"][0]["tests"][0]["sourceUrl"] = source
            with self.subTest(source=source), self.assertRaises(ValueError):
                MODULE.build_source_research(self.roster, changed)

    def test_missing_or_falsified_source_summary_rejected(self):
        for state in ("INDEPENDENT_REVIEW_REQUIRED", "SOURCE_FIELD_MISSING"):
            changed = copy.deepcopy(self.scan)
            changed["rows"][0]["tests"][4]["state"] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                MODULE.build_source_research(self.roster, changed)
        missing = copy.deepcopy(self.scan)
        missing["rows"][0]["tests"][4]["summary"] = ""
        with self.assertRaises(ValueError):
            MODULE.build_source_research(self.roster, missing)

    def test_false_scientific_verification_or_prediction_rejected(self):
        for key, value in (
            ("scientificAssessment", "VERIFIED"),
            ("prediction", "APPROVE"),
            ("certainty", "HIGH"),
        ):
            changed = copy.deepcopy(self.scan)
            changed["rows"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.build_source_research(self.roster, changed)

    def test_future_dates_or_extra_missing_trial_rejected(self):
        newer = copy.deepcopy(self.scan)
        newer["rosterAsOf"] = "2026-11-12"
        with self.assertRaises(ValueError):
            MODULE.build_source_research(self.roster, newer)
        missing = copy.deepcopy(self.scan)
        missing["rows"].pop()
        with self.assertRaises(ValueError):
            MODULE.build_source_research(self.roster, missing)


if __name__ == "__main__":
    unittest.main()
