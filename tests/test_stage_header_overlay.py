"""Guard the placement of checkbox filters in both Streamlit and HTML headers."""
from supported_dashboard_checks import run_frontend_contract
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from stage_header_overlay import _SCRIPT, position_stage_filter


class HeaderOverlayTests(TestCase):
    def test_streamlit_stage_button_is_repositioned_into_grid_header(self):
        with patch("stage_header_overlay.st.html") as output:
            position_stage_filter("stageheader_test", 216)
        script = output.call_args.args[0]
        self.assertTrue(output.call_args.kwargs["unsafe_allow_javascript"])
        self.assertIn('const marker = "stageheader_test";', script)
        self.assertIn("const stageOffset = 216;", script)
        self.assertIn("anchor.style.position = 'fixed'", script)
        self.assertIn('gridSelector', script)
        self.assertNotIn("__MARKER__", script)
        self.assertNotIn("__STAGE_OFFSET__", script)

    def test_stage_popup_tracks_scroll_and_cleans_up(self):
        self.assertIn("MutationObserver", _SCRIPT)
        self.assertIn("horizontalScroll", _SCRIPT)
        self.assertIn("observer.disconnect()", _SCRIPT)

    def test_supported_filter_checkboxes_are_accessible_and_do_not_invent_wt_overlays(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('trial-filters.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('wt-chart-checkbox-map.test.cjs'), 0)
