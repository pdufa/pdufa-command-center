import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("sync", Path(__file__).resolve().parents[1] / "scripts/sync_pipeline_research.py")
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

class SyncTests(unittest.TestCase):
    def test_manual_notes_formulas_and_changed_values_are_preserved(self):
        for cell in ({"userEnteredValue": {"formulaValue": "=TODAY()"}},
                     {"userEnteredValue": {"stringValue": "reviewed"}},
                     {"note": "Clinician review"}):
            before = copy.deepcopy(cell)
            self.assertIsNone(sync.owned_change(cell, "new", "record"))
            self.assertEqual(cell, before)

    def test_owned_upsert_is_idempotent_and_respects_human_edit(self):
        first = sync.owned_change({}, "original", "record")
        self.assertIsNone(sync.owned_change(first, "original", "record"))
        self.assertIsNotNone(sync.owned_change(first, "new version", "record"))
        first["userEnteredValue"] = {"stringValue": "human correction"}
        self.assertIsNone(sync.owned_change(first, "new version", "record"))

    def test_dropdown_values_and_real_zero_remain_distinct_from_missing(self):
        cell = {"dataValidation": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": "Yes"}]}}}
        self.assertIsNone(sync.owned_change(cell, "No", "record"))
        self.assertEqual(sync.owned_change({}, 0, "record")["userEnteredValue"], {"numberValue": 0})

    def test_never_reuses_partial_manual_row_or_erases_unrelated_cells(self):
        grid = [{} for _ in range(6)]
        grid[4] = {"values": [{}, {"userEnteredValue": {"stringValue": "manual issuer pending NCT"}}]}
        records = [{"nctId": "NCT00116805", "recordId": "one"}]
        requests, writes = sync.plan_cells(7, grid, records, lambda r: [r["nctId"], "automated"])
        self.assertEqual([w[0] for w in writes], [5, 5])
        self.assertTrue(all("updateCells" in r for r in requests))
        self.assertTrue(all(r["updateCells"]["fields"] == "userEnteredValue,note" for r in requests))

    def test_duplicate_sheet_and_incomplete_source_fail_closed(self):
        grid = [{}]*4 + [{"values": [{"userEnteredValue": {"stringValue": "NCT00116805"}}]}]*2
        with self.assertRaises(ValueError):
            sync.plan_cells(7, grid, [], lambda r: [])
        with self.assertRaises(ValueError):
            sync.validate_pages([])

if __name__ == "__main__": unittest.main()
