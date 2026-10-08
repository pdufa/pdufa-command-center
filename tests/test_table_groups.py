import csv
from pathlib import Path
import unittest

import pandas as pd

from table_groups import MAX_COLUMNS, _filter_stage_rows, _stage_header_layout, apply_editor_changes, column_groups, column_topic


class ColumnGroupsTests(unittest.TestCase):
    def test_all_source_fields_remain_reachable_in_compact_panes(self):
        root = Path(__file__).resolve().parents[1]
        for path in (root / "data").glob("*.csv"):
            with path.open(newline="", encoding="utf-8") as source:
                columns = next(csv.reader(source))
            groups = column_groups(columns)
            panes = [fields for family in groups.values() for _, fields in family]
            with self.subTest(source=path.name):
                self.assertEqual(set(columns), {c for fields in panes for c in fields})
                self.assertTrue(all(len(fields) <= MAX_COLUMNS for fields in panes))
                if len(columns) > MAX_COLUMNS and "ticker" in columns:
                    self.assertTrue(all("ticker" in fields for fields in panes))

    def test_watchlist_and_program_identity_repeat_in_every_view(self):
        columns = ["Watchlist", "Ticker", "Drug", "Indication", "Current Stage", "Next Milestone", "PDUFA Date", "FDA PoA", "Financing #2 Date", "Market Cap", "Entry Gate", "Evidence Status"]
        groups = column_groups(columns)
        self.assertEqual(set(groups), {"Overview", "FDA", "Financing", "Market", "Trading"})
        self.assertTrue(all(fields[:3] == columns[:3] for panes in groups.values() for _, fields in panes))

    def test_related_topics_and_default_fda_timeline(self):
        self.assertEqual(column_topic("NDA Submission"), ("FDA", "Application & dates"))
        self.assertEqual(column_topic("Our Trade/PDUFA Score"), ("Trading", "Signals & scores"))
        self.assertEqual(column_topic("fda_statistics_gate"), ("FDA", "Statistics"))
        columns = ["Ticker", "Drug", "fda_statistics_gate", "FDA PoA", "NDA Submission", "PDUFA Date", "fda_cmc_gate", "fda_facility_gate", "fda_match_result"]
        self.assertEqual(column_groups(columns)["FDA"][0][0], "Application & dates")

    def test_small_tables_stay_one_compact_view(self):
        self.assertEqual(list(column_groups(["Field", "Value"])), ["Overview"])

    def test_pipeline_transfer_checkbox_repeats_in_every_column_tab(self):
        columns = ["Move to MASTER TABLE", "Ticker", "Drug", "Indication", "Company", "Graduation Status", "Market Cap", "Phase 2 Start", "Registered Phase", "Trial Evidence"]
        groups = column_groups(columns)
        self.assertTrue(all(fields[:3] == columns[:3] for panes in groups.values() for _, fields in panes))

    def test_stage_and_countdown_stay_immediately_next_to_ticker(self):
        columns = ["Watchlist", "Ticker", "Drug", "Indication", "STAGE", "DAYS TO PDUFA", "PDUFA Date", "FDA PoA", "Market Cap", "Trial Status", "Trial Evidence", "Cash"]
        for panes in column_groups(columns).values():
            for _, fields in panes:
                self.assertLessEqual(len(fields), MAX_COLUMNS)
                position = fields.index("Ticker")
                self.assertEqual(fields[position:position + 3], ["Ticker", "STAGE", "DAYS TO PDUFA"])


class StageMenuSortTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {"Ticker": "P2", "STAGE": "PHASE 2 ONGOING", "DAYS TO PDUFA": pd.NA, "Watchlist": False},
            {"Ticker": "FIN", "STAGE": "2ND FINANCING CLOSED · PHASE 3 COMPLETED — RESULTS REVIEW", "DAYS TO PDUFA": 30, "Watchlist": True},
            {"Ticker": "FDA", "STAGE": "PDUFA / FDA REVIEW", "DAYS TO PDUFA": 8, "Watchlist": False},
            {"Ticker": "P3", "STAGE": "PHASE 3 ONGOING", "DAYS TO PDUFA": 80, "Watchlist": True},
        ], index=[18, 4, 93, 51])
        self.options = list(self.frame["STAGE"])

    def test_check_multiple_stage_values_without_changing_row_identity(self):
        chosen = [self.options[1], self.options[3]]
        result = _filter_stage_rows(self.frame, chosen, "Workflow: early to late")
        self.assertEqual(set(result["Ticker"]), {"FIN", "P3"})
        self.assertEqual(set(result.index), {4, 51})
        self.assertEqual(result.loc[4, "Watchlist"], True)
        self.assertEqual(len(self.frame), 4)

    def test_user_selected_stage_priority(self):
        chosen = [self.options[2], self.options[3], self.options[0]]
        result = _filter_stage_rows(self.frame, chosen, "Selected stages: chosen order",
                                    priority=[self.options[3], self.options[0]])
        self.assertEqual(result["Ticker"].tolist(), ["P3", "P2", "FDA"])

    def test_workflow_order_and_countdown(self):
        workflow = _filter_stage_rows(self.frame, self.options, "Workflow: early to late")
        self.assertEqual(workflow["Ticker"].tolist(), ["P2", "P3", "FIN", "FDA"])
        countdown = _filter_stage_rows(self.frame, self.options, "Days to PDUFA: soonest first")
        self.assertEqual(countdown["Ticker"].tolist(), ["FDA", "FIN", "P3", "P2"])

    def test_clear_all_shows_no_rows_without_editing_data(self):
        empty = _filter_stage_rows(self.frame, [], "Stage: A to Z")
        self.assertTrue(empty.empty)
        self.assertEqual(len(self.frame), 4)


class StageButtonPlacementTests(unittest.TestCase):
    def test_stage_button_anchors_after_ticker_and_optional_action(self):
        plain = ["Ticker", "STAGE", "DAYS TO PDUFA", "Drug", "PDUFA Date"]
        watch = ["Watchlist", *plain, "Market Cap", "Trial Status", "Financing Status"]
        early, width, tail = _stage_header_layout(plain)
        shifted, shifted_width, shifted_tail = _stage_header_layout(watch)
        self.assertGreater(early, 0)
        self.assertGreater(width, 0)
        self.assertEqual(shifted - early, 108)
        self.assertEqual(width, shifted_width)
        self.assertGreater(tail, 0)
        self.assertGreater(shifted_tail, 0)


class EditorChangesTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {"order": 1, "task": "Check dates", "status": "ACTIVE", "notes": "Retain evidence", "source": "Source A"},
            {"order": 2, "task": "Check trials", "status": "NEXT", "notes": "Keep this note", "source": "Source B"},
        ], index=[12, 31])

    def test_secondary_tab_edit_preserves_hidden_fields_and_identity(self):
        changes = {"edited_rows": {1: {"status": "DONE", "task": "Disallowed identity edit"}}}
        edited = apply_editor_changes(self.frame, changes, {"status"})
        self.assertEqual(edited.loc[31, "status"], "DONE")
        self.assertEqual(edited.loc[31, "task"], "Check trials")
        self.assertEqual(edited.loc[31, "notes"], "Keep this note")
        self.assertEqual(list(edited.index), [12, 31])

    def test_dynamic_deletion_and_addition_retain_other_tab_data(self):
        first = apply_editor_changes(self.frame, {"edited_rows": {1: {"notes": "Edited on another tab"}}}, {"notes"})
        edited = apply_editor_changes(first, {"deleted_rows": [0], "added_rows": [{"order": 3, "task": "New task"}]}, {"order", "task"}, dynamic=True)
        self.assertEqual(len(edited), 2)
        self.assertEqual(edited.iloc[0]["notes"], "Edited on another tab")
        self.assertEqual(edited.iloc[0]["source"], "Source B")
        self.assertEqual(edited.iloc[1]["task"], "New task")
        self.assertTrue(pd.isna(edited.iloc[1]["source"]))
        self.assertEqual(list(edited.columns), list(self.frame.columns))

    def test_fixed_panes_cannot_add_or_delete_records(self):
        edited = apply_editor_changes(self.frame, {"deleted_rows": [0], "added_rows": [{"task": "New"}]}, {"notes"})
        pd.testing.assert_frame_equal(edited, self.frame)

    def test_watchlist_edit_uses_row_position_with_filtered_index(self):
        frame = pd.DataFrame({"Ticker": ["ABC", "XYZ"], "Watchlist": [False, True]}, index=[42, 91])
        edited = apply_editor_changes(frame, {"edited_rows": {0: {"Watchlist": True}, 1: {"Watchlist": False}}}, {"Watchlist"})
        self.assertEqual(edited["Watchlist"].tolist(), [True, False])
        self.assertEqual(list(edited.index), [42, 91])


if __name__ == "__main__":
    unittest.main()
