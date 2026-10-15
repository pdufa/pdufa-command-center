"""Reconciliation contract: one SEC/FDA baseline row per filtered Pipeline record."""
import unittest
from datetime import date

import pandas as pd

from pipeline_filings_alignment import (
    align_baseline, pipeline_scope, reconciliation_counts,
    candidate_events_outside_pipeline, scope_evidence_tables, scope_research_queue,
)


class PipelineFilingsAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.records = pd.DataFrame([
            {"record_id": "TRIAL|NCT12345678", "record_type": "Registered trial",
             "nct_id": "NCT12345678", "ticker": "ABC", "drug": "Drug A",
             "current_stage": "Phase 3", "source_url": "https://trial.example",
             "pdufa_date": ""},
            {"record_id": "APPLICATION|ABC|DRUG_A_20261120",
             "record_type": "Regulatory program / event", "nct_id": "",
             "ticker": "ABC", "drug": "Drug A", "current_stage": "PDUFA Decision",
             "pdufa_date": "2026-11-20"},
            {"record_id": "TRIAL|NCT87654321", "record_type": "Registered trial",
             "nct_id": "NCT87654321", "ticker": "XYZ", "drug": "Drug B",
             "current_stage": "Phase 2", "pdufa_date": ""},
        ])
        self.candidates = [{
            "Ticker": "ABC", "Trial / event": "ABC|DRUG_A_20261120",
            "Drug": "Drug A", "Agency claim": "PDUFA_TARGET",
            "Agency verification": "VERIFIED",
            "Agency source": "https://fda.example",
            "Research gaps": "TWO_FINANCING_DOCUMENTS",
        }]

    def test_all_pipeline_records_reconcile_even_when_candidate_list_is_small(self):
        filtered, counts = pipeline_scope(self.records, {}, date(2026, 10, 15))
        self.assertEqual(counts["universe_total"], 3)
        self.assertEqual(counts["chart_total"], 3)
        self.assertEqual(counts["display_total"], 0)
        for agency in ("SEC", "FDA"):
            rows = align_baseline(filtered.to_dict("records"), self.candidates)
            self.assertEqual(len(rows), counts["chart_total"])
            self.assertEqual([r["Pipeline ID"] for r in rows],
                             list(self.records["record_id"]))
            self.assertEqual(reconciliation_counts(rows), {"matched": 1, "unassessed": 2})
            registered = rows[0]
            self.assertEqual(registered["Agency verification"], "NOT_CHECKED")
            self.assertEqual(registered["Agency source"], "")
            self.assertEqual(registered["Trial NCT"], "NCT12345678")
            self.assertNotEqual(registered["Agency claim"], "PDUFA_TARGET")
            application = rows[1]
            self.assertEqual(application["Agency verification"], "VERIFIED")
            self.assertEqual(application["Agency source"], "https://fda.example")

    def test_chart_filters_match_pipeline_when_show_is_not_pressed(self):
        state = {"pipeline_stages_v9": ["Phase 3"], "pipeline_dates_v9": [],
                 "pipeline_query_v9": ""}
        filtered, counts = pipeline_scope(self.records, state, date(2026, 10, 15))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(counts["chart_total"], 1)
        self.assertEqual(counts["display_total"], 0)
        self.assertEqual(len(align_baseline(filtered.to_dict("records"), self.candidates)), 1)

    def test_applied_pipeline_filters_sync_display_and_both_baselines(self):
        state = {
            "pipeline_stages_v9": ["PDUFA Decision"],
            "pipeline_dates_v9": ["31–60 DAYS"],
            "pipeline_query_v9": "abc",
            "pipeline_sort_v9": "Ticker A–Z",
        }
        state["pipeline_applied_v9"] = (
            ("PDUFA Decision",), ("31–60 DAYS",), "abc", "Ticker A–Z"
        )
        filtered, counts = pipeline_scope(self.records, state, date(2026, 10, 15))
        self.assertEqual(counts["chart_total"], 1)
        self.assertEqual(counts["display_total"], 1)
        self.assertEqual(align_baseline(filtered.to_dict("records"), self.candidates)[0]
                         ["Pipeline ID"], "APPLICATION|ABC|DRUG_A_20261120")

    def test_outside_pipeline_candidates_are_flagged_but_filtered_candidates_are_not(self):
        selected, _ = pipeline_scope(
            self.records, {"pipeline_stages_v9": ["Phase 3"]}, date(2026, 10, 15)
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(candidate_events_outside_pipeline(
            self.records.to_dict("records"), self.candidates), [])
        outside = self.candidates + [
            {"Ticker": "GHI", "Trial / event": "GHI|UNLINKED_20261121",
             "Agency claim": "PDUFA_TARGET", "Agency verification": "REVIEW_REQUIRED"}
        ]
        orphaned = candidate_events_outside_pipeline(
            self.records.to_dict("records"), outside
        )
        self.assertEqual(len(orphaned), 1)
        self.assertEqual(orphaned[0]["Candidate event"], "GHI|UNLINKED_20261121")

    def test_agency_evidence_obeys_pipeline_selected_scope(self):
        # The Phase 3 trial shares ABC with an application but cannot inherit
        # an FDA claim or extension by ticker.
        stage, _ = pipeline_scope(
            self.records,
            {"pipeline_stages_v9": ["Phase 3"]}, date(2026, 10, 15)
        )
        only_trial = stage.to_dict("records")
        source_rows = {
            "SEC Base": [{"Ticker": "ABC", "Form": "10-K"},
                         {"Ticker": "OUTSIDE", "Form": "8-K"}],
            "SEC Amendments": [{"Ticker": "ABC", "Form": "10-Q/A"}],
            "FDA Base": [{"Ticker": "ABC", "Trial / event": "ABC|DRUG_A_20261120"}],
            "FDA Amendments": [{"Ticker": "ABC", "Trial / event": "ABC|DRUG_A_20261120"}],
        }
        results = scope_evidence_tables(source_rows, only_trial)
        self.assertEqual(len(results["SEC Base"]), 1)
        self.assertIn("issuer", results["SEC Base"][0]["Scope"])
        self.assertEqual(len(results["FDA Base"]), 0)
        self.assertEqual(len(results["FDA Amendments"]), 0)
        queue = [{"category": "FDA", "event_key": "ABC|DRUG_A_20261120", "ticker": "ABC"},
                 {"category": "SEC", "event_key": "REGISTRY:ABC", "ticker": "ABC"},
                 {"category": "FDA", "event_key": "OTHER|DRUG", "ticker": "ABC"}]
        scoped = scope_research_queue(queue, only_trial)
        self.assertEqual(len(scoped), 1)
        self.assertEqual(scoped[0]["event_key"], "REGISTRY:ABC")

    def test_duplicate_or_missing_pipeline_ids_are_never_silently_dropped(self):
        duplicates = [self.records.iloc[0].to_dict()] * 2
        with self.assertRaises(ValueError):
            align_baseline(duplicates, self.candidates)
        with self.assertRaises(ValueError):
            align_baseline([{"record_id": ""}], self.candidates)


if __name__ == "__main__":
    unittest.main()
