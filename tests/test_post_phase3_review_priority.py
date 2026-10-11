"""Ranking uncovered research leads without making unsupported entry claims."""
import unittest
from datetime import date
from post_phase3_review_priority import review_priority, assign_review_ranks

TODAY=date(2026,10,11)

def case():
    return {
        "Ticker":"ACME", "NCT ID":"NCT01234567",
        "Exact event":"ACME|DRUG_20261130", "Entry qualification":"REVIEW — ENTRY BLOCKED",
        "Phase 3 evidence":"REVIEW — RESULT NOT ADJUDICATED",
        "Phase 3 source":"", "PDUFA verification":"REVIEW — NOT VERIFIED",
        "PDUFA source":"", "Days to PDUFA":50,
    }

def financing():
    return {
        "Exact financing event":"ACME|DRUG_20261130",
        "Source scan":"SOURCE_BLOCKED_RETAINED",
        "Recheck freshness":"STALE",
        "Historical second closing":"NOT VERIFIED",
    }

def market():
    return {
        "market_status":"MARKET_UPDATED",
        "market_source":"https://data.example/ohlcv",
        "last_session":"2026-10-09",
        "last_session_freshness":"RECENT EOD",
        "last_close_usd":"18.80",
        "checked_at_utc":"2026-10-11T15:00:00+00:00",
        "trailing_momentum_pct":"4.2",
        "relative_volume":"1.3",
    }

class ReviewRankingTests(unittest.TestCase):
    def test_no_verified_success_still_produces_useful_triage_score(self):
        r=review_priority(case(),{},financing(),market(),TODAY)
        self.assertEqual(r["Research priority /100"],65)
        self.assertEqual(r["Review timing /30"],30)
        self.assertEqual(r["Review clinical follow-up /20"],0)
        self.assertEqual(r["Review financing follow-up /15"],5)
        self.assertEqual(r["Review regulatory follow-up /15"],7)
        self.assertEqual(r["Review market follow-up /15"],15)
        self.assertEqual(r["Review identity /5"],5)
        self.assertIn("RESEARCH TRIAGE ONLY",r["Research priority status"])

    def test_blocked_financing_never_receives_extra_close_points(self):
        r=review_priority(case(),{},financing(),market(),TODAY)
        self.assertEqual(r["Review financing follow-up /15"],5)

    def test_no_funding_mapping_gets_no_financing_points(self):
        r=review_priority(case(),{},None,market(),TODAY)
        self.assertEqual(r["Review financing follow-up /15"],0)

    def test_market_stale_removes_points(self):
        p=market()
        p["checked_at_utc"]="2026-09-01T05:00:00+00:00"
        r=review_priority(case(),{},None,p,TODAY)
        self.assertEqual(r["Review market follow-up /15"],0)

    def test_pdufa_reported_only_scores_review_urgency_not_verification(self):
        r=review_priority(case(),{},None,None,TODAY)
        self.assertEqual(r["Review regulatory follow-up /15"],7)
        self.assertIn("NOT independently verified",r["Research priority limitations"])

    def test_rank_review_even_if_evidence_score_none(self):
        a=case()
        a["Evidence score /100"]=None
        a["Research priority /100"]=45
        b=dict(a,Ticker="BETA",**{"Exact event":"BETA|DRUG", "Research priority /100":60})
        c=dict(a,Ticker="GONE",**{"Entry qualification":"EXCLUDED — FDA DECIDED / DATE PASSED", "Research priority /100":100})
        d=dict(a,Ticker="RED",**{"Entry qualification":"RED WINDOW — NO NEW ENTRY", "Research priority /100":90})
        rows=[a,b,c,d]
        assign_review_ranks(rows)
        self.assertEqual(b["Research rank"],1)
        self.assertEqual(a["Research rank"],2)
        self.assertIsNone(c["Research rank"])
        self.assertIsNone(d["Research rank"])

    def test_green_leads_review_even_when_review_has_more_points(self):
        review=case()
        review["Research priority /100"]=80
        green=dict(review,Ticker="READY",**{"Exact event":"READY|DRUG", "Entry qualification":"GREEN — GATES ATTESTED", "Research priority /100":40})
        assign_review_ranks([review,green])
        self.assertEqual(green["Research rank"],1)
        self.assertEqual(review["Research rank"],2)

    def test_unsourced_lead_still_has_ordinal_research_rank(self):
        lead={
            "Ticker":"LEAD", "NCT ID":"NCT87654321",
            "Exact event":"", "Entry qualification":"REVIEW — RESEARCH LEAD",
            "Phase 3 evidence":"REGISTRY RESULTS POSTED — REVIEW",
            "Phase 3 source":"https://clinicaltrials.gov/study/NCT87654321",
            "PDUFA verification":"REVIEW — SOURCE MISSING",
            "Days to PDUFA":None,
        }
        lead.update(review_priority(lead,None,None,None,TODAY))
        assign_review_ranks([lead])
        self.assertGreater(lead["Research priority /100"],0)
        self.assertEqual(lead["Research rank"],1)
        self.assertIn("Phase 3",lead["Research priority limitations"])
