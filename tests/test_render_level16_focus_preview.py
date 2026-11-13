"""Validate read-only, escaped FOCUS Levels 1–6 assessment preview."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/medical" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load("render_level16_focus_preview", "render_level16_focus_preview.py")
level16 = load("phase_first_levels_1_6", "phase_first_levels_1_6.py")


def evidence_report():
    sources = [level16.ROSTER_PATH, level16.APPLICATIONS_PATH, level16.DEFINITION_PATH]
    roster, apps, definition = [json.loads(p.read_text(encoding="utf-8")) for p in sources]
    return level16.build(roster, apps, {"results": {}}, definition)


class PreviewTests(unittest.TestCase):
    def test_preview_preserves_current_32_trials_and_six_levels(self):
        report = evidence_report()
        html = renderer.render(report)
        self.assertEqual(html.count("<details>"), 32)
        self.assertIn("Scientific Levels 1–6", html)
        self.assertIn("NOT MEDICAL ASSESSMENTS OR FDA FORECASTS", html)
        self.assertIn("NOT ADJUDICATED", html)
        self.assertIn("Source submissions awaiting authentication", html)
        self.assertIn("Provisional application cycles", html)
        self.assertIn("Trials without application mapping", html)
        self.assertNotIn("approved forecast", html.lower())

    def test_untrusted_fields_escape_html_and_links_are_safe(self):
        report = evidence_report()
        bad = "<script>alert(7)</script>"
        report["trials"][0]["ticker"] = bad
        level = report["trials"][0]["levels"][0]
        level["submittedEvidenceLeads"] = [
            {"sourceKind": "REGISTRY", "role": "CONTEXT", "claim": bad,
             "sourceUrl": "javascript:alert(1)", "sourceDate": "2026-11-01",
             "authenticationStatus": "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED",
             "scientificReviewStatus": "NOT_ADJUDICATED"}
        ]
        html = renderer.render(report)
        self.assertNotIn(bad, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("Source locator withheld", html)

    def test_pending_source_url_is_visible_as_an_unverified_link(self):
        report = evidence_report()
        report["trials"][0]["levels"][0]["submittedEvidenceLeads"] = [
            {"sourceKind": "REGISTRY", "role": "CONTEXT", "claim": "Registry field source lead",
             "sourceUrl": "https://clinicaltrials.gov/study/" + report["trials"][0]["nct"],
             "sourceDate": "2026-11-10",
             "authenticationStatus": "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED",
             "scientificReviewStatus": "NOT_ADJUDICATED"}
        ]
        html = renderer.render(report)
        self.assertIn("View submitted source", html)
        self.assertIn('rel="noopener noreferrer"', html)

    def test_rejects_pretend_assessments_and_fda_predictions(self):
        original = evidence_report()
        for change in (
            lambda r: r["trials"][0]["levels"][0].update(scientificReviewStatus="REVIEWED"),
            lambda r: r["trials"][0]["levels"][0].update(assessmentCompleted=True),
            lambda r: r["trials"][0]["levels"][0].update(score=90),
            lambda r: r["trials"][0].update(fdaOutcomeJudgment="APPROVAL"),
            lambda r: r.update(status="PREDICTION_COMPLETE"),
        ):
            report = copy.deepcopy(original)
            change(report)
            with self.assertRaises(ValueError):
                renderer.render(report)

    def test_rejects_invalid_roster_and_promoted_source_review(self):
        report = evidence_report()
        report["trials"] = report["trials"][:28]
        with self.assertRaises(ValueError):
            renderer.render(report)
        report = evidence_report()
        report["trials"][0]["levels"][0]["submittedEvidenceLeads"] = [
            {"authenticationStatus": "INDEPENDENTLY_VERIFIED",
             "scientificReviewStatus": "NOT_ADJUDICATED"}
        ]
        with self.assertRaises(ValueError):
            renderer.render(report)


if __name__ == "__main__":
    unittest.main()
