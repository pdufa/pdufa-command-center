#!/usr/bin/env python3
import unittest
from phase3_sponsor_evidence import build

class SponsorEvidenceTests(unittest.TestCase):
    def test_empty_report_stays_unverified(self):
        r = build({"census_total": 741, "original_source_records": []})
        self.assertEqual(r["total"], 741)
        self.assertEqual(r["sponsor_present"], 0)
        self.assertEqual(r["commercial_rights_verified"], 0)
        self.assertIsNone(r["qualified_pipeline_total"])

    def test_extra_source_rejected(self):
        with self.assertRaises(ValueError):
            build({"census_total": 741, "original_source_records": [{"nct_id": "NCT99999999"}]})

    def test_duplicate_source_rejected(self):
        with self.assertRaises(ValueError):
            build({"census_total": 741, "original_source_records": [{"nct_id": "NCT99999999"}, {"nct_id": "NCT99999999"}]})

    def test_wrong_denominator_rejected(self):
        with self.assertRaises(ValueError):
            build({"census_total": 740, "original_source_records": []})

if __name__ == "__main__":
    unittest.main()
