"""Real Streamlit regression: active PDUFA views keep the score contract.

Values remain NOT SCORED if no independently supported score exists.
"""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from pdufa_display_columns import (FRONT, POST_SCORES, PRE_SCORES,
                                   DISPLAY_ORDER_OPTIONS)

APP = Path(__file__).resolve().parents[1] / "app.py"
TABS = ("PIPELINE",)


class FourPdufaScoreTabTests(unittest.TestCase):
    def test_every_subtab_exposes_same_scoring_columns(self):
        app = AppTest.from_file(str(APP), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.run()
        self.assertFalse(list(app.exception), "PDUFA startup failed")
        for tab in TABS:
            with self.subTest(tab=tab):
                app.session_state["pdufa_subtab"] = tab
                app.run()
                self.assertFalse(list(app.exception), tab)
                panel = next(item for item in app.get("tab") if item.label == tab)
                main = [
                    item.value for item in panel.get("dataframe")
                    if {"Ticker", "Score /100", "Score type",
                        "PDUFA Date", "Days to PDUFA", "F"}.issubset(item.value.columns)
                ]
                self.assertTrue(main, f"{tab} is missing its PDUFA score table")
                self.assertEqual(main[0].columns[:len(FRONT)].tolist(), list(FRONT))
                self.assertTrue(set(POST_SCORES).issubset(main[0].columns))
                self.assertTrue(set(PRE_SCORES).issubset(main[0].columns))
                self.assertEqual(
                    main[0].columns[:5].tolist(),
                    ["Ticker", "Score /100", "PDUFA Date",
                     "Days to PDUFA", "2nd Financing Completed"],
                )
                sort_key = {
                    "PIPELINE": "pipeline_sort_v9",
                }[tab]
                sorter = app.selectbox(key=sort_key)
                self.assertEqual(list(sorter.options), list(DISPLAY_ORDER_OPTIONS))
                self.assertEqual(sorter.value, "Top Score")
                if len(main[0]):
                    self.assertTrue(
                        main[0]["Score /100"].dropna().is_monotonic_decreasing,
                        f"{tab} default display must sort highest score first",
                    )
                    self.assertTrue(
                        main[0]["Score /100"].dropna().between(0, 100).all(),
                        f"{tab} contains an invalid numeric score",
                    )
                    self.assertTrue(main[0]["Score type"].notna().all())
                    for score, group in main[0].groupby("Score /100", dropna=False, sort=False):
                        self.assertTrue(
                            group["Days to PDUFA"].dropna().is_monotonic_decreasing,
                            f"{tab} equal score {score} must sort days to PDUFA descending",
                        )
                        dated = group["Days to PDUFA"].notna().tolist()
                        self.assertEqual(dated, sorted(dated, reverse=True),
                                         f"{tab} missing PDUFA days must follow dated rows")

    def test_gem_jr_and_gem_keep_distinct_qualification_contract(self):
        app = AppTest.from_file(str(APP), default_timeout=120)
        app.session_state["nav"] = "PDUFA"
        app.session_state["pdufa_subtab"] = "GEM JR + GEM"
        app.run()
        self.assertFalse(list(app.exception))
        panel = next(t for t in app.get("tab") if t.label == "GEM JR + GEM")
        headings = [x.body for x in panel.get("markdown")]
        self.assertTrue(any("GEM JR — RESEARCH & QUALIFICATION QUEUE" in x for x in headings))
        self.assertTrue(any("POTENTIAL GEMs — PENDING RESEARCH" in x for x in headings))
        source = APP.read_text(encoding="utf-8")
        self.assertIn("two distinct SEC-confirmed financing closures", source)
        self.assertIn('key="gem_jr_shared_block"', source)
        self.assertIn('key="gem_shared_block"', source)


if __name__ == "__main__":
    unittest.main()
