"""Offline company investor-news fallback tests: not a substitute for SEC/FDA."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_issuer_news_fallback as watch

STAMP="2026-11-03T23:59:59Z"


def payload(ticker):
    if ticker=="CYTK":
        return '''<html><body><a href="/press-releases/press-release-details/2026/Cytokinetics-Reports-Third-Quarter/default.aspx">Quarterly results</a><a href="/press-releases/press-release-details/2026/Cytokinetics-Reports-Third-Quarter/default.aspx?ref=tracking">Duplicate</a><a href="https://evil.example/press-release-details/2026/fake">Malicious</a></body></html>'''
    return '''<html><body><a href="/news/press-releases/news-details/2026/Ivonescimab-Update/default.aspx">Update</a><a href="javascript:alert(1)">bad</a></body></html>'''


class IssuerFallbackTests(unittest.TestCase):
    def call(self,payloads=None,statuses=None,details=None,source=None):
        return watch.inspect_report(
            payloads or {"CYTK":payload("CYTK"),"SMMT":payload("SMMT")},
            statuses or {"CYTK":"AVAILABLE","SMMT":"AVAILABLE"},
            details or {"CYTK":None,"SMMT":None},
            STAMP,source)

    def test_official_news_links_are_only_unreviewed_candidates(self):
        result=self.call()
        self.assertEqual(result["officialIssuerNewsPagesAccessible"],2)
        self.assertEqual(result["issuerNewsResearchLinkCandidatesFound"],2)
        self.assertFalse(result["secOfficialFilingsAccessRestoredByFallback"])
        self.assertEqual(result["newCurrentPendingApplicationNumbersIndependentlyVerified"],0)
        self.assertEqual(result["independentlyVerifiedFdaDeadlineRevisions"],0)
        self.assertEqual(result["newThreeWayPredictionsFromIssuerNews"],0)
        for row in result["rows"]:
            self.assertEqual(row["issuerArticleLinksFound"],1)
            self.assertFalse(row["issuerNewsIsComprehensiveSECDisclosureFeed"])
            self.assertFalse(row["issuerArticleLinkCertifiesFdaDeadlineOrApplicationNumber"])
            self.assertFalse(row["sec403FixedByThisIssuerNewsSource"])
            for candidate in row["listedResearchLinkCandidates"]:
                self.assertFalse(candidate["verifiedPublishedAfterLastReviewedGoalSource"])
                self.assertFalse(candidate["articleContentReviewedForPdufaChange"])
                self.assertFalse(candidate["pendingFdaApplicationNumberVerified"])
                self.assertFalse(candidate["officialFdaActionOrExtensionVerified"])

    def test_accessible_html_without_links_is_unknown_not_no_news(self):
        result=self.call(payloads={"CYTK":"<html><body>Some dynamic page</body></html>",
                                   "SMMT":"<html></html>"})
        self.assertEqual(result["officialIssuerNewsPagesAccessible"],2)
        self.assertEqual(result["issuerNewsResearchLinkCandidatesFound"],0)
        for row in result["rows"]:
            self.assertEqual(row["pageParseStatus"],
                             "PAGE_FETCHED_NO_PARSEABLE_ARTICLES_NOT_A_NEGATIVE_RESULT")
            self.assertFalse(row["issuerNewsPageAccessibleButNoArticlesParsedIsNoNews"])

    def test_403_and_404_are_unknown_not_proof_of_no_regulatory_change(self):
        for status in ("SOURCE_UNAVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
                       "MALFORMED_RESPONSE"):
            result=self.call(
                payloads={"CYTK":None,"SMMT":None},
                statuses={"CYTK":status,"SMMT":status})
            self.assertEqual(result["officialIssuerNewsPagesAccessible"],0)
            self.assertEqual(result["issuerNewsResearchLinkCandidatesFound"],0)
            self.assertFalse(result["secOfficialFilingsAccessRestoredByFallback"])
            self.assertEqual(result["newCurrentPendingApplicationNumbersIndependentlyVerified"],0)

    def test_url_host_safety_prevents_fake_issuer_links(self):
        examples=(
            "http://ir.cytokinetics.com/press-releases/press-release-details/2026/x",
            "https://ir.cytokinetics.com.evil.com/press-release-details/2026/x",
            "javascript:alert(1)",
            "https://evil.example/news/press-releases/news-details/2026/x",
            "https://smmttx.com/news/press-releases/news-details/2025/old",
        )
        for u in examples:
            self.assertFalse(watch.is_release_url("CYTK",u))
            self.assertFalse(watch.is_release_url("SMMT",u))

    def test_wrong_source_dossier_cannot_promote_bla_or_extension(self):
        import json
        source=json.loads(watch.SOURCE.read_text("utf-8"))
        for fld,val in (
            ("issuerPublicSourceDate","2026-09-15"),
            ("absenceOfLaterGoalChangeIndependentlyEstablished",True),
            ("fullDatedFDAActionCycleIndependentlyEstablished",True),
        ):
            doc=deepcopy(source)
            next(x for x in doc["records"] if x["ticker"]=="SMMT")[fld]=val
            with self.subTest(fld=fld),self.assertRaises(ValueError):
                self.call(source=doc)


if __name__=="__main__":
    unittest.main()
