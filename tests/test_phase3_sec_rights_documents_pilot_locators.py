"""Research-only SEC document locator and accurate request-denominator tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_sec_rights_documents_pilot import (
    build_report, read_text, rights_review_locators,
)
from test_phase3_sec_rights_documents_pilot import mock_sources


class RightsLocatorCoverageTests(unittest.TestCase):
    def setUp(self):
        self.casebook, self.leads = mock_sources()
        self.requests = []

    def fetch(self, url):
        self.requests.append(url)
        return (b"<html><body>We licensed an unrelated product in the United States. "
                b"The collaboration provides no evidence of rights for this trial. "
                b"Our company terminated the license for a different program.</body></html>")

    def test_identifying_contact_missing_is_not_a_failed_http_request(self):
        report = build_report(self.casebook, self.leads, max_issuers=2, agent="")
        self.assertEqual(report["documents_selected_for_retrieval"], 4)
        self.assertEqual(report["documents_not_attempted_missing_agent"], 4)
        self.assertEqual(report["documents_attempted"], 0)
        self.assertEqual(report["documents_retrieved"], 0)
        self.assertEqual(report["documents_access_failed_or_blocked"], 0)
        self.assertEqual(report["issuers"][0]["review_status"],
                         "NOT_REQUESTED_IDENTIFYING_AGENT_REQUIRED")
        self.assertEqual(report["documents_with_bounded_review_locators"], 0)

    def test_real_attempts_are_counted_separately_from_failed_requests(self):
        def unavailable(url):
            self.requests.append(url)
            raise OSError("source unavailable")
        report = build_report(self.casebook, self.leads, fetch=unavailable, max_issuers=2)
        self.assertEqual(len(self.requests), 4)
        self.assertEqual(report["documents_attempted"], 4)
        self.assertEqual(report["documents_not_attempted_missing_agent"], 0)
        self.assertEqual(report["documents_access_failed_or_blocked"], 4)
        self.assertEqual(report["documents_retrieved"], 0)
        self.assertEqual(report["issuers"][0]["review_status"],
                         "DOCUMENT_REQUESTS_FAILED_OR_BLOCKED")

    def test_source_hashed_text_locators_are_only_review_leads(self):
        report = build_report(self.casebook, self.leads, fetch=self.fetch, max_issuers=1)
        self.assertEqual(report["documents_attempted"], 2)
        self.assertEqual(report["documents_retrieved"], 2)
        self.assertEqual(report["documents_with_bounded_review_locators"], 2)
        self.assertEqual(report["independently_verified_current_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        issuer = report["issuers"][0]
        self.assertEqual(issuer["review_status"], "SOURCE_TEXT_AVAILABLE_REVIEW_REQUIRED")
        for document in issuer["documents"]:
            self.assertFalse(document["verified_trial_development_rights"])
            self.assertRegex(document["source_sha256"], r"^[a-f0-9]{64}$")
            locators = document["rights_language_review_locators"]
            self.assertGreater(len(locators), 0)
            self.assertLessEqual(len(locators), 6)
            self.assertIn("LICENSE_OR_EXCLUSIVITY", {x["topic"] for x in locators})
            for item in locators:
                self.assertEqual(item["status"], "LEXICAL_REVIEW_LEAD_NOT_LEGAL_RIGHTS_PROOF")
                self.assertLessEqual(len(item["context_excerpt"]), 150)
                self.assertGreaterEqual(item["normalized_text_offset"], 0)

    def test_rights_locators_no_implication_for_unrelated_drug(self):
        locators = rights_review_locators(
            "The company holds a license for an unrelated product in the United States."
        )
        self.assertGreater(len(locators), 0)
        self.assertTrue(all(x["status"] == "LEXICAL_REVIEW_LEAD_NOT_LEGAL_RIGHTS_PROOF"
                            for x in locators))

    def test_html_script_keyword_cannot_create_false_rights_locator(self):
        text = read_text(b"<html><script>license</script><style>exclusive rights</style>"
                         b"<body>Ordinary financial disclosure</body></html>")
        self.assertEqual(rights_review_locators(text), [])

    def test_denial_page_is_not_treated_as_primary_evidence(self):
        report = build_report(self.casebook, self.leads, fetch=lambda url: b"<html>Access Denied</html>",
                              max_issuers=1)
        self.assertEqual(report["documents_attempted"], 2)
        self.assertEqual(report["documents_retrieved"], 0)
        self.assertEqual(report["documents_access_failed_or_blocked"], 2)
        self.assertEqual(report["documents_with_bounded_review_locators"], 0)

    def test_bounded_output_even_if_filing_mentions_license_many_times(self):
        locators = rights_review_locators(("license for unrelated program " * 10000))
        self.assertLessEqual(len(locators), 6)
        self.assertTrue(all(len(x["context_excerpt"]) <= 150 for x in locators))

    def test_malformed_plain_text_rejected(self):
        for value in (None, b"license", "license " * 1_200_000):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    rights_review_locators(value)


if __name__ == "__main__":
    unittest.main()
