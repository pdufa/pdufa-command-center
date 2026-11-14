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
handoff_builder = load("level16_review_handoff", "level16_review_handoff.py")
chronology_builder = load("level16_orca2_statistical_timeline", "level16_orca2_statistical_timeline.py")


def evidence_report():
    sources = [level16.ROSTER_PATH, level16.APPLICATIONS_PATH, level16.DEFINITION_PATH]
    roster, apps, definition = [json.loads(p.read_text(encoding="utf-8")) for p in sources]
    return level16.build(roster, apps, {"results": {}}, definition)


def handoff_report():
    def load_json(path):
        return json.loads(path.read_text(encoding="utf-8"))
    return handoff_builder.build(
        load_json(handoff_builder.COVERAGE),
        load_json(handoff_builder.ROSTER),
        load_json(handoff_builder.APPLICATIONS),
        chronology_builder.assess(load_json(handoff_builder.ORCA2)),
    )


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


    def test_local_byte_receipts_visible_but_never_labeled_authenticated(self):
        report = evidence_report()
        report["localByteConsistency"] = {
            "status": "LOCAL_BYTE_CONSISTENCY_ONLY_NOT_SOURCE_AUTHENTICATION",
            "localByteMatches": 1, "localDigestMismatches": 0,
            "originalSourceAuthenticated": 0, "independentScientificReviews": 0,
        }
        report["trials"][0]["levels"][0]["submittedEvidenceLeads"] = [
            {"sourceKind": "PROTOCOL", "role": "CONTEXT",
             "claim": "Synthetic placeholder, not an assessed protocol",
             "sourceUrl": "https://example.org/synthetic",
             "sourceDate": "2026-11-10",
             "authenticationStatus": "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED",
             "scientificReviewStatus": "NOT_ADJUDICATED",
             "localByteReceipt": {
                 "byteMatchStatus": "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY",
                 "computedSha256": "a" * 64, "bytesRead": 12,
             }},
        ]
        html = renderer.render(report)
        self.assertIn("Local byte consistency", html)
        self.assertIn("LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY", html)
        self.assertIn("NOT original-source authenticated", html)
        self.assertIn("Independently reviewed Levels 1–6", html)
        self.assertIn("NOT ADJUDICATED", html)

        report["localByteConsistency"]["originalSourceAuthenticated"] = 1
        with self.assertRaises(ValueError):
            renderer.render(report)
        report["localByteConsistency"]["originalSourceAuthenticated"] = 0
        report["trials"][0]["levels"][0]["submittedEvidenceLeads"][0][
            "localByteReceipt"]["byteMatchStatus"] = "INDEPENDENTLY_VERIFIED"
        with self.assertRaises(ValueError):
            renderer.render(report)


    def test_review_handoff_visible_for_all_32_focus_trials(self):
        html = renderer.render(evidence_report(), review_handoff=handoff_report())
        self.assertEqual(html.count("Owner-only assessment handoff — OWNER NOT REVIEWED"), 192)
        self.assertIn("Hochberg", html)
        self.assertIn("OWNER NOT REVIEWED", html)
        self.assertIn("Owner review", html)
        self.assertIn("UNRESOLVED", html)
        self.assertIn("OWNER-ONLY RESEARCH — NO EXTERNAL VERIFICATION REQUIRED", html)
        self.assertNotIn("EXTERNAL_APPROVAL_AND_INFRASTRUCTURE_REQUIRED", html)
        self.assertNotIn("TRUSTED_IDENTITY_PROVIDER_REQUIRED", html)

    def test_review_handoff_escapes_untrusted_research_questions(self):
        handoff = handoff_report()
        bad = '<script>alert("x")</script>'
        handoff["trials"][0]["levels"][0]["openReviewQuestions"].append(bad)
        html = renderer.render(evidence_report(), review_handoff=handoff)
        self.assertNotIn(bad, html)
        self.assertIn("&lt;script&gt;", html)

    def test_review_handoff_rejects_forged_signoff_and_probabilities(self):
        original = handoff_report()
        for mutation in (
            lambda h: h.update(independentlyAuthenticatedSources=1),
            lambda h: h.update(independentlyAdjudicatedLevels=1),
            lambda h: h.update(stagingActivated=True),
            lambda h: h["trials"][0].update(actualCompletedLevels=1),
            lambda h: h["trials"][0]["levels"][0].update(score=95),
            lambda h: h["trials"][0]["levels"][0].update(approvalProbability=0.99),
            lambda h: h["trials"][0]["levels"][0].update(
                sourceAuthenticationStatus="INDEPENDENTLY_AUTHENTICATED"),
            lambda h: h["trials"][0]["levels"][0].update(
                independentScientificReviewStatus="APPROVED"),
            lambda h: h["trials"][0]["levels"][0].update(completionPermitted=True),
        ):
            handoff = copy.deepcopy(original)
            mutation(handoff)
            with self.assertRaises(ValueError):
                renderer.render(evidence_report(), review_handoff=handoff)

    def test_review_handoff_rejects_cross_trial_and_mapping_substitution(self):
        handoff = handoff_report()
        handoff["trials"][0]["nct"] = "NCT99999999"
        with self.assertRaises(ValueError):
            renderer.render(evidence_report(), review_handoff=handoff)
        handoff = handoff_report()
        handoff["trials"][0]["ticker"] = "WRONG"
        with self.assertRaises(ValueError):
            renderer.render(evidence_report(), review_handoff=handoff)
        handoff = handoff_report()
        handoff["trials"][0]["applicationMappingStatus"] = "NOT_MAPPED_APPLICATION_CYCLE"
        with self.assertRaises(ValueError):
            renderer.render(evidence_report(), review_handoff=handoff)

    def test_review_handoff_rejects_incomplete_or_invalid_level_questions(self):
        handoff = handoff_report()
        handoff["trials"][0]["levels"].pop()
        with self.assertRaises(ValueError):
            renderer.render(evidence_report(), review_handoff=handoff)
        handoff = handoff_report()
        handoff["trials"][0]["levels"][0]["openReviewQuestions"] = [
            {"reviewComplete": True}
        ]
        with self.assertRaises(ValueError):
            renderer.render(evidence_report(), review_handoff=handoff)


if __name__ == "__main__":
    unittest.main()
