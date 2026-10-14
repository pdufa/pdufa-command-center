"""SEC Form 4 insider evidence must never invent recent open-market buys."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_insider import FILE, STATUS, REVIEW, assess, load_records
from scripts.collect_gem_insider_form4 import (
    parse_form4, filings_for_issuer, xml_for_filing, collect
)

ASOF = date(2026, 10, 13)
CIK = "0000000123"


def form4_xml(code="P", direction="A", amount="1000", price="10.5",
              issuer="123", title="Common Stock", root="ownershipDocument"):
    return f"""<{root}>
    <documentType>4</documentType>
    <issuer><issuerCik>{issuer}</issuerCik><issuerTradingSymbol>TEST</issuerTradingSymbol></issuer>
    <reportingOwner><reportingOwnerId>
      <rptOwnerCik>444</rptOwnerCik><rptOwnerName>Jane Example</rptOwnerName>
    </reportingOwnerId></reportingOwner>
    <nonDerivativeTable><nonDerivativeTransaction>
       <securityTitle><value>{title}</value></securityTitle>
       <transactionDate><value>2026-10-06</value></transactionDate>
       <transactionCoding><transactionCode>{code}</transactionCode></transactionCoding>
       <transactionAmounts>
         <transactionShares><value>{amount}</value></transactionShares>
         <transactionPricePerShare><value>{price}</value></transactionPricePerShare>
         <transactionAcquiredDisposedCode><value>{direction}</value>
         </transactionAcquiredDisposedCode>
       </transactionAmounts>
    </nonDerivativeTransaction></nonDerivativeTable>
    </{root}>""".encode()


class Form4EvidenceTests(unittest.TestCase):
    def parse(self, xml):
        return parse_form4(xml, ticker="TEST", issuer_cik=CIK,
                           filed="2026-10-07", as_of=ASOF,
                           source="https://www.sec.gov/Archives/edgar/data/123/000000000001234/owned.xml")

    def test_actual_qualifying_purchased_and_sold_common_stock(self):
        buy=self.parse(form4_xml())
        sale=self.parse(form4_xml(code="S",direction="D"))
        self.assertEqual(buy[0]["code"],"P")
        self.assertEqual(buy[0]["shares"],1000)
        self.assertEqual(sale[0]["code"],"S")
        self.assertEqual(buy[0]["owner"],"Jane Example")

    def test_excludes_grants_exercises_zero_price_options_and_wrong_direction(self):
        for raw in (form4_xml(code="A",direction="A"),
                    form4_xml(code="M",direction="A"),
                    form4_xml(code="P",direction="D"),
                    form4_xml(price="0"),
                    form4_xml(title="Stock Options"),
                    form4_xml(price="not-reported")):
            with self.subTest(raw=raw[:60]):
                self.assertEqual(self.parse(raw), [])

    def test_rejects_wrong_issuer_and_non_form4(self):
        with self.assertRaisesRegex(ValueError, "issuer CIK mismatch"):
            self.parse(form4_xml(issuer="456"))
        with self.assertRaisesRegex(ValueError, "Not a regular"):
            self.parse(form4_xml(root="informationTable"))

    def test_amendments_and_incomplete_filings_require_manual_review(self):
        submissions={"cik":123,"filings":{"recent":{
            "form":["4", "4/A"],"filingDate":["2026-10-07","2026-10-09"],
            "accessionNumber":["0000000123-26-000001","0000000123-26-000002"],
            "primaryDocument":["form4.xml","form4.xml"],
        }}}
        with self.assertRaisesRegex(ValueError,"amendments"):
            filings_for_issuer(submissions, CIK, as_of=ASOF)

    def test_source_complete_zero_vs_source_missing_are_distinct(self):
        good={"ticker":"TEST","as_of":ASOF.isoformat(),"status":"COMPLETE",
              "filings_reviewed":0,"transactions":[]}
        zero=assess("TEST",good,as_of=ASOF)
        self.assertEqual(zero["Insider Form 4 signal"],STATUS)
        self.assertEqual(zero["Insider open-market purchases"],0)
        self.assertEqual(assess("TEST",None,as_of=ASOF)[
            "Insider Form 4 signal"],REVIEW)
        self.assertIsNone(assess("TEST",None,as_of=ASOF)[
            "Insider open-market purchases"])

    def test_source_backed_cash_amount_and_date(self):
        tx=self.parse(form4_xml())[0]
        good={"ticker":"TEST","as_of":ASOF.isoformat(),"status":"COMPLETE",
              "filings_reviewed":1,"latest_filing":"2026-10-07",
              "transactions":[tx]}
        result=assess("TEST",good,as_of=ASOF)
        self.assertEqual(result["Insider open-market purchases"],1)
        self.assertEqual(result["Insider purchase amount USD"],10500)
        self.assertEqual(result["Insider net reported amount USD"],10500)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/FILE).write_text(json.dumps({
                "schema_version":1,"source":"SEC_ISSUER_FORM4_XML",
                "as_of_pacific":ASOF.isoformat(),"records":[good]
            }),encoding="utf-8")
            self.assertIn("TEST",load_records(folder,as_of=ASOF))

    def test_xml_download_only_uses_sec_archive_document(self):
        accession="0000000123-26-000001"
        primary={"accession":accession, "primary":"ownership.xml",
                 "filed":"2026-10-07"}
        seen=[]
        def fetch(uri,contact):
            seen.append(uri)
            return form4_xml()
        with patch("scripts.collect_gem_insider_form4.time.sleep"):
            xml,source=xml_for_filing(CIK,primary,"GEM test@example.org",fetch=fetch)
        self.assertEqual(len(seen),1)
        self.assertIn("/Archives/edgar/data/",source)
        self.assertEqual(len(self.parse(xml)),1)


if __name__=="__main__":
    unittest.main()
