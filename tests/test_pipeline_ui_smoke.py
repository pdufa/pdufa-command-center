"""Exercise the real Streamlit Pipeline page, not only the filter helpers."""
import unittest

from streamlit.testing.v1 import AppTest


class PipelinePageSmokeTests(unittest.TestCase):
    def test_pipeline_opens_with_both_selectors_and_empty_chart(self):
        app = AppTest.from_file("app.py", default_timeout=120)
        app.session_state["nav"] = "PIPELINE"
        app.run(timeout=120)

        exceptions = [str(error.message) for error in app.exception]
        self.assertFalse(exceptions, f"Streamlit render exceptions: {exceptions}")
        selectors = {item.label: item for item in app.multiselect}
        self.assertIn("STAGES", selectors)
        self.assertIn("DATES", selectors)
        self.assertEqual(selectors["STAGES"].value, [])
        self.assertEqual(selectors["DATES"].value, [])
        self.assertTrue(
            any("PIPELINE TRIALS / PROGRAMS" in item.body for item in app.markdown),
            "Bottom chart title was not rendered",
        )
        self.assertTrue(len(app.dataframe), "Bottom chart frame was not rendered")
        metric = [item for item in app.metric
                  if item.label == "Trials / programs displayed"]
        self.assertEqual(len(metric), 1)
        self.assertEqual(str(metric[0].value), "0")

        # Stage selection alone must never populate results or hide DATES.
        selectors["STAGES"].set_value(["PDUFA Decision"]).run(timeout=120)
        self.assertFalse(list(app.exception))
        selectors_after = {item.label: item for item in app.multiselect}
        self.assertIn("DATES", selectors_after)
        self.assertEqual(selectors_after["DATES"].value, [])
        metric_after = [item for item in app.metric
                        if item.label == "Trials / programs displayed"]
        self.assertEqual(str(metric_after[0].value), "0")


if __name__ == "__main__":
    unittest.main()
