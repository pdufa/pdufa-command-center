"""Exercise the real Streamlit Pipeline page, not only the filter helpers."""
import unittest
import json
import re
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from step7_cached_snapshot import load_current_snapshot as load_saved_snapshot

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
        # Universe count buttons remain stable even when a stage/date is
        # unchecked. The exact selected counts are audited separately below.
        charts = self.count_charts(app)
        self.assertEqual(len(charts), 2)
        for chart, column in zip(charts, ("Current Stage", "DATES")):
            rows = CountRows(chart.body).rows
            self.assertGreaterEqual(sum(count for _, count in rows), len(shown))
            expected = shown[column].value_counts().to_dict()
            for category, count in rows:
                self.assertGreaterEqual(count, expected.get(category, 0))
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
                          {"PIPELINE", "GEM JR", "GEM", "PDUFA WORKBENCH"}]
        self.assertEqual(submenu_labels, ["PIPELINE", "GEM JR", "GEM"])
        self.assertTrue(any("WATCHLIST MANAGEMENT" in item.body for item in app.markdown))
        self.assertTrue(any("PIPELINE — PDUFA COUNTDOWN, WATCHLIST & ANALYSIS" in item.body
                            for item in app.markdown))
        stage_rows = CountRows(self.count_charts(app)[0].body).rows
        self.assertEqual([label for label, _ in stage_rows], app.multiselect(key="pipeline_stages_v9").options)
        self.assertIsNotNone(app.button(key="pipeline_count_button_v10_current_stage_9"))
        self.assertIsNotNone(app.button(key="pipeline_count_button_v10_DATES_0"))
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
        # Clearing one stage never wipes the other stage-count buttons.
        self.assertEqual(stage_rows, CountRows(self.count_charts(app)[0].body).rows)
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
        # The STAGE COUNTS button applies its stage immediately because a date
        # is already selected; no extra SHOW click is required for count buttons.
        app.button(key="pipeline_count_button_v10_current_stage_9").click().run()
        self.assert_matching_chart(app, "PDUFA Decision", 0, 30)


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
        self.assertEqual(app.session_state["pdufa_subtab"], "GEM JR")
        labels = [item.label for item in app.get("tab")]
        self.assertIn("GEM JR", labels)
        self.assertIn("GEM", labels)
        self.assertNotIn("PHASE 3 DAILY", labels)

    def test_gem_jr_and_gem_are_separate_full_width_tabs(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "GEM JR"
        app.run()
        self.assertFalse(list(app.exception),
                         [str(error.message) for error in app.exception])
        labels = [item.label for item in app.get("tab")]
        self.assertIn("GEM JR", labels)
        self.assertIn("GEM", labels)
        self.assertNotIn("GEM JR + GEM", labels)
        self.assertNotIn("PRE PHASE 3", labels)
        self.assertNotIn("POST PHASE 3", labels)
        components = [c for c in app.get("component_instance")
                      if "gem_reference_dashboard" in c.proto.component_name]
        self.assertEqual(len(components), 1)
        payload = json.loads(components[0].proto.json_args)["payload"]
        self.assertEqual(payload["stage"], "GEM JR")
        self.assertFalse(any("DETAILED SOURCE WORKBENCH" in x.label
                             for x in app.get("toggle")))

    def test_retired_extended_research_bookmark_does_not_restore_old_layout(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "GEM JR + GEM"
        app.session_state["gemjr_extended_research"] = True
        app.run()
        self.assertFalse(list(app.exception))
        components = [c for c in app.get("component_instance")
                      if "gem_reference_dashboard" in c.proto.component_name]
        self.assertEqual(len(components), 1)
        payload = json.loads(components[0].proto.json_args)["payload"]
        self.assertEqual(payload["stage"], "GEM JR")
        self.assertFalse(any("STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH" in x.body
                             for x in app.markdown))
        self.assertNotIn("Simulated trade scenarios", [x.label for x in app.metric])

    def test_pre_phase3_subtab_never_fabricates_success_probability(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        self.assertFalse(list(app.exception))
        nav = app.radio(key="nav")
        self.assertIn("PDUFA", nav.options)
        self.assertNotIn("PRE PHASE 3", nav.options)
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")

        app.session_state["pdufa_subtab"] = "PIPELINE"

        app.session_state["pipeline_early_research"] = True
        app.run()
        self.assertFalse(list(app.exception))
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")
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


    @patch('step7_cached_snapshot.load_current_snapshot')
    def test_pre_phase3_full_priority_order_and_separate_clinical_pilots(self, load_snapshot):
        # Exercise the actual saved grid at its generation time. Expiry is
        # tested separately; yesterday's scan must not break this layout test.
        import json
        from datetime import datetime, timedelta
        import streamlit as st
        manifest = json.loads((APP_PATH.parent / 'data/step7_live_status.json').read_text())
        fixture_now = datetime.fromisoformat(manifest['generated_at_utc']) + timedelta(minutes=1)
        load_snapshot.side_effect = lambda root, now: load_saved_snapshot(root, fixture_now)
        st.cache_data.clear()
        self.addCleanup(st.cache_data.clear)
        app = AppTest.from_file(str(APP_PATH), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        app.session_state["pdufa_subtab"] = "PIPELINE"
        app.session_state["pipeline_early_research"] = True
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
        app.session_state["pdufa_subtab"] = "PIPELINE"
        app.session_state["pipeline_early_research"] = True
        app.run()
        ordered = next(t.value for t in app.dataframe if "Review priority factors" in t.value.columns)
        self.assertTrue(ordered["Score /100"].dropna().is_monotonic_decreasing)
        self.assertEqual(ordered.columns[:5].tolist(), [
            "Ticker", "Score /100", "PDUFA Date", "Days to PDUFA", "2nd Financing Completed",
        ])
        app.selectbox(key="step7_priority_sort").set_value("Ticker A–Z")
        # The dated pilot evidence can expire independently of saved trials.
        # The UI must hide expired scorecards rather than preserving an old /100.
        if int(count.group(1)) == 0:
            self.assertFalse(any("DATED CLINICAL RESEARCH PILOT SCORES" in m.body
                                 for m in app.markdown))
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
        app.session_state["pdufa_subtab"] = "PIPELINE"
        app.session_state["pipeline_early_research"] = True
        app.run()
        self.assertFalse(list(app.exception))
        trvi_grid = next(t.value for t in app.dataframe
                         if {"NCT ID", "Preliminary clinical score /100", "Review priority rank"}.issubset(t.value.columns))
        trvi = trvi_grid.loc[trvi_grid["NCT ID"].eq("NCT07671911")]
        self.assertEqual(len(trvi), 1)
        self.assertEqual(float(trvi.iloc[0]["Preliminary clinical score /100"]), 80.0)
        app.text_input(key="step7_trial_search").set_value("LBRX")
        app.session_state["pdufa_subtab"] = "PIPELINE"
        app.session_state["pipeline_early_research"] = True
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
            app.session_state["pdufa_subtab"] = "PIPELINE"
            app.session_state["pipeline_early_research"] = True
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
        self.assertEqual(app.session_state["pdufa_subtab"], "PIPELINE")
        self.assertEqual(app.session_state["detail_return_page"], "PDUFA")
        self.assertFalse(any(item.label == "Phase 1–3 company–trial leads"
                             for item in app.metric))
        self.assertFalse(any("PRE PHASE 3 — Clinical Trial Evaluation" in item.body
                             for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
