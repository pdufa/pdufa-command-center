"""Real dated pilot evidence remains an uncalibrated research assessment.

This validates the persisted first source review against the *strict* rubric,
not against the less constrained provisional score display.
"""
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from pre_readout_score import assess, WEIGHTS

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"data"/"phase3_pre_readout_evidence.csv"


def research_queue():
    return pd.DataFrame([{
        "Ticker":"TRVI", "Company":"Trevi Therapeutics, Inc.",
        "Drug":"NAL ER","Indication":"Idiopathic Pulmonary Fibrosis",
        "NCT ID":"NCT07671911", "Source":"https://clinicaltrials.gov/study/NCT07671911",
        "Program Identity":"VERIFIED", "Phase 2 NCT Links":"NCT05964335",
        "Assessment Status":"NOT SCORED — BEFORE-READOUT EVIDENCE INCOMPLETE",
        "Pre-Readout Evidence Points":float("nan"),
        "Phase 3 Success Probability %":float("nan"),
        "Missing Evidence":"issuer check",
    }])


class FirstStrictResearchPilotTests(unittest.TestCase):
    def setUp(self):
        self.review=pd.read_csv(EVIDENCE).fillna("")
        self.assertEqual(len(self.review),2,"Only the two dated, independently sourced pilot reviews belong in this ledger")
        self.assertEqual(set(self.review["nct_id"]), {"NCT07671911", "NCT07363577"})

    def test_review_has_exact_study_dates_sources_and_issuer_check(self):
        record=self.review.loc[self.review["nct_id"].eq("NCT07671911")].iloc[0]
        self.assertEqual((record["ticker"],record["nct_id"]),("TRVI","NCT07671911"))
        self.assertEqual(record["assessment_cutoff_date"],"2026-10-10")
        self.assertEqual(record["issuer_readout_status"],"VERIFIED_UNRELEASED")
        self.assertEqual(record["issuer_readout_checked_at"],"2026-10-10")
        self.assertEqual(record["issuer_readout_source"],
                         "https://ir.trevitherapeutics.com/news-events/press-releases")
        self.assertEqual(record["actual_topline_release_date"],"")
        self.assertEqual(sum(float(record[f"{key}_points"]) for key in WEIGHTS),80)

    def test_strict_rubric_gives_research_points_not_success_probability(self):
        scored=assess(research_queue(),self.review,date(2026,10,10)).iloc[0]
        self.assertEqual(scored["Pre-Readout Evidence Points"],80)
        self.assertEqual(scored["Assessment Status"],
                         "100-POINT RESEARCH SCORE — UNCALIBRATED")
        self.assertTrue(pd.isna(scored["Phase 3 Success Probability %"]))

    def test_exact_nova2_second_research_score_and_dose_caveat(self):
        lbrx = research_queue()
        lbrx.loc[0, "Ticker"]="LBRX"
        lbrx.loc[0, "Drug"]="LB-102 (100 mg tablet) | LB-102 (50 mg tablet)"
        lbrx.loc[0, "Indication"]="Schizophrenia"
        lbrx.loc[0, "NCT ID"]="NCT07363577"
        lbrx.loc[0, "Source"]="https://clinicaltrials.gov/study/NCT07363577"
        lbrx.loc[0, "Phase 2 NCT Links"]="NCT06179108"
        out=assess(lbrx,self.review,date(2026,10,10)).iloc[0]
        self.assertEqual(out["Pre-Readout Evidence Points"],72)
        self.assertEqual(out["Assessment Status"],"100-POINT RESEARCH SCORE — UNCALIBRATED")
        self.assertTrue(pd.isna(out["Phase 3 Success Probability %"]))
        evidence=self.review.loc[self.review["nct_id"].eq("NCT07363577")].iloc[0]
        # This numeric p comes from the 75mg Phase 2 comparator. NOVA-2
        # tests 50/100mg: statistical significance does not establish
        # effectiveness of either dose in the Phase 3 study.
        self.assertEqual(str(evidence["phase2_primary_pvalue"]),"0.002")
        self.assertEqual(evidence["phase2_pvalue_source_date"],"2026-04-22")
        self.assertEqual(evidence["issuer_readout_checked_at"],"2026-10-10")
        self.assertTrue(pd.isna(assess(lbrx,self.review,date(2026,10,11)).iloc[0]["Pre-Readout Evidence Points"]))
        for changed in (
            {"Drug":"LB-102"}, {"NCT ID":"NCT07369154"},
            {"Program Identity":"REVIEW"}, {"Phase 2 NCT Links":""},
        ):
            tampered=lbrx.copy()
            for col,val in changed.items():
                tampered.loc[0,col]=val
            self.assertTrue(pd.isna(assess(tampered,self.review,date(2026,10,10)).iloc[0]["Pre-Readout Evidence Points"]),changed)

    def test_mismatched_trial_or_expired_asof_can_never_inherit_pilot(self):
        wrong=research_queue()
        wrong.loc[0,"NCT ID"]="NCT07671912"
        self.assertTrue(pd.isna(assess(wrong,self.review,date(2026,10,10)).iloc[0]["Pre-Readout Evidence Points"]))
        yesterday=assess(research_queue(),self.review,date(2026,10,9)).iloc[0]
        self.assertTrue(pd.isna(yesterday["Pre-Readout Evidence Points"]))
        tomorrow=assess(research_queue(),self.review,date(2026,10,11)).iloc[0]
        self.assertTrue(pd.isna(tomorrow["Pre-Readout Evidence Points"]))

    def test_broken_independent_source_or_unreleased_gate_blocks_score(self):
        for field,value in (
            ("issuer_readout_status","UNVERIFIED"),
            ("issuer_readout_source",""),
            ("issuer_readout_checked_at",""),
            ("phase2_nct_id","NCT00000000"),
            ("phase2_primary_endpoint_met",""),
            ("actual_topline_release_date","2026-10-10"),
            ("phase3_design_source_date","2026-10-10"),
        ):
            tampered=self.review.copy()
            tampered.loc[0,field]=value
            outcome=assess(research_queue(),tampered,date(2026,10,10)).iloc[0]
            self.assertTrue(pd.isna(outcome["Pre-Readout Evidence Points"]), field)


if __name__=="__main__":
    unittest.main()
