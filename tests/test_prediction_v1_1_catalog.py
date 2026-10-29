"""Tests for the v1.1 catalog contract and canonical S01-S40 references."""
import json
import unittest
from pathlib import Path
from research.prediction_v1_1_catalog_validator import validate_catalog, CATALOG

class V11CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(Path(CATALOG).read_text(encoding="utf-8"))

    def test_current_draft_is_structurally_valid(self):
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_unknown_question_is_rejected(self):
        self.catalog["fields"][0]["assessment_ids"] = ["Q11"]
        self.assertTrue(any("unknown canonical assessment ID" in e for e in validate_catalog(self.catalog)))

    def test_duplicate_field_id_is_rejected(self):
        self.catalog["fields"].append(dict(self.catalog["fields"][0]))
        self.assertTrue(any("duplicate ID" in e for e in validate_catalog(self.catalog)))

    def test_missing_provenance_is_rejected(self):
        self.catalog["fields"][0]["source"] = ""
        self.assertTrue(any("empty source" in e for e in validate_catalog(self.catalog)))

    def test_unvalidated_status_must_remain_explicit(self):
        self.catalog["status"] = "COMPLETE"
        self.assertTrue(any("unvalidated" in e for e in validate_catalog(self.catalog)))

if __name__ == "__main__":
    unittest.main()
