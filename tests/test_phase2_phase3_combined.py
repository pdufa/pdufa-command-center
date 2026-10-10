"""Phase 2 p + Phase 3 pre-readout research score gates."""
import unittest
import pandas as pd
from phase2_phase3_combined import combine_phase2_phase3

def candidate(status="100-POINT RESEARCH SCORE — UNCALIBRATED", p_status="REPORTED — MANUAL CLINICAL REVIEW", points=84):
    return pd.DataFrame([{"NCT ID":"NCT12345678", "Assessment Status":status,
        "Pre-Readout Evidence Points":points, "Phase 2 p Evidence":p_status,
        "Phase 3 Success Probability %":pd.NA}])

def evidence(phase2="19"):
    return pd.DataFrame([{"nct_id":"NCT12345678","phase2_efficacy_points":phase2}])

class CombinedResearchScoreTests(unittest.TestCase):
    def test_valid_combination_adds_to_hundred_point_rubric_not_probability(self):
        out=combine_phase2_phase3(candidate(),evidence()).iloc[0]
        self.assertEqual(out["Phase 2 Clinical Score /25"],19)
        self.assertEqual(out["Phase 3 Pre-Readout Score /75"],65)
        self.assertEqual(out["Combined Pre-Readout Score /100"],84)
        self.assertTrue(pd.isna(out["Phase 3 Success Probability %"]))
        self.assertIn("NOT A PROBABILITY",out["Combined Score Status"])
    def test_no_verified_phase2_p_blocks_combined_score(self):
        for p in ("NOT COLLECTED","NO VERIFIED PRIMARY p","NO LINKED PHASE 2 NCT",""):
            out=combine_phase2_phase3(candidate(p_status=p),evidence()).iloc[0]
            self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]),p)
    def test_incomplete_clinical_domains_are_never_made_up_from_p(self):
        out=combine_phase2_phase3(candidate(status="NOT SCORED — BEFORE-READOUT EVIDENCE INCOMPLETE", points=pd.NA),evidence()).iloc[0]
        self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]))
    def test_missing_manual_phase2_assessment_stays_missing(self):
        out=combine_phase2_phase3(candidate(),evidence(phase2="")).iloc[0]
        self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]))
    def test_invalid_points_fail_closed(self):
        for p in ("26","-1","nan","oops"):
            out=combine_phase2_phase3(candidate(),evidence(phase2=p)).iloc[0]
            self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]),p)
    def test_wrong_trial_does_not_receive_phase2_points(self):
        x=evidence()
        x.loc[0,"nct_id"]="NCT87654321"
        out=combine_phase2_phase3(candidate(),x).iloc[0]
        self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]))
    def test_duplicate_nct_manual_records_fail_closed(self):
        x=pd.concat([evidence(),evidence()],ignore_index=True)
        out=combine_phase2_phase3(candidate(),x).iloc[0]
        self.assertTrue(pd.isna(out["Combined Pre-Readout Score /100"]))
        self.assertIn("DUPLICATE",out["Combined Score Status"])
if __name__=="__main__":
    unittest.main()
