"""Exercise the real Streamlit Pipeline page, not only the filter helpers."""
import unittest
import pandas as pd
from pathlib import Path

from streamlit.testing.v1 import AppTest
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
        self.assertEqual(len(app.dataframe[0].value), 0)
        metrics = [item for item in app.metric
                   if item.label == "Trials / programs displayed"]
        self.assertEqual(len(metrics), 1)
        self.assertEqual(int(metrics[0].value), 0)

    def assert_matching_chart(self, app, stage, low=None, high=None):
        self.assertFalse(list(app.exception))
        self.assertFalse(list(app.error))
        shown = app.dataframe[0].value
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
            item.value for item in app.dataframe[1:]
            if list(item.value.columns) in (["Stage", "Count"], ["DATES", "Count"])
        ]
        self.assertEqual(len(audit_tables), 2)
        for audit in audit_tables:
            counts = audit["Count"]
            self.assertEqual(int(counts.iloc[-1]), len(shown))
            self.assertEqual(int(counts.iloc[:-1].sum()), len(shown))

    def test_plan_tab_renders_editing_and_backup_without_errors(self):
        """PLAN is a genuine reachable page, with an editor and backup controls."""
        app = AppTest.from_file(str(APP_PATH), default_timeout=90)
        app.session_state["nav"] = "11. PLAN"
        app.run()
        self.assertFalse(list(app.exception),
                         [str(error.message) for error in app.exception])
        self.assertEqual(app.radio(key="nav").value, "11. PLAN")
        self.assertTrue(any("11. PLAN — SYSTEM RULES & OPERATING RHYTHM"
                            in item.body for item in app.markdown))
        self.assertTrue(any(item.label == "Plan Items" for item in app.metric))
        self.assertTrue(any(item.key == "save_swiftlook_plan" for item in app.button))
        self.assertTrue(any(item.key == "download_swiftlook_plan"
                            for item in app.get("download_button")))
        # AppTest does not expose Streamlit's data_editor widget as a test element.
        # The live Playwright audit verifies the rendered PLAN screen on mobile.
        plan_code = APP_PATH.read_text(encoding="utf-8")
        self.assertIn('edited_plan = grouped_editor(', plan_code)

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
                          {"PIPELINE", "PRE PHASE 3", "POST PHASE 3", "PDUFA WORKBENCH"}]
        self.assertEqual(submenu_labels, ["PIPELINE", "PRE PHASE 3", "POST PHASE 3"])
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
        self.assertTrue(app.dataframe[0].value["PDUFA Target"].eq("").all())

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
        tickers = app.dataframe[0].value["Ticker"].tolist()
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

    def test_post_phase3_report_remains_under_pdufa(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        self.assertFalse(list(app.exception))
        nav = next(item for item in app.radio if item.key == "nav")
        self.assertNotIn("TODAY", nav.options)
        self.assertTrue(any("POST PHASE 3 — DAILY RESULTS & INTAKE" in item.body for item in app.markdown))
        details = app.get("toggle")
        self.assertTrue(any(item.key == "pipeline_phase3_daily_details_v1" for item in details))
        table_count_before = len(app.dataframe)
        next(item for item in app.get("toggle") if item.key == "pipeline_phase3_daily_details_v1").set_value(True).run()
        self.assertFalse(list(app.exception), "Migrated Phase 3 Daily report must render")
        self.assertTrue(any(item.label == "Yesterday: source-linked posts" for item in app.metric))
        self.assertTrue(any(item.label == "Recorded Phase 3 result rows" for item in app.metric))
        self.assertTrue(app.selectbox(key="today_watchlist_ticker_v2").options)
        self.assertGreater(len(app.dataframe), table_count_before)
        daily_source = (APP_PATH.parent / "today_page.py").read_text(encoding="utf-8")
        self.assertIn("TOP — Phase 3 results posted yesterday", daily_source)
        self.assertIn("BOTTOM — Cumulative Phase 3 result records", daily_source)



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
                        "NCT ID", "Ticker"}.issubset(set(t.value.columns))]
        self.assertTrue(clinical, "PRE PHASE 3 clinical grid must render")
        columns = clinical[0].columns.tolist()
        self.assertEqual(columns[:9], [
            "Ticker", "Review priority rank", "Review priority /100", "Review priority status",
            "Preliminary clinical score /100", "Preliminary score status",
            "Pre-readout research score /100", "Score status",
            "Linked Phase 2 PRIMARY p",
        ])
        self.assertTrue(any("2 provisional, source-cited clinical research score(s) /100" in c.value
                            for c in app.get("caption")))
        self.assertEqual(clinical[0]["Review priority rank"].tolist(), list(range(1, len(clinical[0]) + 1)))
        self.assertTrue(clinical[0]["Review priority /100"].is_monotonic_decreasing)
        self.assertTrue(any("filtered rows have a review-priority score /100" in c.value for c in app.get("caption")))
        self.assertTrue(any("ALL-TRIAL REVIEW PRIORITY" in m.body for m in app.markdown))
        app.selectbox(key="step7_priority_sort").set_value("CLINICAL RESEARCH SCORE")
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        ordered = next(t.value for t in app.dataframe if "Review priority factors" in t.value.columns)
        self.assertEqual(ordered.iloc[:2]["Ticker"].tolist(), ["TRVI", "LBRX"])
        self.assertEqual(ordered.iloc[:2]["Preliminary clinical score /100"].tolist(), [80,72])
        app.selectbox(key="step7_priority_sort").set_value("REVIEW PRIORITY")
        self.assertTrue(any("DATED CLINICAL RESEARCH PILOT SCORES" in m.body
                            for m in app.markdown))
        pilot_cards = {m.label: m.value for m in app.metric
                       if "· NCT0" in m.label and "RESEARCH /100" in m.label}
        trvi_card = next((value for label, value in pilot_cards.items()
                          if "TRVI · NCT07671911" in label), None)
        lbrx_card = next((value for label, value in pilot_cards.items()
                          if "LBRX · NCT07363577" in label), None)
        self.assertEqual(trvi_card, "80/100")
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
                         if {"NCT ID", "Preliminary clinical score /100"}.issubset(t.value.columns))
        trvi = trvi_grid.loc[trvi_grid["NCT ID"].eq("NCT07671911")]
        self.assertEqual(len(trvi), 1)
        self.assertEqual(float(trvi.iloc[0]["Preliminary clinical score /100"]), 80.0)
        app.text_input(key="step7_trial_search").set_value("LBRX")
        app.session_state["pdufa_subtab"] = "PRE PHASE 3"
        app.run()
        self.assertFalse(list(app.exception))
        lbrx_grid = next(t.value for t in app.dataframe
                         if {"NCT ID", "Preliminary clinical score /100"}.issubset(t.value.columns))
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
                                 if {"NCT ID", "Pre-readout research score /100"}.issubset(t.value.columns))
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
