"""Source identity, publication lag, delta calculations and GEM 13F scoring."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_hedge_funds import (
    DATA_FILE, REVIEW, STATUS, assess_signal, issuer_name,
    load_signal_records, summarize_filings, tracked_issuers,
)
from gem_two_benchmark import assess
from scripts.collect_gem_hedge_funds import (
    filing_inventory, get_holdings, parse_information_table, collect,
)

ASOF = date(2026, 10, 13)
CUSIP = "123456789"


def xml_holdings(issuer="Test Biotech Inc.", cusip=CUSIP, shares=500):
    return (f'<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">'
            '<infoTable><nameOfIssuer>' + issuer +
            '</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>' + cusip +
            '</cusip><shrsOrPrnAmt><sshPrnamt>' + str(shares) +
            '</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>'
            '</infoTable></informationTable>').encode()


def manager(current=500, previous=200):
    return {
        "cik": "0001263508", "name": "Baker Bros. Advisors LP",
        "status": "COMPLETE",
        "latest_period": "2026-06-30",
        "prior_period": "2026-03-31",
        "latest_filing": "2026-08-14",
        "current_url": "https://www.sec.gov/Archives/edgar/data/1263508/111/infotable.xml",
        "previous_url": "https://www.sec.gov/Archives/edgar/data/1263508/222/infotable.xml",
        "current": {"holdings": [{"issuer": "Test Biotech Inc.", "cusip": CUSIP,
                                  "shares": current}] if current else []},
        "previous": {"holdings": [{"issuer": "Test Biotech Inc.", "cusip": CUSIP,
                                   "shares": previous}] if previous else []},
    }


class HedgeFundTests(unittest.TestCase):
    def test_xml_parses_common_shares_only_not_puts_or_bonds(self):
        self.assertEqual(parse_information_table(xml_holdings())[0]["shares"], 500)
        put = xml_holdings().replace(b"<shrsOrPrnAmt>", b"<putCall>PUT</putCall><shrsOrPrnAmt>")
        self.assertEqual(parse_information_table(put), [])
        bonds = xml_holdings().replace(b">COM<", b">CONVERTIBLE BONDS<")
        self.assertEqual(parse_information_table(bonds), [])
        with self.assertRaisesRegex(ValueError, "Invalid SEC"):
            parse_information_table(b"<bad")

    def test_manager_comparison_uses_matching_13f_issuer_and_same_cusip(self):
        rows, reports = summarize_filings({"TEST BIOTECH": "TEST"},
                                          [manager()], as_of=ASOF)
        self.assertEqual(len(reports), 1)
        self.assertEqual(rows[0]["ticker"], "TEST")
        self.assertEqual(rows[0]["managers"][0]["shares"], 500)
        self.assertEqual(rows[0]["managers"][0]["prior_shares"], 200)
        signal = assess_signal("TEST", rows[0], as_of=ASOF)
        self.assertEqual(signal["Hedge-fund signal"], STATUS)
        self.assertEqual(signal["Hedge-fund accumulation /10"], 4)
        self.assertEqual(signal["Hedge-fund managers adding"], 1)
        self.assertEqual(signal["Hedge-fund managers holding"], 1)

    def test_reduction_and_no_longer_reported_are_not_fabricated_buys(self):
        reduced, _ = summarize_filings({"TEST BIOTECH": "TEST"},
                                       [manager(current=100, previous=400)],
                                       as_of=ASOF)
        self.assertEqual(assess_signal("TEST", reduced[0], as_of=ASOF)[
            "Hedge-fund managers reducing"], 1)
        gone, _ = summarize_filings({"TEST BIOTECH": "TEST"},
                                    [manager(current=0, previous=400)], as_of=ASOF)
        r = assess_signal("TEST", gone[0], as_of=ASOF)
        self.assertEqual(r["Hedge-fund managers no longer reported"], 1)
        self.assertEqual(r["Hedge-fund accumulation /10"], 0)

    def test_mismatched_cusip_and_ambiguous_stock_name_do_not_score(self):
        m = manager()
        m["previous"]["holdings"][0]["cusip"] = "987654321"
        rows, _ = summarize_filings({"TEST BIOTECH": "TEST"}, [m], as_of=ASOF)
        self.assertEqual(rows, [])
        with tempfile.TemporaryDirectory() as td:
            with (Path(td)/"company_registry.csv").open("w", newline="") as fp:
                w = csv.DictWriter(fp, fieldnames=["ticker", "company", "cik10"])
                w.writeheader()
                w.writerows([
                    {"ticker": "AAA", "company": "Example Biotech, Inc.", "cik10": "123"},
                    {"ticker": "BBB", "company": "Example Biotech Corp.", "cik10": "124"},
                ])
            self.assertNotIn("EXAMPLE BIOTECH", tracked_issuers(td))
        self.assertEqual(issuer_name("The Test Biotech, Inc."), "TEST BIOTECH")

    def test_unverified_manager_or_unpublished_source_no_points(self):
        bad = manager()
        bad["status"] = "ERROR"
        rows, _ = summarize_filings({"TEST BIOTECH": "TEST"}, [bad], as_of=ASOF)
        self.assertEqual(rows, [])
        self.assertEqual(assess_signal("TEST", None, as_of=ASOF)[
            "Hedge-fund signal"], REVIEW)
        with tempfile.TemporaryDirectory() as td:
            doc = Path(td)/DATA_FILE
            doc.write_text(json.dumps({"schema_version": 1,
                "source": "SEC_13F_XML_INFO_TABLE", "as_of_pacific": "2026-10-14",
                "records": [{"ticker": "TEST", "quarter_end": "2026-06-30",
                             "managers": []}]}))
            self.assertEqual(load_signal_records(td, as_of=ASOF), {})

    def test_filings_are_asof_dated_and_amendments_cannot_pass(self):
        submissions = {"cik": 1263508, "filings": {"recent": {
            "form": ["13F-HR", "13F-HR", "13F-HR/A"],
            "filingDate": ["2026-08-14", "2026-05-15", "2026-08-15"],
            "reportDate": ["2026-06-30", "2026-03-31", "2026-06-30"],
            "accessionNumber": ["0001104659-26-097191",
                                "0001104659-26-062547",
                                "0001104659-26-097999"],
        }}}
        accepted = filing_inventory(submissions, "0001263508", as_of=ASOF)
        self.assertEqual(len(accepted), 2)
        self.assertTrue(accepted[1]["amended"])
        self.assertEqual(accepted[1]["period"], date(2026, 3, 31))
        self.assertEqual(accepted[1]["accession"], "0001104659-26-097999")

    def test_amended_restated_13f_is_complete_but_add_only_is_blocked(self):
        filing = {"accession": "0001104659-26-097191", "amended": True}
        def fetch(url, _):
            if url.endswith("index.json"):
                return json.dumps({"directory": {"item": [
                    {"name": "primary_doc.xml"}, {"name": "infotable.xml"}]}}).encode()
            if url.endswith("primary_doc.xml"):
                return b"<form13F><amendmentType>RESTATEMENT</amendmentType></form13F>"
            return xml_holdings()
        with patch("scripts.collect_gem_hedge_funds.time.sleep"):
            self.assertEqual(get_holdings("0001263508", filing, "Test test@example.org",
                                          fetch=fetch)["holdings"][0]["shares"], 500)
        def add_only(url, who):
            if url.endswith("primary_doc.xml"):
                return b"<form13F><amendmentType>NEW HOLDINGS</amendmentType></form13F>"
            return fetch(url, who)
        with patch("scripts.collect_gem_hedge_funds.time.sleep"):
            with self.assertRaisesRegex(ValueError, "not a verified complete"):
                get_holdings("0001263508", filing, "Test test@example.org",
                             fetch=add_only)

    def test_get_holdings_exact_infoshare_xml(self):
        filing = {"accession": "0001104659-26-097191"}
        requests = []
        def fetch(url, _):
            requests.append(url)
            return (json.dumps({"directory": {"item": [
                {"name": "primary_doc.xml"}, {"name": "infotable.xml"}]}}).encode()
                if url.endswith("index.json") else xml_holdings())
        with patch("scripts.collect_gem_hedge_funds.time.sleep"):
            report = get_holdings("0001263508", filing,
                                  "GEM Research test@example.org", fetch=fetch)
        self.assertEqual(report["holdings"][0]["shares"], 500)
        self.assertEqual(len(requests), 2)

    def test_collector_fail_closed_when_sec_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            with (Path(td)/"gem_hedge_fund_managers.csv").open("w", newline="") as fp:
                w = csv.DictWriter(fp, fieldnames=[
                    "manager_name", "cik", "sec_proof_url"])
                w.writeheader()
                w.writerow({"manager_name": "Baker Bros. Advisors LP", "cik": "0001263508",
                            "sec_proof_url": "https://www.sec.gov/Archives/edgar/data/1263508/proof"})
            def denied(*args, **kwargs):
                raise RuntimeError("403 SEC")
            with patch("scripts.collect_gem_hedge_funds.time.sleep"):
                r = collect(td, as_of=ASOF, agent="GEM Research test@example.org",
                            fetch=denied)
            self.assertEqual(r["managers_complete"], 0)
            self.assertEqual(r["records"], [])
            self.assertEqual(r["collector_status"], "BLOCKED — NO VERIFIED 13F MANAGERS")

    def test_two_benchmark_entry_unchanged_and_fund_score_advisory(self):
        event = {"phase3_status": "VERIFIED_SUCCESS", "phase3_date": "2026-09-01",
                 "ticker": "TEST", "nct_id": "NCT01234567",
                 "trial_evidence_url": "https://issuer.example/phase3"}
        base = {
            "Ticker": "TEST", "NCT ID": "NCT01234567", "Exact event": "TEST|DRUG",
            "2nd Financing Completed": "YES — VERIFIED (HISTORICAL)",
            "Verified 2nd financing close date": "2026-10-01",
            "Clinical evidence /30": 30, "Trading setup /20": 20,
            "Market activity /10": 10, "Cash runway (months)": 18,
            "PDUFA verification": "VERIFIED — SOURCE LINKED",
            "Days to PDUFA": 45,
        }
        a = assess(base, event, as_of=ASOF)
        b = assess({**base, "Hedge-fund signal": STATUS,
                    "Hedge-fund accumulation /10": 4}, event, as_of=ASOF)
        self.assertTrue(a["Two-benchmark eligible"])
        self.assertTrue(b["Two-benchmark eligible"])
        self.assertEqual(b["Two-benchmark priority /100"] -
                         a["Two-benchmark priority /100"], 4)
        self.assertEqual(sum(b[k] for k in (
            "Phase 3 quality /30", "Financial runway /20",
            "Dilution overhang /15", "Trading activity /20",
            "PDUFA timing /5", "Hedge-fund accumulation /10")),
            b["Two-benchmark priority /100"])


if __name__ == "__main__":
    unittest.main()
