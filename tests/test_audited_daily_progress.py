import unittest
from scripts.audited_daily_progress import compare

URL = "https://example.org/evidence"
def snap(day, science=None, outcome=None, main=None):
    return {"as_of": day, "systems": {"SCIENCE": science, "OUTCOME": outcome, "MAIN": main}}
def row(done, total, scope="fixed"):
    return {"completed": done, "total": total, "scope": scope, "evidence_uri": URL}

class DailyProgressTests(unittest.TestCase):
    def test_comparable_progress(self):
        report = compare(snap("2026-10-25", row(2, 10)), snap("2026-10-26", row(3, 10)))
        self.assertEqual(report["systems"]["SCIENCE"]["change_pp"], 10)
        self.assertIsNone(report["systems"]["OUTCOME"]["percent"])

    def test_denominator_change_not_misrepresented(self):
        report = compare(snap("2026-10-25", row(2, 10)), snap("2026-10-26", row(3, 20)))
        self.assertEqual(report["systems"]["SCIENCE"]["status"], "BASELINE_ONLY")
        self.assertIsNone(report["systems"]["SCIENCE"]["change_pp"])

    def test_scope_change_not_misrepresented(self):
        report = compare(snap("2026-10-25", row(2, 10, "pilot")), snap("2026-10-26", row(3, 10, "all")))
        self.assertIsNone(report["systems"]["SCIENCE"]["change_pp"])

    def test_invalid_values_rejected(self):
        for invalid in (row(11, 10), row(-1, 10), row(True, 10), row(1, 0)):
            with self.assertRaises(ValueError):
                compare(snap("2026-10-25"), snap("2026-10-26", invalid))

    def test_no_previous_baseline(self):
        report = compare(snap("2026-10-25"), snap("2026-10-26", row(7, 12)))
        self.assertEqual(report["systems"]["SCIENCE"]["percent"], 58.33)
        self.assertIsNone(report["systems"]["SCIENCE"]["change_pp"])

    def test_sparse_dates_do_not_become_a_daily_change(self):
        report = compare(snap("2026-10-19", main=row(1, 31)), snap("2026-10-26", main=row(2, 31)))
        self.assertEqual(report["systems"]["MAIN"]["status"], "BASELINE_ONLY")
        self.assertIsNone(report["systems"]["MAIN"]["change_pp"])

    def test_noncanonical_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            compare(snap("20261025"), snap("2026-10-26", main=row(1, 31)))

if __name__ == "__main__":
    unittest.main()
