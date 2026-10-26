import unittest
from unittest.mock import MagicMock
from outcome_fda_readiness_streamlit import render_outcome_readiness

class StreamlitReadinessRendererTests(unittest.TestCase):
    def test_renders_collapsed_blockers_without_enabling_prediction(self):
        st = MagicMock()
        a, b, c = MagicMock(), MagicMock(), MagicMock()
        st.columns.return_value = (a, b, c)
        payload = render_outcome_readiness(st)
        st.subheader.assert_called_once()
        a.metric.assert_called_once_with("Evidence documented", "85.0%")
        b.metric.assert_called_once_with("FDA timelines", "17/20")
        c.metric.assert_called_once_with("Prediction", "NOT_READY")
        st.expander.assert_called_once_with(
            "Why prediction is not ready (5)", expanded=False)
        self.assertEqual(st.write.call_count, 5)
        st.warning.assert_called_once()
        self.assertFalse(payload["primary"]["prediction_ready"])
        self.assertIsNone(payload["primary"]["prediction_probability"])
