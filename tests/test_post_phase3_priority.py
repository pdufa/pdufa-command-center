"""Source-gated evidence ranking must not override entry eligibility."""
import unittest
from datetime import date
from post_phase3_priority import score_candidate, assign_priority_ranks

TODAY = date(2026, 10, 11)
GATES = (
    "trial_identity", "phase3_primary", "clinical_benefit", "safety",
    "second_financing", "no_unresolved_dilution",
    "post_readout_price_base", "normalized_volume",
)

def event():
    return {
        "ticker": "ACME", "nct_id": "NCT01234567",
        "phase3_status": "VERIFIED_SUCCESS", "phase3_date": "2026-03-02",
        "trial_evidence_url": "https://issuer.example/readout",
        "pdufa_date": "2026-12-01", "pdufa_confirmation": "VERIFIED",
        "pdufa_evidence_url": "https://issuer.example/goal",
        "conflict_flag": "NONE",
    }

def financing():
    return {
        "Exact financing event": "ACME|EXACT_DRUG",
        "Audited gate details": " | ".join(x + ": PASS — ATTESTED" for x in GATES),
        "Historical second closing": "DOCUMENTED — RECHECK REQUIRED",
        "Recheck freshness": "RECENT",
        "Source scan": "FINANCING_VERIFIED",
        "Second source": "https://www.sec.gov/Archives/edgar/data/123456/0001.htm",
    }

def market():
    return {
        "ticker": "ACME", "market_status": "MARKET_UPDATED",
        "market_source": "https://market.example/daily/ACME",
        "last_session_freshness": "RECENT EOD",
        "last_session": "2026-10-09",
        "checked_at_utc": "2026-10-11T15:00:00+00:00",
        "last_close_usd": "20.00",
        "trailing_momentum_pct": "8",
        "relative_volume": "1.2",
    }

class TestUnifiedRatings(unittest.TestCase):
    def test_full_supported_rubric_max_is_95_without_company_audit(self):
        x=score_candidate(event(), financing(), market(), TODAY)
        self.assertEqual(x["Evidence score /100"],95)
        self.assertEqual(x["Clinical evidence /30"],30)
        self.assertEqual(x["Financing evidence /20"],20)
        self.assertEqual(x["Trading setup /20"],20)
        self.assertEqual(x["PDUFA evidence /15"],15)
        self.assertEqual(x["Market activity /10"],10)
        self.assertEqual(x["Company track record /5"],0)
        self.assertEqual(x["Rating coverage"],"5/6 categories evidenced")

    def test_financing_sec_blocked_is_zero_financing_points(self):
        f=financing()
        f["Source scan"]="SOURCE_BLOCKED_RETAINED"
        f["Recheck freshness"]="STALE"
        x=score_candidate(event(), f, market(), TODAY)
        self.assertEqual(x["Financing evidence /20"],0)
        self.assertLess(x["Evidence score /100"],95)

    def test_funding_gate_only_from_exact_named_pass_labels(self):
        f=financing()
        f["Audited gate details"]="second_financing: REVIEW — EVIDENCE MISSING | no_unresolved_dilution: REVIEW — EVIDENCE MISSING"
        x=score_candidate(event(),f,market(),TODAY)
        self.assertEqual(x["Financing evidence /20"],0)
        self.assertEqual(x["Clinical evidence /30"],0)
        self.assertEqual(x["Trading setup /20"],0)

    def test_market_stale_or_untrusted_not_rated(self):
        p=market()
        p["checked_at_utc"]="2026-09-01T10:00:00+00:00"
        x=score_candidate(event(),financing(),p,TODAY)
        self.assertEqual(x["Market activity /10"],0)
        self.assertEqual(x["Trading setup /20"],0)
        p["checked_at_utc"]="2026-10-11T15:00:00+00:00"
        p["market_source"]="http://market.example/ticker"
        x=score_candidate(event(),financing(),p,TODAY)
        self.assertEqual(x["Market activity /10"],0)

    def test_no_program_evidence_remains_unrated_not_zero(self):
        e=event()
        e["phase3_status"]="RESULTS_REVIEW"
        e["pdufa_confirmation"]="REPORTED_ONLY"
        x=score_candidate(e,{},market(),TODAY)
        self.assertIsNone(x["Evidence score /100"])
        self.assertTrue(x["Rating status"].startswith("NOT RATED"))

    def test_unmatched_research_lead_not_promoted(self):
        x=score_candidate(None,{},market(),TODAY)
        self.assertIsNone(x["Evidence score /100"])
        self.assertIn("RESEARCH LEAD",x["Rating status"])

    def test_stale_snapshot_blocks_all_numbers(self):
        x=score_candidate(event(),financing(),market(),TODAY,snapshot_current=False)
        self.assertIsNone(x["Evidence score /100"])
        self.assertIn("STALE",x["Rating status"])

    def test_unknown_financing_cannot_be_100_from_clinical(self):
        f=financing()
        f["Second source"]="https://other.example/filing"
        x=score_candidate(event(),f,market(),TODAY)
        self.assertEqual(x["Financing evidence /20"],0)
        self.assertNotEqual(x["Evidence score /100"],95)

    def test_negative_momentum_does_not_receive_positive_points(self):
        p=market()
        p["trailing_momentum_pct"]="-1.0"
        p["relative_volume"]="0.7"
        x=score_candidate(event(),financing(),p,TODAY)
        self.assertEqual(x["Market activity /10"],4)

    def test_rank_is_numeric_highest_first_independent_of_gate(self):
        rows=[
            {"Ticker":"A","NCT ID":"NCT01234567", "Exact event":"A|A","Entry qualification":"REVIEW — ENTRY BLOCKED","Evidence score /100":70},
            {"Ticker":"B","NCT ID":"NCT01234568", "Exact event":"B|B","Entry qualification":"GREEN — GATES ATTESTED","Evidence score /100":60},
            {"Ticker":"C","NCT ID":"NCT01234569", "Exact event":"C|C","Entry qualification":"REVIEW — RESEARCH LEAD","Evidence score /100":None},
            {"Ticker":"D","NCT ID":"NCT01234570", "Exact event":"D|D","Entry qualification":"RED WINDOW — NO NEW ENTRY","Evidence score /100":85},
        ]
        assign_priority_ranks(rows)
        self.assertEqual(rows[0]["Evidence rank"],1)
        self.assertEqual(rows[1]["Evidence rank"],2)
        self.assertIsNone(rows[2]["Evidence rank"])
        self.assertIsNone(rows[3]["Evidence rank"])
        self.assertTrue(rows[0]["Entry qualification"].startswith("REVIEW"))
        self.assertTrue(rows[1]["Entry qualification"].startswith("GREEN"))
