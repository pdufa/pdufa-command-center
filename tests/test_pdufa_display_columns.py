"""Four PDUFA subtab presentation and financing identity regression checks."""
from supported_dashboard_checks import run_frontend_contract
import csv
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta

import pandas as pd

from pdufa_date_gradient import date_color, segment, COUNTDOWN_BANDS
from pdufa_table_headers import HELP_ICON, header_config, column_width_for, style_countdown_cells
from pdufa_display_columns import (
    FRONT, DISPLAY_ORDER_OPTIONS, enrich_exact_trials, finance_style,
    prepare_pdufa_grid, sort_pdufa_grid, sort_pdufa_rows,
    align_pdufa_finance_columns,
)


class PdufaGridTests(unittest.TestCase):
    def test_four_color_countdown_boundaries_are_exact(self):
        examples = [
            (180, "90+ DAYS", "#166534"),
            (91, "90+ DAYS", "#166534"),
            (90, "90–60 DAYS", "#86efac"),
            (60, "90–60 DAYS", "#86efac"),
            (59, "59–30 DAYS", "#fb923c"),
            (30, "59–30 DAYS", "#fb923c"),
            (29, "29–0 DAYS", "#f87171"),
            (0, "29–0 DAYS", "#f87171"),
        ]
        self.assertEqual([b[0] for b in COUNTDOWN_BANDS],
                         ["+90", "90–60", "59–30", "29–0"])
        for days, label, background in examples:
            with self.subTest(days=days):
                self.assertEqual(segment(days), label)
                self.assertIn(background, date_color(days))
        self.assertEqual(segment(-1), "PAST DUE")
        self.assertIn("#e5e7eb", date_color(-1))
        self.assertEqual(segment(pd.NA), "DATE UNKNOWN")
        self.assertIn("#e5e7eb", date_color(pd.NA))

    def test_all_countdown_header_aliases_use_one_compact_title(self):
        for name in ("Days to PDUFA", "DAYS TO PDUFA",
                     "days_to_pdufa", "Days Left"):
            with self.subTest(name=name):
                sample = pd.DataFrame({name: [90], "Ticker": ["XYZ"]})
                header = header_config(sample)[name]
                self.assertEqual(header["label"], f"Days to PDUFA {HELP_ICON}")
                self.assertFalse(header["label"].startswith(HELP_ICON))
                self.assertNotIn("\\n", header["label"])
                self.assertGreater(header["width"], 100)
                for band in ("+90", "90–60", "59–30", "29–0"):
                    self.assertNotIn(band, header["label"])
                self.assertIn("past", header["help"].lower())

    def test_circled_question_mark_follows_each_header_inline(self):
        # The shared header builder is used by all three dashboard tables:
        # #2 PIPELINE, #3 PRE3 and #4 POST3.
        for title in ("Ticker", "Drug", "Indication", "Score /100",
                      "PDUFA Date", "Days to PDUFA", "F",
                      "Cash Runway (months)"):
            with self.subTest(title=title):
                sample = pd.DataFrame({title: ["VALUE"]})
                entry = header_config(sample)[title]
                self.assertEqual(entry["label"], f"{title} {HELP_ICON}")
                self.assertEqual(entry["label"].count(HELP_ICON), 1)
                self.assertFalse(entry["label"].startswith(HELP_ICON))
                self.assertTrue(entry["help"])
        configured = header_config(
            pd.DataFrame({"Ticker": ["XYZ"]}),
            {"Ticker": {"label": f"Symbol {HELP_ICON}", "help": "Issuer ID"}},
        )
        self.assertEqual(configured["Ticker"]["label"], f"Symbol {HELP_ICON}")
        self.assertEqual(configured["Ticker"]["help"], "Issuer ID")

    def test_unified_panels_share_right_side_help_headers(self):
        source = (Path(__file__).resolve().parents[1]
                  / "unified_clinical_trading.py").read_text(encoding="utf-8")
        for name, label in (
            ("overview_pipeline_panel", "1 — PIPELINE"),
            ("overview_gemjr_panel", "2 — GEM JR"),
        ):
            with self.subTest(panel=name):
                start = source.index(f'key="{name}"')
                self.assertIn(label, source[start:start + 700])
                self.assertIn("render_dashboard_sheet(", source[start:start + 1250])

    def test_native_fallback_question_mark_is_not_a_missing_font_glyph(self):
        self.assertEqual(HELP_ICON, "(?)")
        self.assertNotIn("\\u20dd", HELP_ICON)
        header = header_config(pd.DataFrame({"Ticker": ["ABC"]}))["Ticker"]
        self.assertEqual(header["label"], "Ticker (?)")

    def test_pdufa_columns_expand_to_real_header_and_cell_content(self):
        sample = pd.DataFrame({"Ticker": ["ABC"], "Drug": ["Drug"], "Indication": ["Disease"],
                               "DAYS TO PDUFA": [75], "Cash Runway (months)": [18]})
        configured = header_config(sample)
        self.assertTrue(all(isinstance(configured[c]["width"], int)
                            for c in sample.columns))
        self.assertGreater(configured["Cash Runway (months)"]["width"],
                           configured["Ticker"]["width"])
        preconfigured = header_config(sample, {
            "Ticker": {"label": "Symbol", "width": 50, "help": "Issuer ticker"},
            "Drug": {"width": "large"},
        })
        self.assertGreater(preconfigured["Ticker"]["width"], 50)
        self.assertIsInstance(preconfigured["Drug"]["width"], int)
        self.assertIn("Symbol", preconfigured["Ticker"]["label"])
        self.assertEqual(preconfigured["Ticker"]["help"], "Issuer ticker")

    def test_long_values_are_fully_sized_without_100px_ceiling(self):
        narrow = header_config(pd.DataFrame({"Drug": ["X"]}))["Drug"]["width"]
        medium = header_config(pd.DataFrame({"Drug": ["LONG_DRUG_NAME"]}))["Drug"]["width"]
        long = header_config(pd.DataFrame({"Drug": ["VERY_LONG_DRUG_PROGRAM_NAME_WITH_MULTIPLE_SEGMENTS"]}))["Drug"]["width"]
        self.assertLess(narrow, medium)
        self.assertLess(medium, long)
        self.assertGreater(long, 250)
        self.assertEqual(column_width_for("LABEL", ["X" * 400]),
                         column_width_for("LABEL", ["X" * 400, "X" * 10]))
        self.assertGreater(column_width_for("LABEL", ["X" * 400]), 2000)

    def test_no_pdufa_color_swatch_legend_rendered(self):
        from inspect import getsource
        from pdufa_table_headers import pdufa_dataframe, pdufa_editor
        for renderer in (pdufa_dataframe, pdufa_editor):
            with self.subTest(renderer=renderer.__name__):
                code = getsource(renderer)
                self.assertNotIn("render_countdown_band_key", code)
                self.assertNotIn("COUNTDOWN_HEADER_SUBLINE", code)

    def test_supported_pipeline_renders_dates_and_filters_without_fabricating_missing_values(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('pipeline-data.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('trial-filters.test.cjs'), 0)

    def test_days_column_coloring_preserves_original_values_and_finance_style(self):
        frame = pd.DataFrame({
            "Days to PDUFA": [100, 75, 40, 10, -2, pd.NA],
            "Cash Runway (months)": [18, 18, 18, 18, 18, 18],
        })
        styled = style_countdown_cells(finance_style(frame))
        html = styled.to_html()
        for color in ("#166534", "#86efac", "#fb923c", "#f87171", "#e5e7eb"):
            self.assertIn(color, html)
        self.assertEqual(frame.loc[0, "Days to PDUFA"], 100)
        self.assertEqual(frame.loc[0, "Cash Runway (months)"], 18)

    def test_shared_order_dates_scores_and_cash_runway(self):
        source = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678",
            "PDUFA Target": "2026-12-15", "Evidence score /100": 70,
            "Clinical evidence /30": 21, "Primary endpoint p values observed": "0.001",
            "Financing cycle (separate)": "RED — FINANCING CLOSED (HISTORICAL)",
            "cash_runway_months": 18, "Cash runway verified date": "2026-10-01",
        }])
        view = prepare_pdufa_grid(source, as_of=date(2026, 10, 11))
        self.assertEqual(view.columns[:len(FRONT)].tolist(), list(FRONT))
        self.assertEqual(view.loc[0, "Score /100"], 70)
        self.assertEqual(view.loc[0, "Clinical evidence /30"], 21)
        self.assertEqual(view.loc[0, "PDUFA Date"], "2026-12-15")
        self.assertEqual(int(view.loc[0, "Days to PDUFA"]), 65)
        self.assertEqual(view.loc[0, "Date Classification"], "90–61 DAYS")
        self.assertEqual(view.loc[0, "Primary p"], "0.001")
        self.assertEqual(view.loc[0, "F"], "F CLOSED")
        self.assertEqual(view.loc[0, "2nd Financing Completed"], "NOT VERIFIED")
        self.assertEqual(view.loc[0, "Cash Runway (months)"], 18)
        self.assertEqual(view.loc[0, "Cash Runway As Of"], "2026-10-01")

    def test_front_column_order_and_score_first_sort_with_no_score_last(self):
        self.assertEqual(
            list(FRONT[:5]),
            ["Ticker", "Score /100", "PDUFA Date", "Days to PDUFA", "2nd Financing Completed"],
        )
        self.assertEqual(DISPLAY_ORDER_OPTIONS, ("Top Score", "Ticker A–Z"))
        frame = pd.DataFrame([
            {"Ticker": "ZZZ", "NCT ID": "NCT00000001",
             "Evidence score /100": 20, "Pre-readout research score /100": 20, "PDUFA Date": "2026-12-01"},
            {"Ticker": "BBB", "NCT ID": "NCT00000002",
             "Evidence score /100": 90, "Pre-readout research score /100": 90, "PDUFA Date": "2026-12-20"},
            {"Ticker": "AAA", "NCT ID": "NCT00000003",
             "Evidence score /100": 90, "Pre-readout research score /100": 90, "PDUFA Date": "2026-12-21"},
            {"Ticker": "CCC", "NCT ID": "NCT00000004",
             "PDUFA Date": ""},
        ])
        for view in ("UNIFIED", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"):
            with self.subTest(view=view):
                displayed = prepare_pdufa_grid(frame, view=view,
                                               as_of=date(2026, 10, 11))
                top = sort_pdufa_grid(displayed, "Top Score")
                self.assertEqual(top["Ticker"].tolist(), ["AAA", "BBB", "ZZZ", "CCC"])
                name = sort_pdufa_grid(displayed, "Ticker A–Z")
                self.assertEqual(name["Ticker"].tolist(), ["AAA", "BBB", "CCC", "ZZZ"])
                self.assertEqual(top.columns[:5].tolist(), list(FRONT[:5]))
                self.assertTrue(pd.isna(top.iloc[-1]["Score /100"]))

    def test_two_finance_columns_are_adjacent_to_countdown_in_all_four_views(self):
        for view in ("UNIFIED", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"):
            with self.subTest(view=view):
                result = prepare_pdufa_grid(pd.DataFrame([{
                    "Ticker": "TEST", "Cash Runway (months)": 14,
                    "2nd Financing Completed": "NOT VERIFIED",
                }]), view=view)
                columns = result.columns.tolist()
                idx = columns.index("Days to PDUFA")
                self.assertEqual(columns[idx+1:idx+3], [
                    "2nd Financing Completed", "Cash Runway (months)",
                ])
                self.assertEqual(result.loc[0, "2nd Financing Completed"], "NOT VERIFIED")
                self.assertEqual(result.loc[0, "Cash Runway (months)"], 14)

    def test_weak_closed_stage_never_proves_second_financing_closed(self):
        record = {"Ticker": "TEST", "NCT ID": "NCT00000001",
                  "Financing cycle (separate)": "RED — FINANCING CLOSED (HISTORICAL)",
                  "second_financing_closed": "YES"}
        unverified = prepare_pdufa_grid(pd.DataFrame([record]))
        self.assertEqual(unverified.loc[0, "2nd Financing Completed"], "NOT VERIFIED")
        verified = prepare_pdufa_grid(pd.DataFrame([{**record,
            "event_key": "TEST|EXACT_PROGRAM",
            "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "second_financing_source": "https://www.sec.gov/Archives/example",
        }]))
        self.assertEqual(verified.loc[0, "2nd Financing Completed"],
                         "YES — VERIFIED (HISTORICAL)")
        src = pd.DataFrame([{**record,
            "event_key": "TEST|EXACT_PROGRAM",
            "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "second_financing_source": "not a verified link",
        }])
        self.assertEqual(prepare_pdufa_grid(src).loc[0, "2nd Financing Completed"],
                         "NOT VERIFIED")

    def test_verified_close_joins_only_the_same_exact_trial(self):
        source = pd.DataFrame([
            {"Ticker": "TEST", "NCT ID": "NCT00000001", "Drug": "Alpha"},
            {"Ticker": "TEST", "NCT ID": "NCT00000002", "Drug": "Beta"},
        ])
        post = [{"Ticker": "TEST", "NCT ID": "NCT00000001", "Drug": "Alpha",
                 "2nd Financing Completed": "YES — VERIFIED (HISTORICAL)"}]
        linked = prepare_pdufa_grid(enrich_exact_trials(source, post=post))
        self.assertEqual(linked.loc[0, "2nd Financing Completed"], "YES — VERIFIED (HISTORICAL)")
        self.assertEqual(linked.loc[1, "2nd Financing Completed"], "NOT VERIFIED")

    def test_legacy_event_table_adds_and_orders_financing_and_runway(self):
        frame = pd.DataFrame({
            "Ticker": ["ABC"], "event_key": ["ABC|PROGRAM"],
            "Days Left": [45], "PDUFA Date": ["2026-12-01"],
            "cash_runway_months": [15], "Drug": ["Alpha"],
        })
        out = align_pdufa_finance_columns(frame, audit_path="/nonexistent.csv")
        i = out.columns.get_loc("Days Left")
        self.assertEqual(out.columns[i+1:i+3].tolist(),
                         ["2nd Financing Completed", "Cash Runway (months)"])
        self.assertEqual(out.loc[0, "2nd Financing Completed"], "NOT VERIFIED")
        self.assertEqual(out.loc[0, "Cash Runway (months)"], 15)
        self.assertNotIn("Cash Runway (months)", frame)

    def test_legacy_historical_prediction_without_countdown_gets_financial_neighbors(self):
        frame = pd.DataFrame({"Ticker": ["ABC"], "PDUFA Date": ["2026-12-01"]})
        original = align_pdufa_finance_columns(frame)
        self.assertEqual(original.columns.tolist(), frame.columns.tolist())
        displayed = align_pdufa_finance_columns(frame, add_countdown=True,
                                                audit_path="/nonexistent.csv")
        i = displayed.columns.get_loc("Days to PDUFA")
        self.assertEqual(displayed.columns[i+1:i+3].tolist(),
                         ["2nd Financing Completed", "Cash Runway (months)"])

    def test_exact_event_ledger_and_duplicates_fail_closed(self):
        columns = ["event_key", "second_financing_status",
                   "second_financing_audit_status", "second_financing_closed",
                   "second_financing_source"]
        approved = {
            "event_key": "ABC|PROGRAM",
            "second_financing_status": "CLOSED",
            "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "second_financing_closed": "YES",
            "second_financing_source": "https://www.sec.gov/Archives/edgar/ABC",
        }
        frame = pd.DataFrame([
            {"Ticker": "ABC", "event_key": "ABC|PROGRAM", "Days Left": 45},
            {"Ticker": "XYZ", "event_key": "ABC|PROGRAM", "Days Left": 45},
            {"Ticker": "ABC", "event_key": "ABC|OTHER", "Days Left": 45},
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fin.csv"
            def save(rows):
                with path.open("w", newline="", encoding="utf-8") as output:
                    writer = csv.DictWriter(output, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(rows)
            save([approved])
            shown = align_pdufa_finance_columns(frame, audit_path=path)
            self.assertEqual(shown["2nd Financing Completed"].tolist(), [
                "YES — VERIFIED (HISTORICAL)", "NOT VERIFIED", "NOT VERIFIED",
            ])
            save([approved, approved])
            shown = align_pdufa_finance_columns(frame, audit_path=path)
            self.assertEqual(shown["2nd Financing Completed"].tolist(),
                             ["NOT VERIFIED"] * 3)

    def test_equal_scores_use_numeric_days_before_ticker_with_missing_days_last(self):
        frame = pd.DataFrame([
            {"Ticker": "A_LATER", "Score /100": "90", "Days to PDUFA": "100"},
            {"Ticker": "Z_SOONER", "Score /100": "90", "Days to PDUFA": "9"},
            {"Ticker": "HIGHER", "Score /100": "91", "Days to PDUFA": "180"},
            {"Ticker": "A_UNDATED", "Score /100": "90", "Days to PDUFA": None},
            {"Ticker": "LOWER", "Score /100": "20", "Days to PDUFA": "1"},
            {"Ticker": "UNSCORED_DATED", "Score /100": None, "Days to PDUFA": "3"},
            {"Ticker": "UNSCORED_UNDATED", "Score /100": None, "Days to PDUFA": "unknown"},
        ])
        result = sort_pdufa_grid(frame)
        self.assertEqual(result["Ticker"].tolist(), [
            "HIGHER", "A_LATER", "Z_SOONER", "A_UNDATED", "LOWER",
            "UNSCORED_DATED", "UNSCORED_UNDATED",
        ])
        # Sorting changes the row order, preserving the original field values.
        pd.testing.assert_frame_equal(result[frame.columns].sort_index(), frame)
        self.assertNotIn("_score_sort", result)
        self.assertNotIn("_days_sort", result)

    def test_missing_scores_and_deterministic_ticker_tiebreak(self):
        frame = pd.DataFrame([
            {"Ticker": "ABC", "NCT ID": "NCT00000002", "Score /100": None},
            {"Ticker": "ABC", "NCT ID": "NCT00000001", "Score /100": None},
            {"Ticker": "XYZ", "NCT ID": "NCT00000001", "Score /100": 10},
        ])
        sorted_frame = sort_pdufa_grid(frame)
        self.assertEqual(sorted_frame["NCT ID"].tolist(),
                         ["NCT00000001", "NCT00000001", "NCT00000002"])
        self.assertEqual(sorted_frame["Ticker"].tolist(), ["XYZ", "ABC", "ABC"])
        with self.assertRaises(ValueError):
            sort_pdufa_grid(frame, "Lowest Score")

    def test_legacy_countdown_names_share_score_and_days_descending_order(self):
        for days_column in ("Days to PDUFA", "DAYS TO PDUFA", "days_to_pdufa", "Days Left"):
            with self.subTest(days_column=days_column):
                frame = pd.DataFrame([
                    {"Ticker": "SOON", "Trade Score": "90", days_column: "9"},
                    {"Ticker": "LATER", "Trade Score": "90", days_column: "100"},
                    {"Ticker": "BEST", "Trade Score": "91", days_column: "1"},
                    {"Ticker": "UNDATED", "Trade Score": "90", days_column: None},
                    {"Ticker": "UNSCORED", "Trade Score": None, days_column: "200"},
                ], index=[0, 0, 1, 1, 2])
                result = sort_pdufa_rows(frame)
                self.assertEqual(result["Ticker"].tolist(),
                                 ["BEST", "LATER", "SOON", "UNDATED", "UNSCORED"])
                pd.testing.assert_frame_equal(result, frame.iloc[[2, 1, 0, 3, 4]])

    def test_unscored_countdown_uses_descending_days_and_missing_last(self):
        frame = pd.DataFrame({"Ticker": ["A", "B", "C"],
                              "DAYS TO PDUFA": [9, None, 100]})
        self.assertEqual(sort_pdufa_rows(frame)["Ticker"].tolist(), ["C", "A", "B"])

    def test_missing_data_does_not_become_a_zero_or_financing_close(self):
        source = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678",
            "Linked Phase 2 PRIMARY p": "p=0.012",
            "Financing cycle (separate)": "REVIEW — FINANCING UNVERIFIED",
        }])
        view = prepare_pdufa_grid(source, as_of=date(2026, 10, 11))
        self.assertTrue(pd.isna(view.loc[0, "Score /100"]))
        self.assertEqual(view.loc[0, "Score type"], "NOT SCORED")
        self.assertEqual(view.loc[0, "PDUFA Date"], "")
        self.assertTrue(pd.isna(view.loc[0, "Days to PDUFA"]))
        self.assertTrue(pd.isna(view.loc[0, "Primary p"]))
        self.assertEqual(view.loc[0, "F"], "F UNKNOWN")
        self.assertTrue(pd.isna(view.loc[0, "Cash Runway (months)"]))

    def test_exact_trial_join_rejects_drug_conflict_and_duplicates(self):
        base = pd.DataFrame([{
            "Ticker": "AAAA", "NCT ID": "NCT12345678", "Drug": "drug A",
        }])
        bad = [{
            "Ticker": "AAAA", "NCT ID": "NCT12345678",
            "Drug": "drug B", "Evidence score /100": 95,
            "Financing cycle (separate)": "RED — FINANCING CLOSED (HISTORICAL)",
        }]
        rejected = enrich_exact_trials(base, post=bad)
        self.assertTrue(pd.isna(rejected.loc[0, "Evidence score /100"]))
        self.assertTrue(pd.isna(rejected.loc[0, "Financing cycle (separate)"]))
        duplicate = [dict(bad[0], Drug="drug A"), dict(bad[0], Drug="drug A")]
        rejected = enrich_exact_trials(base, post=duplicate)
        self.assertTrue(pd.isna(rejected.loc[0, "Evidence score /100"]))
        good = [dict(bad[0], Drug="drug A")]
        accepted = enrich_exact_trials(base, post=good)
        self.assertEqual(accepted.loc[0, "Evidence score /100"], 95)

    def test_financing_block_colors_have_black_text(self):
        src = pd.DataFrame({"F": ["F START", "F RUN", "F CLOSED", "F UNKNOWN"]})
        rendered = finance_style(src).to_html()
        for color in ("#bbf7d0", "#fef08a", "#fecaca", "#e5e7eb"):
            self.assertIn(color, rendered)
        self.assertIn("color: #000000", rendered)

    def test_financial_bands_color_runway_score_age_and_unknown(self):
        today = pd.Timestamp.now(tz="America/Los_Angeles").date()
        frame = pd.DataFrame({
            "F": ["F START", "F RUN", "F CLOSED", "F UNKNOWN"],
            "Cash Runway (months)": [18, 8, 3, pd.NA],
            "Financing evidence /20": [18, 12, 4, pd.NA],
            "Cash Runway As Of": [
                today.isoformat(),
                (today - timedelta(days=100)).isoformat(),
                (today - timedelta(days=160)).isoformat(),
                "",
            ],
            "Market Cap": ["$650M", "$4B", "", "NOT VERIFIED"],
            "Cash": ["$80M", None, "$3M", ""],
        })
        html = finance_style(frame).to_html()
        for color in ("#bbf7d0", "#fef08a", "#fecaca", "#dbeafe", "#e5e7eb"):
            self.assertIn(color, html)
        # Styles must never overwrite, backfill or reinterpret source values.
        self.assertEqual(frame.loc[0, "Cash Runway (months)"], 18)
        self.assertEqual(frame.loc[1, "Market Cap"], "$4B")
        self.assertEqual(frame.loc[3, "F"], "F UNKNOWN")

    def test_financial_unknown_and_future_asof_are_not_marked_current(self):
        from pdufa_display_columns import finance_style
        today = pd.Timestamp.now(tz="America/Los_Angeles").date()
        frame = pd.DataFrame({"Cash Runway As Of": [
            (today + timedelta(days=1)).isoformat(), "not verified",
        ]})
        html = finance_style(frame).to_html()
        self.assertIn("#e5e7eb", html)
        self.assertNotIn("#bbf7d0", html)

    def test_each_of_four_tabs_receives_model_specific_score(self):
        """Review triage scores are visibly distinct from clinical evidence."""
        cases = [
            ("PIPELINE", {"Review priority /100": 58,
                          "Review priority status": "REVIEW CANDIDATE"}, 58,
             "PRE: review priority"),
            ("PRE PHASE 3", {"Review priority /100": 47,
                             "Review priority status": "REVIEW CANDIDATE"}, 47,
             "PRE: review priority"),
            ("POST PHASE 3", {"Research priority /100": 34}, 34,
             "POST: research triage"),
            ("UNIFIED", {"Pre-readout research score /100": 81,
                         "Research priority /100": 33}, 81,
             "PRE: reviewed clinical"),
        ]
        for view, evidence, expected, label in cases:
            with self.subTest(view=view):
                frame = pd.DataFrame([{"Ticker": "TEST", **evidence}])
                result = prepare_pdufa_grid(frame, view=view,
                                            as_of=date(2026, 10, 11))
                self.assertEqual(result.columns[:len(FRONT)].tolist(), list(FRONT))
                self.assertEqual(result.loc[0, "Score /100"], expected)
                self.assertEqual(result.loc[0, "Score type"], label)

    def test_clinical_and_evidence_score_overrides_research_priority(self):
        frame = pd.DataFrame([{
            "Ticker": "TEST",
            "Evidence score /100": 74,
            "Research priority /100": 10,
            "Pre-readout research score /100": 88,
            "Review priority /100": 35,
        }])
        expected = {
            "POST PHASE 3": (74, "POST: evidence"),
            "PRE PHASE 3": (88, "PRE: reviewed clinical"),
            "PIPELINE": (88, "PRE: reviewed clinical"),
            "UNIFIED": (74, "POST: evidence"),
        }
        for view, (score, label) in expected.items():
            result = prepare_pdufa_grid(frame, view=view)
            self.assertEqual(result.loc[0, "Score /100"], score)
            self.assertEqual(result.loc[0, "Score type"], label)

    def test_excluded_pre_priority_not_attached_and_invalid_scores_not_used(self):
        frame = pd.DataFrame([{
            "Ticker": "TEST", "Review priority /100": 88,
            "Review priority status": "EXCLUDED — unverified identity",
            "Research priority /100": "not a number",
            "Evidence score /100": 110,
        }])
        for view in ("UNIFIED", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"):
            result = prepare_pdufa_grid(frame, view=view)
            self.assertTrue(pd.isna(result.loc[0, "Score /100"]))
            self.assertEqual(result.loc[0, "Score type"], "NOT SCORED")

    def test_mixed_component_score_types_remain_numeric_without_fabricating_zero(self):
        frame = pd.DataFrame([
            {"Ticker": "ONE", "Clinical evidence /30": 22,
             "Financing evidence /20": "12", "Phase 3 Design /30": "NOT SCORED",
             "Review priority /100": 57, "Preliminary clinical score /100": "80"},
            {"Ticker": "TWO", "Clinical evidence /30": "REVIEW",
             "Financing evidence /20": 33, "Phase 3 Design /30": None,
             "Review priority /100": "", "Preliminary clinical score /100": "REVIEW"},
        ])
        result = prepare_pdufa_grid(frame, view="POST PHASE 3", as_of=date(2026, 10, 13))
        for col in ("Clinical evidence /30", "Financing evidence /20", "Phase 3 Design /30",
                    "Review priority /100", "Preliminary clinical score /100"):
            self.assertTrue(pd.api.types.is_numeric_dtype(result[col].dtype), col)
        self.assertEqual(result.loc[0, "Clinical evidence /30"], 22)
        self.assertEqual(result.loc[0, "Financing evidence /20"], 12)
        self.assertEqual(result.loc[0, "Review priority /100"], 57)
        self.assertEqual(result.loc[0, "Preliminary clinical score /100"], 80)
        for i, col in ((0, "Phase 3 Design /30"), (1, "Clinical evidence /30"),
                       (1, "Financing evidence /20"), (1, "Phase 3 Design /30"),
                       (1, "Review priority /100"), (1, "Preliminary clinical score /100")):
            self.assertTrue(pd.isna(result.loc[i, col]))

    def test_pipeline_exact_trial_join_carries_review_priority_score(self):
        pipeline = pd.DataFrame([{
            "Ticker": "TEST", "NCT ID": "NCT12345678", "Drug": "Alpha",
        }])
        pre = [{
            "Ticker": "TEST", "NCT ID": "NCT12345678", "Drug": "Alpha",
            "Review priority /100": 62, "Review priority status": "REVIEW CANDIDATE",
            "Priority stage /30": 30, "Priority identity /15": 15,
        }]
        matched = enrich_exact_trials(pipeline, pre=pre)
        displayed = prepare_pdufa_grid(matched, view="PIPELINE",
                                       as_of=date(2026, 10, 11))
        self.assertEqual(displayed.loc[0, "Score /100"], 62)
        self.assertEqual(displayed.loc[0, "Score type"], "PRE: review priority")
        self.assertEqual(displayed.loc[0, "Priority stage /30"], 30)



if __name__ == "__main__":
    unittest.main()
