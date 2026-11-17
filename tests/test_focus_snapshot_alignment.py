import unittest
from scripts.check_focus_snapshot_alignment import compare

class SnapshotAlignmentTests(unittest.TestCase):
    def test_identifies_stale_package_without_modifying_inputs(self):
        front = {"asOf":"2026-11-16","records":[{"nct":"NCT00000001","ticker":"ABC"}]}
        back = {"asOf":"2026-11-14","records":[{"nct":"NCT00000001","ticker":"ABC"}]}
        self.assertFalse(compare(front, back)["aligned"])
        self.assertEqual(back["asOf"], "2026-11-14")

    def test_reports_changed_membership_and_fields(self):
        front = {"asOf":"new","records":[{"nct":"NCT00000001","ticker":"NEW"},
                                            {"nct":"NCT00000002","ticker":"DEF"}]}
        back = {"asOf":"old","records":[{"nct":"NCT00000001","ticker":"OLD"},
                                           {"nct":"NCT00000003","ticker":"GHI"}]}
        result = compare(front, back)
        self.assertEqual(result["changedNcts"], ["NCT00000001"])
        self.assertEqual(result["frontendOnlyNcts"], ["NCT00000002"])
        self.assertEqual(result["backendOnlyNcts"], ["NCT00000003"])

    def test_rejects_duplicate_nct(self):
        with self.assertRaises(ValueError):
            compare({"records":[{"nct":"NCT00000001"},{"nct":"NCT00000001"}]},
                    {"records":[]})
