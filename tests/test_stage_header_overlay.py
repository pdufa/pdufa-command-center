"""Guard the placement of checkbox filters in both Streamlit and HTML headers."""
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

    def test_prediction_grid_places_checkbox_inside_header(self):
        app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn('sort_button += stage_filter_button', app)
        self.assertIn('class="stage-filter-head"', app)
        self.assertIn('class="stage-choice"', app)
        self.assertIn('const sortStageRows = () =>', app)
        self.assertNotIn('frame = stage_filter_panel(frame, key="merged_stage_"', app)
