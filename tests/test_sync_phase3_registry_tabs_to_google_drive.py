"""Fail-closed source safety checks for the two Google Drive Phase 3 tabs."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts/sync_phase3_registry_tabs_to_google_drive.py"
spec = importlib.util.spec_from_file_location("google_phase3_backup", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(count=2, positive=1):
    entries = []
    for i in range(count):
        posted = i < positive
        entries.append({
            "nctId": f"NCT{i+1:08d}", "ticker": "TEST",
            "company": "Research issuer", "registryStatus": "COMPLETED",
            "resultsCount": 1 if posted else 0,
            "resultsFirstPostedDate": "2026-10-01" if posted else "",
        })
    return {
        "schemaVersion": 2,
        "measure": module.MEASURE,
        "sourceKind": "OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT",
        "sourceFile": "data/phase3_all_years_300m_10b_trials.csv",
        "snapshotDate": "2026-10-25",
        "sourceAsOf": "2026-10-25T01:00:00+00:00",
        "total": count,
        "noResultsPosted": count-positive,
        "resultsPosted": positive,
        "records": entries,
    }


class BackupBeforePastTests(unittest.TestCase):
    def test_before_past_counts_exact_ncts_and_caution(self):
        source = fixture(6, 2)
        tabs = module.prepare(source, min_trials=6)
        self.assertEqual(len(tabs["Phase 3 Before"]), 7)
        self.assertEqual(len(tabs["Phase 3 Past"]), 5)
        self.assertEqual(tabs["Phase 3 Before"][0][1], "4 trials")
        self.assertEqual(tabs["Phase 3 Past"][0][1], "2 trials")
        self.assertEqual(tabs["Phase 3 Before"][3][4], "NO")
        self.assertEqual(tabs["Phase 3 Past"][3][4], "YES")
        self.assertIn("company's public Phase 3 announcement", tabs["Phase 3 Before"][1][0])
        distinct = [row[1] for values in tabs.values() for row in values[3:]]
        self.assertEqual(len(distinct), len(set(distinct)))

    def test_duplicate_nct_fails(self):
        source = fixture(2, 1)
        source["records"][1]["nctId"] = source["records"][0]["nctId"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            module.prepare(source, min_trials=2)

    def test_wrong_results_date_fails(self):
        source = fixture(2, 1)
        source["records"][0]["resultsFirstPostedDate"] = ""
        with self.assertRaises(ValueError):
            module.prepare(source, min_trials=2)

    def test_wrong_counts_fail(self):
        source = fixture(2, 1)
        source["noResultsPosted"] = 2
        with self.assertRaises(ValueError):
            module.prepare(source, min_trials=2)

    def test_unverified_source_classification_fails(self):
        source = fixture(2, 1)
        source["measure"] = "ISSUER_PUBLIC_READOUT"
        with self.assertRaises(ValueError):
            module.prepare(source, min_trials=2)

    def test_repository_live_source_preflight(self):
        source = json.loads(module.SOURCE.read_text(encoding="utf-8"))
        tabs = module.prepare(source)
        n = len(tabs["Phase 3 Before"]) + len(tabs["Phase 3 Past"]) - 6
        self.assertEqual(n, source["total"])
        self.assertEqual(len(tabs["Phase 3 Before"])-3, source["noResultsPosted"])
        self.assertEqual(len(tabs["Phase 3 Past"])-3, source["resultsPosted"])


if __name__ == "__main__":
    unittest.main()
