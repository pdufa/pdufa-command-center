"""Offline SEC recent-filing screening for source-review leads only."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_sec_nov14_filing_watch as watch

ASOF="2026-11-03T23:59:59Z"


def company(ticker,events=()):
    cik=int(watch.CASES[ticker][0])
    rows=list(events)
    return {
        "cik":cik,"tickers":[ticker],"name":ticker+" ISSUER",
        "filings":{"recent":{
            "form":[x[0] for x in rows],
            "filingDate":[x[1] for x in rows],
            "accessionNumber":[x[2] for x in rows],
            "primaryDocument":[x[3] for x in rows]}}}


def both(cy=None,sm=None):
    return {
        "CYTK":cy if cy is not None else company("CYTK"),
        "SMMT":sm if sm is not None else company("SMMT")}


class SecGoalSourceFreshnessTests(unittest.TestCase):
    def call(self,files=None,status=None,details=None,asof=ASOF,dossier=None):
        filings=both() if files is None else files
        status={"CYTK":"AVAILABLE","SMMT":"AVAILABLE"} if status is None else status
        details={"CYTK":None,"SMMT":None} if details is None else details
        return watch.inspect_watch(filings,status,details,asof,dossier)

    def test_provenance_and_form_filter_only_source_review(self):
        rows=(
            ("10-Q","2026-08-06","0001193125-26-338217","cytk-20260630.htm"),
            ("8-K","2026-10-31","0001193125-26-450001","q3.htm"),
            ("4","2026-11-01","0001193125-26-450002","insider.xml"),
            ("10-Q","2026-11-04","0001193125-26-450003","future.htm"),
        )
        summit=(
            ("8-K","2026-09-15","0001599298-26-000081","a2026_prx0915xharmoniltf.htm"),
            ("8-K/A","2026-10-22","0001599298-26-000111","followup.htm"),
        )
        r=self.call(both(company("CYTK",rows),company("SMMT",summit)))
        self.assertEqual(r["monitoredIssuerFamilies"],2)
        self.assertEqual(r["sourceAvailableCount"],2)
        self.assertEqual(r["sourceCoverageStatus"],"TWO_ISSUER_SOURCES_AVAILABLE")
        self.assertEqual(r["issuerFamiliesWithNewerFilings"],2)
        self.assertEqual(r["potentialNewFilingReviewCandidates"],2)
        a,b=r["rows"]
        self.assertEqual(a["lastSelectedGoalSourceDate"],"2026-08-06")
        self.assertEqual(b["lastSelectedGoalSourceDate"],"2026-09-15")
        self.assertEqual(a["newerRelevantFormFilingCount"],1)
        self.assertEqual(b["newerRelevantFormFilingCount"],1)
        self.assertIn("/1061983/000119312526450001/q3.htm",
                      a["newerFilingReviewCandidates"][0]["documentUrl"])
        self.assertIn("/1599298/000159929826000111/followup.htm",
                      b["newerFilingReviewCandidates"][0]["documentUrl"])
        self.assertFalse(a["newFilingAutomaticallyMeansPdufaChange"])
        self.assertFalse(b["absenceOfNewFilingProvesNoFDAExtension"])
        self.assertFalse(r["rows"][0]["certifiedFDADeadlineRevision"])
        self.assertEqual(r["independentlyVerifiedCurrentFDAApplicationCycles"],0)
        self.assertEqual(r["newThreeWayForecastsFromFilings"],0)

    def test_source_failures_never_mean_no_fda_extension(self):
        for status in ("SOURCE_UNAVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
                       "MALFORMED_RESPONSE"):
            p={"CYTK":None,"SMMT":None}
            s={"CYTK":status,"SMMT":status}
            r=self.call(p,s)
            self.assertEqual(r["sourceAvailableCount"],0)
            self.assertEqual(r["sourceCoverageStatus"],
                             "ISSUER_SOURCES_UNAVAILABLE_NOT_ZERO_NEW_FILINGS")
            self.assertEqual(r["potentialNewFilingReviewCandidates"],0)
            self.assertTrue(all(x["absenceOfNewFilingProvesNoFDAExtension"] is False
                                for x in r["rows"]))
        with self.assertRaises(ValueError):
            self.call(both(),{"CYTK":"MALFORMED_RESPONSE","SMMT":"AVAILABLE"})

    def test_future_filing_is_not_available_as_of_earlier_date(self):
        cy=company("CYTK",[
            ("8-K","2026-10-01","0001193125-26-450001","x.htm")])
        r=self.call(both(cy,company("SMMT")),asof="2026-09-30T23:59:59Z")
        self.assertEqual(r["rows"][0]["newerRelevantFormFilingCount"],0)
        r=self.call(both(cy,company("SMMT")),asof="2026-10-02T23:59:59Z")
        self.assertEqual(r["rows"][0]["newerRelevantFormFilingCount"],1)

    def test_issuer_cik_wrong_ticker_and_misaligned_columns_fail(self):
        p=both()
        p["CYTK"]["cik"]=999999
        with self.assertRaisesRegex(ValueError,"CIK_TICKER"):
            self.call(p)
        p=both()
        p["SMMT"]["tickers"]=["ANOTHER"]
        with self.assertRaisesRegex(ValueError,"CIK_TICKER"):
            self.call(p)
        p=both()
        p["CYTK"]["filings"]["recent"]["primaryDocument"].append("extra.htm")
        with self.assertRaisesRegex(ValueError,"COLUMNS_MISALIGNED"):
            self.call(p)

    def test_unsafe_edgar_url_and_duplicates_fail(self):
        for document in ("../x.htm","../../file","foo/bar.htm","a?query.htm"):
            p=both(company("CYTK",[
                ("8-K","2026-11-01","0001193125-26-450001",document)]),
                company("SMMT"))
            with self.subTest(document=document),self.assertRaisesRegex(
                    ValueError,"UNSAFE_EDGAR_FILING_PATH"):
                self.call(p)
        repeated=("8-K","2026-10-01","0001193125-26-450001","x.htm")
        p=both(company("CYTK",[repeated,repeated]),company("SMMT"))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_FILING_ACCESSION"):
            self.call(p)

    def test_issuer_latest_source_is_not_fda_certification(self):
        import json
        d=json.loads(watch.DOSSIER.read_text("utf-8"))
        for key,value in (
            ("absenceOfLaterGoalChangeIndependentlyEstablished",True),
            ("fullDatedFDAActionCycleIndependentlyEstablished",True),
            ("reportedGoalDate","2026-12-14")):
            alt=deepcopy(d)
            next(x for x in alt["records"] if x["ticker"]=="SMMT")[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):
                self.call(dossier=alt)

    def test_no_filing_still_does_not_prove_no_new_deadline(self):
        r=self.call()
        self.assertEqual(r["sourceAvailableCount"],2)
        self.assertEqual(r["potentialNewFilingReviewCandidates"],0)
        self.assertFalse(r["rows"][0]["absenceOfNewFilingProvesNoFDAExtension"])
        self.assertFalse(r["rows"][1]["absenceOfNewFilingProvesNoFDAExtension"])


if __name__=="__main__":
    unittest.main()
