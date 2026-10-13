"""Regression cases observed in real partial source runs."""
import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import source_verification as v, recheck_events as recheck
from scripts import nightly_missing_sources as scan

CIK = "0000000001"
COMPANY = {"ticker": "ABC", "company": "Test Pharma", "cik10": CIK}
EVENT = {"event_key": "ABC|DRUG", "ticker": "ABC", "company": "Test Pharma",
         "drug": "TestDrug", "indication": "lung cancer", "pdufa_date": "2026-11-01"}
DOC = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex99-1.htm"


def rows(path, records):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=records[0]); w.writeheader(); w.writerows(records)


def facts(form="10-Q", cash_tag="CashAndCashEquivalentsAtCarryingValue", flow=-25):
    base = {"end": "2026-09-30", "filed": "2026-10-10", "form": form, "accn": "0000000001-26-000001"}
    return {"cik": 1, "facts": {"us-gaap": {
        cash_tag: {"units": {"USD": [{**base, "val": 100}]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [{**base, "val": flow, "start": "2026-07-01"}]}}
    }}}


class ScanRepairs(unittest.TestCase):
    def verifier(self, payload, **kwargs):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return v.Verifier([COMPANY], fetch=lambda u: raw, as_of=date(2026, 10, 12), **kwargs)

    def test_legacy_documentless_accession_does_not_discard_current_inventory(self):
        payload = {"cik": 1, "tickers": ["ABC"], "filings": {"recent": {
            "form": ["8-K", "10-Q"], "filingDate": ["2026-10-10", "1999-03-15"],
            "accessionNumber": ["0000000001-26-000001", "0000000001-99-000001"],
            "primaryDocument": ["current.htm", ""]}}}
        result = self.verifier(payload).registry(COMPANY)
        self.assertEqual(result["verification_status"], "VERIFIED")
        payload["filings"]["recent"]["accessionNumber"][1] = "not-an-accession"
        self.assertEqual(self.verifier(payload).registry(COMPANY)["verification_status"], "REVIEW_REQUIRED")

    def test_transition_report_is_current_financial_evidence(self):
        result = self.verifier(facts(form="10-KT")).financial(EVENT)
        self.assertEqual([r["verification_status"] for r in result], ["VERIFIED", "VERIFIED"])

    def test_positive_operating_flow_resolves_runway_as_not_applicable(self):
        result = self.verifier(facts(flow=25)).financial(EVENT)
        self.assertEqual(result[1]["verification_status"], "NOT_APPLICABLE")
        self.assertTrue(result[1]["source_sha256"])
        self.assertEqual(v.summary(result)["required_findings_unresolved"], 0)

    def test_restricted_cash_is_named_and_does_not_become_spendable_runway(self):
        result = self.verifier(facts(cash_tag="CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")).financial(EVENT)
        self.assertEqual(result[0]["claim"], "LIQUIDITY_FACT")
        self.assertEqual(result[0]["verification_status"], "VERIFIED")
        self.assertEqual(result[1]["verification_status"], "REVIEW_REQUIRED")
        self.assertIn("restricted", result[1]["reason"])

    def test_different_accessions_cannot_supply_one_runway(self):
        payload = facts()
        payload["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"][0]["accn"] = "0000000001-26-000002"
        self.assertEqual(self.verifier(payload).financial(EVENT)[1]["verification_status"], "REVIEW_REQUIRED")

    def test_collector_and_verifier_use_identical_cash_and_period_arithmetic(self):
        payload = facts()
        with patch.object(recheck, "get", return_value=json.dumps(payload)):
            collected = recheck.cash_check(CIK)
        verified = self.verifier(payload).financial({**EVENT, "cash": str(collected["cash"]), "cash_runway_months": str(collected["runway"])})
        self.assertEqual([r["verification_status"] for r in verified], ["VERIFIED", "VERIFIED"])

    def test_official_issuer_target_requires_explicit_host_mapping_and_company(self):
        url = "https://ir.testpharma.com/release"
        event = {**EVENT, "pdufa_evidence_url": url}
        source = b"Test Pharma announced TestDrug for lung cancer. FDA PDUFA target date is November 1, 2026."
        verifier = self.verifier(source, issuer_sources={"ABC": {"hosts": ["ir.testpharma.com"]}})
        self.assertEqual(verifier.regulatory(event)[0]["verification_status"], "VERIFIED")
        wrong = self.verifier(source.replace(b"Test Pharma", b"Other Company"), issuer_sources={"ABC": {"hosts": ["ir.testpharma.com"]}})
        self.assertEqual(wrong.regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_missing_decision_date_can_be_recovered_from_explicit_action_clause(self):
        event = {**EVENT, "outcome": "APPROVED", "pdufa_evidence_url": DOC}
        source = b"On October 10, 2026, FDA approved TestDrug for lung cancer. Test Pharma announced the decision."
        result = self.verifier(source).regulatory(event)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertIn("2026-10-10", result["observed"])

    def test_release_dateline_does_not_create_a_false_target_conflict(self):
        source = b"Test Pharma on February 25, 2026 announced TestDrug for lung cancer with a PDUFA goal date of November 1, 2026."
        result = self.verifier(source).regulatory({**EVENT, "pdufa_evidence_url": DOC})[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-11-01")

    def test_two_explicit_target_dates_still_require_reconciliation(self):
        text = "PDUFA goal date of November 1, 2026, extended to a target action date of December 1, 2026."
        self.assertEqual(v.target_dates(text), {"2026-11-01", "2026-12-01"})

    def test_neighboring_pdf_program_does_not_supply_target_date(self):
        source = ("Test Pharma pipeline • OtherDrug for skin infection PDUFA date of December 1, 2026 "
                  "• TestDrug for lung cancer PDUFA date of November 1, 2026").encode()
        result = self.verifier(source).regulatory({**EVENT, "pdufa_evidence_url": DOC})[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-11-01")

    def test_same_drug_other_indication_does_not_supply_target_date(self):
        event = {**EVENT, "indication": "advanced systemic mastocytosis", "pdufa_evidence_url": DOC}
        source = ("Test Pharma TestDrug for advanced systemic mastocytosis has a PDUFA date of November 1, 2026. "
                  "TestDrug for nonadvanced systemic mastocytosis has a PDUFA date of December 1, 2026.").encode()
        result = self.verifier(source).regulatory(event)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-11-01")

    def test_nonadvanced_indication_requires_its_qualifier(self):
        self.assertFalse(v.indication_matches({"indication": "Non-Advanced Systemic Mastocytosis"},
                                              "advanced systemic mastocytosis"))
        self.assertTrue(v.indication_matches({"indication": "Non-Advanced Systemic Mastocytosis"},
                                             "NonAdvanced Systemic Mastocytosis"))

    def test_dose_suffix_does_not_hide_exact_active_drug_identity(self):
        self.assertTrue(v.drug_matches({"drug": "Ameluz PDT"}, "Ameluz is a photosensitizer"))
        self.assertTrue(v.drug_matches({"drug": "Phentolamine Ophthalmic Solution 0.75%"}, "phentolamine ophthalmic solution for presbyopia"))
        self.assertFalse(v.drug_matches({"drug": "TestDrug + OtherDrug"}, "TestDrug only"))

    def test_matching_financing_ledger_supplies_fresh_closing_evidence_only(self):
        review = {"second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                  "second_financing_source": DOC, "second_financing_date": "2026-10-10"}
        event = {**EVENT, "_financing_review": review}
        result = self.verifier(b"On October 10, 2026, Test Pharma completed its public offering for $25 million.").financing(event)
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertIn("not the post-Phase-3 second-financing sequence", result["reason"])
        review["second_financing_source"] = DOC.replace("/data/1/", "/data/2/")
        self.assertEqual(self.verifier(b"closed").financing(event)["verification_status"], "REVIEW_REQUIRED")

    def test_short_interest_keeps_shares_separate_from_float_percentage(self):
        quote = {"chart": {"error": None, "result": [{"meta": {"symbol": "ABC"},
            "timestamp": [datetime(2026, 10, 9, 20, tzinfo=timezone.utc).timestamp()],
            "indicators": {"quote": [{"close": [10], "volume": [1000]}]}}]}}
        nasdaq = {"data": {"symbol": "ABC", "shortInterestTable": {"rows": [{
            "settlementDate": "09/30/2026", "interest": "12,345", "daysToCover": 2.1}]}}}
        def fetch(url):
            if "/short-interest" in url: return json.dumps(nasdaq).encode()
            if "/options/" in url: raise v.SourceUnavailable("HTTP_401")
            return json.dumps(quote).encode()
        result = v.Verifier([COMPANY], fetch=fetch, as_of=date(2026, 10, 12)).market(EVENT)
        short = next(r for r in result if r["claim"] == "SHORT_INTEREST")
        self.assertEqual(short["verification_status"], "VERIFIED")
        self.assertEqual(json.loads(short["observed"])["short_shares"], 12345)
        self.assertNotIn("float_percentage", json.loads(short["observed"]))
        self.assertEqual(v.summary(result)["required_findings_unresolved"], 0)
        self.assertEqual(v.summary(result)["optional_findings_unavailable"], 2)

    def test_supplemental_unavailable_data_cannot_waive_required_market_failure(self):
        result = self.verifier({}).market(EVENT)
        self.assertGreater(v.summary(result)["required_findings_unresolved"], 0)
        self.assertEqual(v.summary(result)["optional_findings_unavailable"], 3)

    def test_exact_event_mapping_is_refetched_and_other_event_cannot_borrow_it(self):
        mapped = {"ABC": {"events": {EVENT['event_key']: {"urls": [DOC]}}}}
        source = b'Test Pharma announced TestDrug for lung cancer. FDA PDUFA target date is November 1, 2026.'
        verifier = self.verifier(source, issuer_sources=mapped)
        self.assertEqual(verifier.regulatory(EVENT)[0]['verification_status'], 'VERIFIED')
        self.assertNotIn(DOC, verifier.references({**EVENT, 'event_key': 'ABC|OTHER'}))
        wrong = self.verifier(source.replace(b'TestDrug', b'OtherDrug'), issuer_sources=mapped)
        self.assertEqual(wrong.regulatory(EVENT)[0]['verification_status'], 'REVIEW_REQUIRED')

    def test_completed_placement_and_funded_debt_draw_do_not_require_closed_before_noun(self):
        placements = [
            'The Private Placement closed on February 18, 2026. Purchasers purchased preferred stock for an aggregate price of $25.0 million.',
            'On September 29, 2025, the Company received $50.0 million from the next available tranche under the Existing Loan Agreement.',
            'On October 31, 2025, the Company sold pursuant to an underwritten public offering 28,452,381 shares of common stock for $4.20 per share.',
        ]
        for text, day in zip(placements, ['2026-02-18','2025-09-29','2025-10-31']):
            self.assertTrue(v.documented_funded_transaction(text, day))
            self.assertFalse(v.documented_funded_transaction(text, '2026-01-01'))
        for text in [
            'On February 18, 2026, the Company entered into an underwriting agreement for $25 million.',
            'The private placement is expected to close on February 18, 2026 for $25 million.',
            'On February 18, 2026, the Company received an undrawn credit facility commitment of $50 million.',
            'As of February 18, 2026, cash includes $25 million of ATM sales during the quarter.',
        ]:
            self.assertFalse(v.documented_funded_transaction(text, '2026-02-18'))

    def test_reviewed_financing_link_retains_the_exact_expected_date(self):
        mapped = {'ABC': {'events': {EVENT['event_key']: {'financing_urls': [DOC]}}}}
        event = {**EVENT, 'financing_close_date': '2026-02-18', 'financing_evidence_url': DOC+'/bad'}
        source = b'The Private Placement closed on February 18, 2026. Purchasers purchased stock for $25 million.'
        result = self.verifier(source, issuer_sources=mapped).financing(event)
        self.assertEqual(result['verification_status'], 'VERIFIED')
        self.assertEqual(result['source_url'], DOC)
        self.assertEqual(self.verifier(source, issuer_sources=mapped).financing({**event,'financing_close_date':'2026-02-19'})['verification_status'],'REVIEW_REQUIRED')

    def test_official_release_date_fields_and_parenthesized_datelines(self):
        text = 'REDWOOD CITY, Calif., (July 29, 2026) – Test Pharma today reported its results.'
        self.assertEqual(v.publication_dates(text,text), {'2026-07-29'})
        html = '<div class="field--name-field-nir-news-date">July 13, 2026</div><p>PDUFA May 13, 2027</p>'
        self.assertEqual(v.publication_dates(html,v.visible(html)), {'2026-07-13'})
        self.assertEqual(v.publication_dates('','PDUFA May 13, 2027 -- Test Pharma'), set())

    def test_approval_letter_can_only_use_same_application_and_supplement_label(self):
        letter_url='https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/123456Orig1s004ltr.pdf'
        label_url='https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/123456s004lbl.pdf'
        event={**EVENT,'outcome':'APPROVED','decision_date':'2026-09-16'}
        config={'ABC':{'events':{EVENT['event_key']:{'approval_label_url':label_url}}}}
        verifier=self.verifier(b'TestDrug for lung cancer',issuer_sources=config)
        text='NDA 123456/S-004 Test Pharma SUPPLEMENT APPROVAL TestDrug'
        combined,label=verifier.approval_label_context(event,letter_url,text)
        self.assertEqual(label,label_url)
        self.assertIn('lung cancer',combined)
        wrong=letter_url.replace('s004','s003')
        self.assertEqual(verifier.approval_label_context(event,wrong,text),(text,''))
        wrong=letter_url.replace('123456','654321')
        self.assertEqual(verifier.approval_label_context(event,wrong,text),(text,''))

    def test_usd_statement_fallback_rejects_foreign_currency_staleness_and_column_swap(self):
        from scripts.financial_report_evidence import report_snapshot
        spec={'start':'2026-01-01','end':'2026-06-30','scale':1000,'period_text':'period ended June 30',
              'currency':'USD','currency_text':'US$','ordered_headers':['Amounts in $000','2026','2025'],
              'cash':{'label':'Cash and cash equivalents at June 30','number_index':0},
              'flow':{'label':'Net cash used in operating activities','number_index':0}}
        html=('Test Pharma US$ period ended June 30 <table><tr><td>Amounts in $000</td><td>2026</td><td>2025</td></tr>'
              '<tr><td>Cash and cash equivalents at June 30</td><td>100</td><td>50</td></tr>'
              '<tr><td>Net cash used in operating activities</td><td>(25)</td><td>(10)</td></tr></table>')
        data=report_snapshot(html,spec,date(2026,10,13))
        self.assertEqual((data['cash'],data['flow']),(100000,-25000))
        for raw,settings,as_of in [(html,{**spec,'currency':'EUR'},date(2026,10,13)),
                                   (html,spec,date(2027,6,30)),
                                   (html.replace('<td>2026</td><td>2025</td>','<td>2025</td><td>2026</td>'),spec,date(2026,10,13))]:
            with self.assertRaises(ValueError):report_snapshot(raw,settings,as_of)


if __name__ == "__main__": unittest.main()
