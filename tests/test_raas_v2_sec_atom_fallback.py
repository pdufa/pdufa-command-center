"""SEC company Atom feed alternative: independent official route, not FDA evidence."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_sec_nov14_filing_watch as watch

ASOF="2026-11-03T23:59:59Z"
ATOM="http://www.w3.org/2005/Atom"


def feed(ticker,entries=()):
    body=""
    for form,date,cik,number in entries:
        body+=(
            '<entry><title>'+form+' - '+ticker+' (test)</title>'
            '<category term="'+form+'"/>'
            '<updated>'+date+'T15:20:00-04:00</updated>'
            '<link rel="alternate" href="https://www.sec.gov/Archives/edgar/data/'
            +str(cik)+"/"+number+"/"+number+"-index.htm"+'"/></entry>')
    return '<feed xmlns="'+ATOM+'"><title>Company Filings</title>'+body+'</feed>'


def unavailable():
    return {"CYTK":None,"SMMT":None}, {
        "CYTK":"SOURCE_UNAVAILABLE","SMMT":"SOURCE_UNAVAILABLE"}, {
        "CYTK":"SEC 403","SMMT":"SEC 403"}


class OfficialSecAtomTests(unittest.TestCase):
    def test_feed_url_is_sec_official_and_cik_scoped(self):
        self.assertIn("www.sec.gov/cgi-bin/browse-edgar?",
                      watch.official_atom_url("CYTK"))
        self.assertIn("CIK=0001061983",watch.official_atom_url("CYTK"))
        self.assertIn("CIK=0001599298",watch.official_atom_url("SMMT"))
        self.assertIn("output=atom",watch.official_atom_url("SMMT"))
        with self.assertRaises(ValueError):
            watch.official_atom_url("FAKE")

    def test_sec_atom_reveals_official_filing_leads_when_json_403(self):
        atom={"CYTK":feed("CYTK",[
            ("8-K","2026-10-27","1061983","000119312526450001"),
            ("4","2026-11-01","1061983","000119312526450002"),
            ("10-Q","2026-11-04","1061983","000119312526450003")]),
            "SMMT":feed("SMMT",[
            ("10-Q","2026-10-26","1599298","000159929826000121")])}
        jp,js,jd=unavailable()
        result=watch.inspect_watch(jp,js,jd,ASOF,
            atom_payloads=atom,
            atom_statuses={"CYTK":"AVAILABLE","SMMT":"AVAILABLE"},
            atom_details={"CYTK":None,"SMMT":None})
        self.assertEqual(result["sourceAvailableCount"],0)
        self.assertEqual(result["sourceCoverageStatus"],
                         "ISSUER_SOURCES_UNAVAILABLE_NOT_ZERO_NEW_FILINGS")
        self.assertEqual(result["alternativeOfficialSecAtomAvailableCount"],2)
        self.assertEqual(result["effectiveOfficialSecFilingSourceCoverageCount"],2)
        self.assertEqual(result["officialSecAtomResearchFilingCandidateCount"],2)
        for x in result["rows"]:
            a=x["alternativeOfficialSecAtomFeed"]
            self.assertEqual(a["sourceStatus"],"AVAILABLE")
            self.assertEqual(a["newerRelevantFormFilingCount"],1)
            self.assertFalse(a["atomFeedAloneVerifiesCompleteIssuerSECFileHistory"])
            self.assertFalse(a["absenceFromAtomFeedProvesNoFdaDeadlineChange"])
            self.assertFalse(a["aFilingLinkIdentifiesCurrentPendingBlaOrSNda"])
            lead=a["newerFilingReviewCandidates"][0]
            self.assertFalse(lead["fdaDeadlineRevisionConfirmed"])
            self.assertFalse(lead["pendingFdaApplicationNumberConfirmed"])
            self.assertFalse(lead["fdaActionOrPredictionConfirmed"])
        self.assertEqual(result["independentlyVerifiedNoFurtherFDAExtensions"],0)
        self.assertEqual(result["newThreeWayForecastsFromFilings"],0)

    def test_wrong_cik_link_and_unsupported_xml_are_not_verified(self):
        date="2026-11-01"
        cases=(
            feed("CYTK",[("8-K",date,"1599298","000119312526450001")]),
            "<notatom></notatom>",
            "<feed xmlns='"+ATOM+"'><entry><category term='8-K'/></entry></feed>",
            "<feed xmlns='"+ATOM+"'><entry><category term='8-K'/><updated>2026-11-01T15:00:00Z</updated><link href='https://evil.test/Archives/edgar/data/1061983/000119312526450001/a-index.htm'/></entry></feed>",
            "<feed xmlns='"+ATOM+"'><entry>",
        )
        for xml in cases:
            with self.subTest(xml=xml[:45]),self.assertRaises(ValueError):
                watch.inspect_atom_company("CYTK",xml,"AVAILABLE",None,
                                           watch.parse_clock(ASOF))
        with self.assertRaises(ValueError):
            watch.inspect_atom_company("CYTK","<feed/>","SOURCE_UNAVAILABLE",
                                       "403",watch.parse_clock(ASOF))

    def test_not_queried_and_unavailable_never_mean_no_new_company_filings(self):
        jp,js,jd=unavailable()
        result=watch.inspect_watch(jp,js,jd,ASOF,
            atom_payloads={"CYTK":None,"SMMT":None},
            atom_statuses={"CYTK":"SOURCE_UNAVAILABLE","SMMT":"HTTP_404_NO_PUBLIC_RECORD"},
            atom_details={"CYTK":"403","SMMT":"404"})
        self.assertEqual(result["alternativeOfficialSecAtomAvailableCount"],0)
        self.assertEqual(result["effectiveOfficialSecFilingSourceCoverageCount"],0)
        self.assertEqual(result["officialSecAtomResearchFilingCandidateCount"],0)
        self.assertTrue(all(x["alternativeOfficialSecAtomFeed"][
            "absenceFromAtomFeedProvesNoFdaDeadlineChange"] is False
            for x in result["rows"]))
        self.assertFalse(result["rows"][0]["absenceOfNewFilingProvesNoFDAExtension"])
        default=watch.inspect_watch(jp,js,jd,ASOF)
        self.assertEqual(default["rows"][0]["alternativeOfficialSecAtomFeed"][
            "sourceStatus"],"NOT_QUERIED")

    def test_filing_dates_are_not_retrospectively_promoted(self):
        xml=feed("CYTK",[
            ("8-K","2026-08-06","1061983","000119312526400001"),
            ("8-K","2026-08-07","1061983","000119312526400002"),
            ("8-K","2026-11-04","1061983","000119312526400003")])
        r=watch.inspect_atom_company(
            "CYTK",xml,"AVAILABLE",None,watch.parse_clock(ASOF))
        self.assertEqual(r["newerRelevantFormFilingCount"],1)
        self.assertEqual(r["newerFilingReviewCandidates"][0]["filedDate"],
                         "2026-08-07")


if __name__=="__main__":
    unittest.main()
