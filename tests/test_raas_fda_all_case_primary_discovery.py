"""Tests for all-case FDA public product discovery; no network or FDA approval."""
import json
import unittest
from datetime import datetime, timezone

from scripts.raas_fda_all_case_primary_discovery import (
    SCOPE, SEARCH_TERMS, source_query, retrieve_public, parse_public_ingredient,
    assemble_discovery, validate_saved_worklist, observed_at,
)

UTC = "2026-11-05T16:00:00Z"
SIG = "a" * 64


def row(ticker, i):
    return {
        "caseKey": f"{ticker}-CASE-{i}",
        "ticker": ticker,
        "sourceFingerprint": SIG,
        "originalFirstGoalDate": "2026-11-30",
        "listedTargetDate": "2026-11-30",
        "phase3SourceEligibility": "NOT_YET_VERIFIED",
        "decision": "ABSTAIN",
        "independentlyAdjudicatedOutcome": None,
        "verifiedPredecisionForecast": None,
    }


def worklist():
    tickers = [
        "COGT", "COGT", "COGT", "CYTK", "SMMT", "CAPR",
        "BBIO", "VRTX", "ANAB", "CORT", "MLYS",
    ]
    return {
        "schemaVersion": 1,
        "scope": "RAAS_NIGHTLY_FDA_THREE_WAY_EVIDENCE_READINESS_RESEARCH_ONLY",
        "runAtUtc": "2026-11-05T15:00:00Z",
        "auditStateFingerprint": "b" * 64,
        "records": [row(t, i) for i, t in enumerate(tickers)],
    }


def payload(ingredient, sponsor="COGENT BIOSCIENCES", application="NDA123456",
            submission_date="20261103"):
    return {
        "meta": {"results": {"total": 1}},
        "results": [
            {
                "application_number": application,
                "sponsor_name": sponsor,
                "products": [{
                    "brand_name": "TEST RESEARCH PRODUCT",
                    "active_ingredients": [{"name": ingredient}],
                }],
                "submissions": [{
                    "submission_type": "ORIG",
                    "submission_number": "1",
                    "submission_status": "AP",
                    "submission_status_date": submission_date,
                }],
            },
        ],
    }


class RaasAllCaseFdaDiscoveryTests(unittest.TestCase):
    def test_all_eleven_case_roster_searches_nine_ingredient_names(self):
        items = validate_saved_worklist(worklist(), UTC[:10])
        self.assertEqual(len(items), 11)
        self.assertEqual(len(SEARCH_TERMS), 9)
        urls = {source_query(SEARCH_TERMS[r["ticker"]][0]) for r in items}
        self.assertEqual(len(urls), 9)
        self.assertTrue(all("api.fda.gov/drug/drugsfda.json" in u for u in urls))
        with self.assertRaisesRegex(ValueError, "UNAPPROVED_FDA_QUERY"):
            source_query('FOO\"&limit=1000')

    def test_openfda_public_data_is_unverified_even_for_perfect_match(self):
        result = parse_public_ingredient(
            payload("BEZUCLASTINIB"), "AVAILABLE", "BEZUCLASTINIB", UTC)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(len(result["publicCandidates"]), 1)
        candidate = result["publicCandidates"][0]
        self.assertEqual(candidate["publiclyIndexedApplicationNumber"], "NDA123456")
        self.assertEqual(candidate["latestPubliclyIndexedSubmissionStatusDate"],
                         "2026-11-03")
        self.assertIs(candidate["specificOriginalGoalReviewCycleVerified"], False)
        self.assertIs(candidate["currentApprovalCrlOrExtensionVerified"], False)
        self.assertIs(result["independentlyVerifiedFdaOriginalGoalOutcome"], False)

    def test_fuzzy_ingredient_and_other_issuer_do_not_establish_case_identity(self):
        bad = payload("NOT-BEZUCLASTINIB", sponsor="OTHER COMPANY")
        parsed = parse_public_ingredient(bad, "AVAILABLE", "BEZUCLASTINIB", UTC)
        self.assertEqual(parsed["publicCandidates"], [])
        self.assertEqual(parsed["resultCount"], 1)
        report = worklist()
        observed = {
            key: (payload(key, sponsor="OTHER COMPANY"), "AVAILABLE", None)
            for key in {v[0] for v in SEARCH_TERMS.values()}
        }
        out = assemble_discovery(report, UTC, observed)
        self.assertEqual(out["savedResearchCaseCount"], 11)
        self.assertEqual(out["apiProductQueriesMade"], 9)
        self.assertEqual(len(out["records"]), 11)
        self.assertEqual(out["independentlyCertifiedPendingReviewCycles"], 0)
        self.assertEqual(out["independentlyAdjudicatedOriginalGoalFdaOutcomes"], 0)
        self.assertEqual(out["independentlyAuthenticatedProspectiveForecasts"], 0)
        self.assertEqual(out["autoTradingSignals"], 0)
        cogt = [x for x in out["records"] if x["ticker"] == "COGT"]
        self.assertEqual(len(cogt), 3)
        self.assertEqual(len({r["queryUrl"] for r in cogt}), 1)
        self.assertTrue(all(r["matchingPublishedApplicationLeads"][0][
            "sponsorNameStringMentionsExpectedClinicalSponsor"] is False for r in cogt))
        self.assertTrue(all(r["exactFDAApplicationAndReviewCycleIndependentlyCertified"]
                            is False for r in out["records"]))

    def test_prior_fda_supplement_must_not_convert_to_new_efficiency_action(self):
        r = parse_public_ingredient(
            payload("AFICAMTEN", sponsor="CYTOKINETICS", application="NDA219083",
                    submission_date="20260205"),
            "AVAILABLE", "AFICAMTEN", UTC)
        self.assertEqual(r["publicCandidates"][0]["publiclyIndexedApplicationNumber"],
                         "NDA219083")
        self.assertIs(r["publicCandidates"][0]["currentApprovalCrlOrExtensionVerified"],
                      False)
        self.assertIs(r["publicCandidates"][0]["specificOriginalGoalReviewCycleVerified"],
                      False)

    def test_no_indexed_results_or_source_error_never_means_no_pending_fda_application(self):
        for state in ["HTTP_404_NO_PUBLIC_MATCH", "SOURCE_UNAVAILABLE",
                      "MALFORMED_RESPONSE"]:
            r = parse_public_ingredient(None, state, "BEZUCLASTINIB", UTC)
            self.assertEqual(r["status"], state)
            self.assertIs(r["noPublicMatchMeansNoPendingApplication"], False)
            self.assertEqual(r["publicCandidates"], [])

    def test_future_submissions_are_filtered_without_changing_source_scope(self):
        r = parse_public_ingredient(payload("BEZUCLASTINIB",
            submission_date="20271215"), "AVAILABLE", "BEZUCLASTINIB", UTC)
        self.assertIsNone(r["publicCandidates"][0][
            "latestPubliclyIndexedSubmissionStatusDate"])
        self.assertEqual(r["status"], "AVAILABLE")

    def test_malformed_and_truncated_public_responses_do_not_certify_anything(self):
        with self.assertRaisesRegex(ValueError, "FDA_RESPONSE_SCHEMA"):
            parse_public_ingredient({"results": {}}, "AVAILABLE", "BEZUCLASTINIB", UTC)
        with self.assertRaisesRegex(ValueError, "SOURCE_STATUS_PAYLOAD_CONTRADICTION"):
            parse_public_ingredient({"results": []}, "HTTP_404_NO_PUBLIC_MATCH",
                                    "BEZUCLASTINIB", UTC)
        p = payload("BEZUCLASTINIB")
        p["meta"]["results"]["total"] = 100
        x = parse_public_ingredient(p, "AVAILABLE", "BEZUCLASTINIB", UTC)
        self.assertIs(x["publicTotalMayBeTruncated"], True)
        self.assertIs(x["independentlyVerifiedCurrentFdaReviewCycle"], False)

    def test_exact_research_case_identity_and_input_asof_must_be_stable(self):
        data = worklist()
        data["records"][1]["caseKey"] = data["records"][0]["caseKey"]
        with self.assertRaisesRegex(ValueError, "RESEARCH_CASE_DUPLICATE"):
            validate_saved_worklist(data, UTC[:10])
        data = worklist()
        data["records"][0]["decision"] = "PASS"
        with self.assertRaisesRegex(ValueError, "NOT_A_SAFE"):
            validate_saved_worklist(data, UTC[:10])
        data = worklist()
        data["runAtUtc"] = "2026-11-08T15:00:00Z"
        with self.assertRaisesRegex(ValueError, "WORKLIST_ASOF_AFTER_RETRIEVAL"):
            validate_saved_worklist(data, UTC[:10])
        with self.assertRaisesRegex(ValueError, "TIME_REQUIRED_UTC"):
            observed_at("2026-11-05T16:00:00")

    def test_query_set_must_cover_all_ingredients_exactly(self):
        observed = {
            key: (None, "HTTP_404_NO_PUBLIC_MATCH", None)
            for key in {v[0] for v in SEARCH_TERMS.values()}
        }
        del observed["AFICAMTEN"]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_INGREDIENT_QUERY_SET"):
            assemble_discovery(worklist(), UTC, observed)

    def test_explicit_source_status_for_live_network_errors_is_nonfatal(self):
        from unittest.mock import patch
        import urllib.error
        for status_code, expected in [(404, "HTTP_404_NO_PUBLIC_MATCH"),
                                      (429, "SOURCE_UNAVAILABLE")]:
            fake_error = urllib.error.HTTPError(
                source_query("BEZUCLASTINIB"), status_code,
                "test", {}, None)
            with patch("urllib.request.urlopen", side_effect=fake_error):
                payload_data, status, _ = retrieve_public(
                    source_query("BEZUCLASTINIB"))
            self.assertIsNone(payload_data)
            self.assertEqual(status, expected)


if __name__ == "__main__":
    unittest.main()
