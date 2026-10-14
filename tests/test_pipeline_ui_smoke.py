"""Exercise the real Streamlit Pipeline page, not only the filter helpers."""
import unittest
import re
import pandas as pd
from pathlib import Path

from streamlit.testing.v1 import AppTest
from pdufa_display_columns import FRONT
from html.parser import HTMLParser


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class CountRows(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.rows = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"li", "div"} and "data-category" in values and "data-count" in values:
            self.rows.append((values["data-category"], int(values["data-count"])))


class PipelinePageSmokeTests(unittest.TestCase):
    def count_charts(self, app):
        return [item for item in app.markdown if '<div class="pipeline-count-chart"' in item.body]

    def assert_empty_chart(self, app):
        self.assertFalse(list(app.exception))
        self.assertFalse(list(app.error))
        self.assertIn("STAGES", {item.label for item in app.multiselect})
        self.assertIn("DATES", {item.label for item in app.multiselect})
        self.assertEqual(len(self.count_charts(app)), 2)
        self.assertEqual(len(next(item.value for item in app.dataframe if "Current Stage" in item.value.columns)), 0)
        metrics = [item for item in app.metric
                   if item.label == "Trials / programs displayed"]
        self.assertEqual(len(metrics), 1)
        self.assertEqual(int(metrics[0].value), 0)

    def assert_matching_chart(self, app, stage, low=None, high=None):
        self.assertFalse(list(app.exception))
        self.assertFalse(list(app.error))
        shown = next(item.value for item in app.dataframe if "Current Stage" in item.value.columns)
        self.assertGreater(len(shown), 0)
        self.assertTrue(shown["Current Stage"].eq(stage).all())
        if low is not None:
            self.assertTrue(shown["Days to PDUFA"].ge(low).all())
        if high is not None:
            self.assertTrue(shown["Days to PDUFA"].le(high).all())
        metric = next(item for item in app.metric
                      if item.label == "Trials / programs displayed")
        self.assertEqual(int(metric.value), len(shown))
        # The charts under the selectors must use the displayed records.
        charts = self.count_charts(app)
        self.assertEqual(len(charts), 2)
        for chart, column in zip(charts, ("Current Stage", "DATES")):
            rows = CountRows(chart.body).rows
            self.assertEqual(sum(count for _, count in rows), len(shown))
            expected = shown[column].value_counts().to_dict()
            for category, count in rows:
                self.assertEqual(count, expected.get(category, 0))
        # The two independently rendered count tables must reconcile to the
        # rows the user actually sees, rather than historical milestone tags.
        # The second Pipeline sub-tab also contains watchlist and research
        # dataframes, so only inspect the two stage/date count audit tables.
        audit_tables = [
            item.value for item in app.dataframe
            if list(item.value.columns) in (["Stage", "Count"], ["DATES", "Count"])
        ]
        self.assertEqual(len(audit_tables), 2)
        for audit in audit_tables:
            counts = audit["Count"]
            self.assertEqual(int(counts.iloc[-1]), len(shown))
            self.assertEqual(int(counts.iloc[:-1].sum()), len(shown))

    def test_plan_tab_removed_but_saved_plan_preserved(self):
        """Deleted PLAN screen must redirect to PDUFA without losing its data."""
        app = AppTest.from_file(str(APP_PATH), default_timeout=90)
        app.session_state["nav"] = "11. PLAN"
        app.run()
        self.assertFalse(list(app.exception),
                         [str(error.message) for error in app.exception])
        main_nav = app.radio(key="nav")
        self.assertEqual(main_nav.value, "PDUFA")
        self.assertNotIn("11. PLAN", main_nav.options)
        self.assertTrue((APP_PATH.parent / "data/swiftlook_plan.csv").is_file())
        self.assertTrue(any("PIPELINE — PDUFA COUNTDOWN" in item.body
                            for item in app.markdown))

    def test_pipeline_opens_with_both_selectors_and_empty_chart(self):
        # Streamlit resolves relative paths against this test file in newer
        # versions; always point at the repository's actual entry point.
        app = AppTest.from_file(str(APP_PATH), default_timeout=60)
        app.session_state["nav"] = "PDUFA"
        app.run()

        exceptions = [str(error.message) for error in app.exception]
        self.assertFalse(exceptions, f"Streamlit render exceptions: {exceptions}")
        self.assertEqual(len(self.count_charts(app)), 2)
        nav = next(item for item in app.radio if item.key == "nav")
        self.assertIn("PDUFA", nav.options)
        self.assertNotIn("WATCHLIST", nav.options)
        submenu_labels = [item.label for item in app.get("tab") if item.label in
                          {"GEM", "PIPELINE", "PRE PHASE 3", "POST PHASE 3", "PDUFA WORKBENCH"}]
        self.assertEqual(submenu_labels, ["GEM", "PIPELINE", "PRE PHASE 3", "POST PHASE 3"])
        self.assertTrue(any("WATCHLIST MANAGEMENT" in item.body for item in app.markdown))
        self.assertTrue(any("PIPELINE — PDUFA COUNTDOWN, WATCHLIST & ANALYSIS" in item.body
                            for item in app.markdown))
        stage_rows = CountRows(self.count_charts(app)[0].body).rows
        self.assertEqual([label for label, _ in stage_rows], app.multiselect(key="pipeline_stages_v9").options)
        self.assertEqual(len(stage_rows), 14)
        date_rows = CountRows(self.count_charts(app)[1].body).rows
        self.assertEqual([label for label, _ in date_rows], app.multiselect(key="pipeline_dates_v9").options)
        self.assertTrue(any("STAGE COUNTS" in item.body for item in app.markdown))
        self.assertTrue(any("DATE TRIAL COUNTS" in item.body for item in app.markdown))
        selectors = {item.label: item for item in app.multiselect}
        self.assertIn("STAGES", selectors)
        self.assertIn("DATES", selectors)
        self.assertEqual(selectors["STAGES"].value, [])
        self.assertEqual(selectors["DATES"].value, [])
        self.assertTrue(
            any("PDUFA TRIALS / PROGRAMS" in item.body for item in app.markdown),
            "Bottom chart title was not rendered",
        )
        self.assertTrue(len(app.dataframe), "Bottom chart frame was not rendered")
        metric = [item for item in app.metric
                  if item.label == "Trials / programs displayed"]
        self.assertEqual(len(metric), 1)
        self.assertEqual(str(metric[0].value), "0")

        # Stage selection alone must never populate results or hide DATES.
        selectors["STAGES"].set_value(["PDUFA Decision"]).run()
        self.assertFalse(list(app.exception))
        selectors_after = {item.label: item for item in app.multiselect}
        self.assertIn("DATES", selectors_after)
        self.assertEqual(selectors_after["DATES"].value, [])
        metric_after = [item for item in app.metric
                        if item.label == "Trials / programs displayed"]
        self.assertEqual(str(metric_after[0].value), "0")
        self.assert_empty_chart(app)

        # Both selections still need an explicit Show click.
        app.multiselect(key="pipeline_dates_v9").set_value(["0–30 DAYS"]).run()
        self.assert_empty_chart(app)
        self.assertFalse(app.button(key="pipeline_show_v9").disabled)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_matching_chart(app, "PDUFA Decision", 0, 30)

        # A different window immediately clears previously applied results.
        app.multiselect(key="pipeline_dates_v9").set_value(["31–60 DAYS"]).run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_matching_chart(app, "PDUFA Decision", 31, 60)

        # Refresh keeps both controls available and requires applying again.
        app.button(key="pipeline_refresh_v9").click().run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_matching_chart(app, "PDUFA Decision", 31, 60)

        # Changing stage cannot retain the prior PDUFA application's rows.
        app.multiselect(key="pipeline_stages_v9").set_value(["Phase 3"]).run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_empty_chart(app)
        app.multiselect(key="pipeline_dates_v9").set_value(["NO PDUFA YET"]).run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_matching_chart(app, "Phase 3")
        self.assertTrue(next(t.value for t in app.dataframe if "PDUFA Target" in t.value.columns)["PDUFA Target"].eq("").all())

        # Search and sort changes also invalidate a previously applied chart.
        app.text_input(key="pipeline_query_v9").set_value("NO_SUCH_PIPELINE_RECORD_9F2A").run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_empty_chart(app)
        app.text_input(key="pipeline_query_v9").set_value("")
        app.selectbox(key="pipeline_sort_v9").set_value("Ticker A–Z").run()
        self.assert_empty_chart(app)
        app.button(key="pipeline_show_v9").click().run()
        self.assert_matching_chart(app, "Phase 3")
        tickers = next(t.value for t in app.dataframe if "Current Stage" in t.value.columns)["Ticker"].tolist()
        self.assertEqual(tickers, sorted(tickers))

        app.button(key="pipeline_clear_v9").click().run()
        self.assert_empty_chart(app)
        self.assertEqual(app.multiselect(key="pipeline_stages_v9").value, [])
        self.assertEqual(app.multiselect(key="pipeline_dates_v9").value, [])
        self.assertTrue(app.button(key="pipeline_show_v9").disabled)

        # Selecting DATES alone is equally insufficient, including after reset.
        app.multiselect(key="pipeline_dates_v9").set_value(["0–30 DAYS"]).run()
        self.assert_empty_chart(app)
        self.assertTrue(app.button(key="pipeline_show_v9").disabled)


    def test_legacy_pipeline_navigation_migrates_to_pdufa(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=60)
        app.session_state["nav"] = "PIPELINE"
        app.session_state["detail_return_page"] = "PIPELINE"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.radio(key="nav").value, "PDUFA")
        self.assertEqual(app.session_state["detail_return_page"], "PDUFA")
        self.assertNotIn("PIPELINE", app.radio(key="nav").options)

    def test_watchlist_add_remove_survives_master_table_removal(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=60)
        app.session_state["nav"] = "PDUFA"
        app.run()
        self.assertFalse(list(app.exception))
        picker = app.selectbox(key="watchlist_ticker_picker_v1")
        self.assertTrue(picker.options, "Ticker choices must come from saved Pipeline data")
        ticker = picker.options[0]
        picker.set_value(ticker).run()
        self.assertFalse(list(app.exception))
        self.assertFalse(app.button(key="watchlist_add_picker_v1").disabled)
        app.button(key="watchlist_add_picker_v1").click().run()
        self.assertFalse(list(app.exception))
        self.assertIn(ticker, app.session_state["watchlist"])
        self.assertFalse(app.button(key="watchlist_remove_picker_v1").disabled)
        app.button(key="watchlist_remove_picker_v1").click().run()
        self.assertFalse(list(app.exception))
        self.assertNotIn(ticker, app.session_state["watchlist"])


    def test_old_phase3_daily_tab_selection_migrates(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "PHASE 3 DAILY"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.session_state["pdufa_subtab"], "POST PHASE 3")
        labels = [item.label for item in app.get("tab")]
        self.assertIn("POST PHASE 3", labels)
        self.assertNotIn("PHASE 3 DAILY", labels)

    def test_post_phase3_three_sections_merged_into_one_page(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "POST PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        overview = next(item for item in app.get("tab")
                        if item.label == "GEM")
        self.assertEqual([item for item in overview if item.type != "tab"], [])
        post = next(item for item in app.get("tab")
                    if item.label == "POST PHASE 3")
        self.assertTrue(any("UNIFIED CLINICAL → TRADING DISPLAY" in item.body
                            for item in post.get("markdown")))
        self.assertTrue(any(item.key == "unified_export"
                            for item in post.get("download_button")))
        labels = [item.label for item in app.get("tab")]
        self.assertIn("POST PHASE 3", labels)
        self.assertNotIn("PHASE 3 DAILY", labels)
        self.assertTrue(any(
            "POST PHASE 3 — TRADING WORKSPACE" in item.body
            for item in app.markdown
        ))
        self.assertFalse(any(
            item.key == "post_phase3_workspace_stage_v1" for item in app.radio
        ), "Merged POST PHASE 3 must not require another stage selector")
        self.assertTrue(any(
            "STAGE 1 — PHASE 3" in item.body for item in app.markdown
        ))
        sorting = app.selectbox(key="postphase3_stage1_sort")
        self.assertEqual(list(sorting.options), ["Top Score", "Ticker A–Z"])
        self.assertEqual(sorting.value, "Top Score")
        self.assertFalse(any(
            "TOP 10 — RESEARCH PRIORITY" in item.body for item in app.markdown
        ))
        self.assertTrue(any(
            "STAGE 2 — GREEN ENTRY → YELLOW HOLD → RED EXIT WATCH" in item.body
            for item in app.markdown
        ))
        self.assertTrue(any(
            "STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH" in item.body
            for item in app.markdown
        ))
        self.assertTrue(any(
            "No actual positions have been supplied" in item.body
            for item in app.info
        ))

        # One ticker focus must update the relocated clinical view and the
        # existing candidate queue without losing either display or its scores.
        score_tables = [item.value for item in post.get("dataframe")
                        if {"Ticker", "Score /100", "Score type"}
                        .issubset(item.value.columns)]
        self.assertEqual(len(score_tables), 2)
        shared = set(score_tables[0]["Ticker"]) & set(score_tables[1]["Ticker"])
        self.assertTrue(shared, "Saved feeds need a shared ticker to verify linked focus")
        ticker = sorted(shared)[0]
        app.selectbox(key="postphase3_shared_ticker").set_value(ticker).run()
        self.assertFalse(list(app.exception))
        post = next(item for item in app.get("tab")
                    if item.label == "POST PHASE 3")
        focused = [item.value for item in post.get("dataframe")
                   if {"Ticker", "Score /100", "Score type"}
                   .issubset(item.value.columns)]
        self.assertEqual(len(focused), 2)
        for frame in focused:
            self.assertGreater(len(frame), 0)
            self.assertTrue(frame["Ticker"].eq(ticker).all())
        from post_phase3_backfill_queue import build_backfill_queue
        queue, _ = build_backfill_queue(APP_PATH.parent / "data")
        expected = sum(str(row.get("ticker") or "").upper() == ticker
                       for row in queue)
        count = next(item for item in post.get("metric")
                     if item.label == "Historical research leads")
        self.assertEqual(int(count.value), expected)
        app.selectbox(key="postphase3_shared_ticker").set_value("All tickers").run()
        self.assertFalse(list(app.exception))

        # AppTest does not send frontend tab-selection events. Use a fresh
        # Overview session for widget interactions; the live browser audit
        # checks switching between the actual tabs.
        overview_app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        overview_app.session_state["nav"] = "PDUFA"
        overview_app.session_state["pdufa_subtab"] = "GEM"
        overview_app.run()
        self.assertFalse(list(overview_app.exception))
        overview = next(item for item in overview_app.get("tab")
                        if item.label == "GEM")
        headings = [item.body for item in overview.get("markdown")]
        self.assertFalse(any("#1-DB" in heading for heading in headings))
        for title in ("### #2-PIPELINE",
                      "### #3-PRE3", "### #4-POST3"):
            self.assertTrue(any(title in heading for heading in headings), title)
        self.assertTrue(any(item.key == "overview_export"
                            for item in overview.get("download_button")))
        overview_app.selectbox(key="overview_shared_ticker").set_value(ticker).run()
        self.assertFalse(list(overview_app.exception))
        self.assertEqual(overview_app.session_state["pdufa_subtab"], "GEM")
        overview = next(item for item in overview_app.get("tab")
                        if item.label == "GEM")
        focused = [item.value for item in overview.get("dataframe")
                   if {"Ticker", "Score /100", "Score type", "F"}
                   .issubset(item.value.columns)]
        # The three headline PIPELINE/PRE3/POST3 sheets now use HTML tables
        # (real circled help icons) rather than native Streamlit dataframes.
        # AppTest can inspect the three remaining native evidence/timeline grids.
        self.assertEqual(len(focused), 3)
        self.assertGreaterEqual(sum(not frame.empty for frame in focused), 1)
        for frame in focused:
            self.assertTrue(frame["Ticker"].eq(ticker).all())
        timeline = next(item.value for item in overview.get("dataframe")
                        if {"Date Classification", "PDUFA source"}.issubset(item.value.columns)
                        and "F" not in item.value.columns)
        self.assertTrue(timeline["Ticker"].eq(ticker).all())
        self.assertTrue(timeline["Score /100"].dropna().is_monotonic_decreasing)
        for _, group in timeline.groupby("Score /100", dropna=False, sort=False):
            self.assertTrue(group["Days to PDUFA"].dropna().is_monotonic_decreasing)
        overview_app.text_input(key="overview_query").set_value("__NO_MATCH__").run()
        self.assertFalse(list(overview_app.exception))
        overview = next(item for item in overview_app.get("tab")
                        if item.label == "GEM")
        counts = {item.label: int(item.value) for item in overview.get("metric")
                  if item.label in {"Matching programs", "Matching pre-readout programs",
                                    "Matching candidates"}}
        self.assertEqual(counts, {"Matching programs": 0,
                                 "Matching pre-readout programs": 0,
                                 "Matching candidates": 0})
        overview_app.text_input(key="overview_query").set_value("").run()
        overview_app.selectbox(key="overview_shared_ticker").set_value("All tickers").run()
        self.assertFalse(list(overview_app.exception))
        self.assertTrue(any("STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH" in item.body
                            for item in app.markdown))

    def test_post_phase3_stage3_has_no_fabricated_backtest_wins(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "POST PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertTrue(any(
            "STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH" in item.body
            for item in app.markdown
        ))
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics.get("Verified event timelines"), "0")
        self.assertEqual(metrics.get("Historical OHLCV rows"), "0")
        self.assertEqual(metrics.get("Simulated trade scenarios"), "0")
        self.assertTrue(any(
            "BACKTEST NOT READY" in item.body for item in app.warning
        ))

    def test_pre_phase3_subtab_never_fabricates_success_probability(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        self.assertFalse(list(app.exception))
        nav = app.radio(key="nav")
        self.assertIn("PDUFA", nav.options)
        self.assertNotIn("PRE PHASE 3", nav.options)
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")

        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.session_state["pdufa_subtab"], "PRE PHASE 3")
        self.assertFalse(any(item.label == "Phase 1–3 company–trial leads"
                             for item in app.metric))
        self.assertFalse(any("PRE PHASE 3 — Clinical Trial Evaluation" in item.body
                             for item in app.markdown))
        source = (APP_PATH.parent/"clinical_step3.py").read_text(encoding="utf-8")
        self.assertIn("if (complete and owner)", source)
        self.assertIn("NOT SCORED — INCOMPLETE OR UNVERIFIED", source)
        self.assertNotIn("NOT READY FOR PHASE 3 SUCCESS PROBABILITIES", source)
        # PDUFA Pipeline stays adjacent and unchanged.
        app.session_state["pdufa_subtab"] = "PIPELINE"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertTrue(any("PDUFA — CLINICAL AND REGULATORY STAGES" in item.body
                            for item in app.markdown))


    def test_pre_phase3_full_priority_order_and_separate_clinical_pilots(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        clinical = [t.value for t in app.dataframe
                    if {"Linked Phase 2 PRIMARY p", "Pre-readout research score /100",
                        "NCT ID", "Ticker", "Review priority rank"}.issubset(set(t.value.columns))]
        self.assertTrue(clinical, "PRE PHASE 3 clinical grid must render")
        columns = clinical[0].columns.tolist()
        self.assertEqual(columns[:len(FRONT)], list(FRONT))
        self.assertIn("Review priority rank", columns)
        self.assertIn("Linked Phase 2 PRIMARY p", columns)
        self.assertIn("Review priority /100", columns)
        # Source-dated pilot assessments can expire or be refreshed.
        captions = [c.value for c in app.get("caption")
                    if "provisional, source-cited clinical research score(s) /100" in c.value]
        self.assertEqual(len(captions), 1)
        count = re.match(
            r"^(\d+) provisional, source-cited clinical research score\(s\) /100",
            captions[0],
        )
        self.assertIsNotNone(count, captions[0])
        self.assertGreaterEqual(int(count.group(1)), 0)
        self.assertIn("not independently audited clinical scores", captions[0])
        self.assertEqual(app.selectbox(key="step7_priority_sort").value, "Top Score")
        self.assertTrue(clinical[0]["Score /100"].dropna().is_monotonic_decreasing)
        self.assertEqual(columns[:5], ["Ticker", "Score /100", "PDUFA Date",
                                        "Days to PDUFA", "2nd Financing Completed"])
        self.assertTrue(any("filtered rows have a review-priority score /100" in c.value for c in app.get("caption")))
        self.assertTrue(any("ALL-TRIAL REVIEW PRIORITY" in m.body for m in app.markdown))
        app.selectbox(key="step7_priority_sort").set_value("Top Score")
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        ordered = next(t.value for t in app.dataframe if "Review priority factors" in t.value.columns)
        self.assertTrue(ordered["Score /100"].dropna().is_monotonic_decreasing)
        self.assertEqual(ordered.columns[:5].tolist(), [
            "Ticker", "Score /100", "PDUFA Date", "Days to PDUFA", "2nd Financing Completed",
        ])
        app.selectbox(key="step7_priority_sort").set_value("Ticker A–Z")
        # Expired pilot evidence must stay absent from numeric scorecards,
        # while the section remains visible with a missing-evidence warning.
        if int(count.group(1)) == 0:
            self.assertTrue(any("DATED CLINICAL RESEARCH PILOT SCORES" in m.body
                                for m in app.markdown))
            self.assertTrue(any("NO CURRENT SOURCE-DATED PILOT SCORES" in m.body
                                for m in app.info))
            self.assertFalse(any("· NCT0" in m.label and "RESEARCH /100" in m.label
                                 for m in app.metric))
            source = APP_PATH.read_text(encoding="utf-8")
            self.assertIn('"DOWNLOAD SOURCE-REVIEW SCORING TEMPLATE FOR THESE 10"', source)
            return
        self.assertTrue(any("DATED CLINICAL RESEARCH PILOT SCORES" in m.body
                            for m in app.markdown))
        pilot_cards = {m.label: m.value for m in app.metric
                       if "· NCT0" in m.label and "RESEARCH /100" in m.label}
        trvi_card = next((value for label, value in pilot_cards.items()
                          if "TRVI · NCT07671911" in label), None)
        lbrx_card = next((value for label, value in pilot_cards.items()
                          if "LBRX · NCT07363577" in label), None)
        # Require exact pilot values only when their dated evidence remains
        # on-screen; source expiry may leave one valid pilot but not both.
        if trvi_card is not None:
            self.assertEqual(trvi_card, "80/100")
        if lbrx_card is not None:
            self.assertEqual(lbrx_card, "72/100")
        self.assertFalse(any("NCT07369154" in label for label in pilot_cards),
                         "Long-term safety NOVA-3 must not inherit NOVA-2 score")
        app.text_input(key="step7_trial_search").set_value("TRVI")
        # AppTest does not submit the active keyed-tab widget along with text
        # inputs; preserve the tab explicitly when simulating a rerun.
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        trvi_grid = next(t.value for t in app.dataframe
                         if {"NCT ID", "Preliminary clinical score /100", "Review priority rank"}.issubset(t.value.columns))
        trvi = trvi_grid.loc[trvi_grid["NCT ID"].eq("NCT07671911")]
        self.assertEqual(len(trvi), 1)
        self.assertEqual(float(trvi.iloc[0]["Preliminary clinical score /100"]), 80.0)
        app.text_input(key="step7_trial_search").set_value("LBRX")
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        lbrx_grid = next(t.value for t in app.dataframe
                         if {"NCT ID", "Preliminary clinical score /100", "Review priority rank"}.issubset(t.value.columns))
        nova2 = lbrx_grid.loc[lbrx_grid["NCT ID"].eq("NCT07363577")]
        nova3 = lbrx_grid.loc[lbrx_grid["NCT ID"].eq("NCT07369154")]
        self.assertEqual(len(nova2), 1)
        self.assertEqual(float(nova2.iloc[0]["Preliminary clinical score /100"]), 72.0)
        self.assertIn("NCT06179108 p=0.0009", nova2.iloc[0]["Linked Phase 2 PRIMARY p"])
        # On a feature branch the newly added identity source may not yet be
        # present in the saved feed. Exact-NCT generated-output assertions are
        # exercised separately in test_nova2_exact_identity_review.py.
        identity_source=nova2.iloc[0]["Company identity review source"]
        if identity_source:
            self.assertEqual(nova2.iloc[0]["Company/program identity"],"VERIFIED")
            self.assertIn("nova-2",identity_source)
            from datetime import datetime, date
            from zoneinfo import ZoneInfo
            if datetime.now(ZoneInfo("America/Los_Angeles")).date() in {date(2026,10,10), date(2026,10,11)}:
                self.assertEqual(float(nova2.iloc[0]["Pre-readout research score /100"]),72)
                self.assertEqual(nova2.iloc[0]["Score status"],
                                 "100-POINT RESEARCH SCORE — UNCALIBRATED")
            else:
                self.assertTrue(pd.isna(nova2.iloc[0]["Pre-readout research score /100"]))
        else:
            self.assertEqual(nova2.iloc[0]["Company/program identity"],"REVIEW")
            self.assertTrue(pd.isna(nova2.iloc[0]["Pre-readout research score /100"]))
        self.assertEqual(nova2.iloc[0]["Phase 2 PRIMARY evidence count"], 3)
        self.assertTrue(nova2.iloc[0]["Phase 2 link review source"].startswith("https://ir.lbpharma.us/"))
        self.assertEqual(len(nova3), 1)
        self.assertTrue(pd.isna(nova3.iloc[0]["Preliminary clinical score /100"]))
        # The issuer newsroom checks are explicitly dated Oct 10 and Oct 11.
        # Do not let yesterday's reviewed research score silently pass as current.
        from datetime import datetime, date
        from zoneinfo import ZoneInfo
        local_day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
        if local_day in {date(2026,10,10), date(2026,10,11)}:
            app.text_input(key="step7_trial_search").set_value("TRVI")
            app.session_state["pdufa_subtab"] = "PRE PHASE 3"
            app.run()
            reviewed_grid = next(t.value for t in app.dataframe
                                 if {"NCT ID", "Pre-readout research score /100", "Review priority rank"}.issubset(t.value.columns))
            reviewed = reviewed_grid.loc[reviewed_grid["NCT ID"].eq("NCT07671911")]
            self.assertEqual(len(reviewed), 1)
            self.assertEqual(float(reviewed.iloc[0]["Pre-readout research score /100"]), 80.0)
            self.assertEqual(reviewed.iloc[0]["Score status"],
                             "100-POINT RESEARCH SCORE — UNCALIBRATED")
        else:
            self.assertFalse(
                (clinical[0]["Pre-readout research score /100"].notna()
                 & clinical[0]["Score status"].eq("100-POINT RESEARCH SCORE — UNCALIBRATED")
                 & clinical[0]["Ticker"].eq("TRVI")).any(),
                "Old issuer checks must not remain current after their cutoff",
            )
        self.assertTrue(any("NEXT 10 PHASE 3 CLINICAL SCORING REVIEWS" in m.body
                            for m in app.markdown))
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertIn('"DOWNLOAD SOURCE-REVIEW SCORING TEMPLATE FOR THESE 10"', source)


    def test_legacy_pre_phase3_main_navigation_redirects_to_subtab(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PRE PHASE 3"
        app.session_state["detail_return_page"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.radio(key="nav").value, "PDUFA")
        self.assertEqual(app.session_state["pdufa_subtab"], "PRE PHASE 3")
        self.assertEqual(app.session_state["detail_return_page"], "PDUFA")
        self.assertFalse(any(item.label == "Phase 1–3 company–trial leads"
                             for item in app.metric))
        self.assertFalse(any("PRE PHASE 3 — Clinical Trial Evaluation" in item.body
                             for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
