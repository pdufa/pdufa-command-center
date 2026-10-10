"""Phase 2 p evidence must predate scoring and match exact Phase 2 trial."""
import unittest
from datetime import date
import pandas as pd
from phase2_p_evidence import join_phase2_p
from scripts.phase2_pre_readout_pvalues_intake import extract

AS_OF = date(2026, 10, 10)
P2 = "NCT87654321"
P3 = "NCT12345678"


def queue():
    return pd.DataFrame([{"NCT ID":P3,"Ticker":"BIO",
        "Phase 2 NCT Links":P2,"Drug":"BIO-A",
        "Phase 3 Success Probability %":pd.NA,
        "Pre-Readout Evidence Points":pd.NA}])


def observation(**kw):
    row={"nct_id":P2,"ticker":"BIO","primary_endpoint":"Clinical score",
         "p_value":"0.012","p_value_modifier":"=",
         "results_first_posted":"2026-08-01",
         "observed_at_utc":"2026-10-08T12:00:00Z",
         "source_url":"https://clinicaltrials.gov/study/"+P2}
    row.update(kw)
    return pd.DataFrame([row])


class Phase2PTests(unittest.TestCase):
    def test_pvalue_is_evidence_not_probability(self):
        joined=join_phase2_p(queue(),observation(),as_of=AS_OF)
        r=joined.iloc[0]
        self.assertEqual(r["Phase 2 p Evidence"],"REPORTED — MANUAL CLINICAL REVIEW")
        self.assertIn("0.012",r["Phase 2 Primary p-values (research only)"])
        self.assertEqual(r["Days Since Phase 2 p Verification"],2)
        self.assertEqual(r["Phase 2 Registry Results Posted"],"2026-08-01")
        self.assertTrue(pd.isna(r["Phase 3 Success Probability %"]))
        self.assertTrue(pd.isna(r["Pre-Readout Evidence Points"]))

    def test_only_exact_nct_and_ticker_join(self):
        for o in (observation(nct_id="NCT99999999"),
                  observation(ticker="OTHER"),
                  observation(source_url="https://example.org/false"),
                  observation(primary_endpoint="")):
            r=join_phase2_p(queue(),o,as_of=AS_OF)
            self.assertEqual(r.iloc[0]["Phase 2 p Evidence"],"NO VERIFIED PRIMARY p")

    def test_future_results_or_first_observation_do_not_leak(self):
        for o in (observation(results_first_posted="2026-10-11"),
                  observation(observed_at_utc="2026-10-11T10:00:00Z"),
                  observation(results_first_posted="2026-10-09",
                              observed_at_utc="2026-10-08T12:00:00Z")):
            r=join_phase2_p(queue(),o,as_of=AS_OF)
            self.assertEqual(r.iloc[0]["Phase 2 p Evidence"],"NO VERIFIED PRIMARY p")

    def test_phase2_result_must_not_be_phase3_result(self):
        study={"protocolSection":{
            "identificationModule":{"nctId":P2},
            "designModule":{"phases":["PHASE2"]},
            "statusModule":{"resultsFirstPostDateStruct":{"date":"2026-09-01"},
                            "lastUpdatePostDateStruct":{"date":"2026-09-01"}}},
            "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[{
                "type":"PRIMARY","title":"Improvement","analyses":[
                    {"pValue":"0.002","pValueModifier":"LT",
                     "groupIds":["OG001","OG002"]}]}]}}}
        rows,flag=extract(study,P2,"BIO","2026-10-10T15:00:00Z")
        self.assertEqual(flag,"PRIMARY_P_FOUND")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["p_value"],"0.002")
        self.assertEqual(rows[0]["nct_id"],P2)
        study["protocolSection"]["designModule"]["phases"]=["PHASE3"]
        self.assertEqual(extract(study,P2,"BIO","2026-10-10T15:00:00Z")[1],"NOT_PHASE2")

    def test_phase2_no_primary_p_is_unknown_not_failure(self):
        study={"protocolSection":{"identificationModule":{"nctId":P2},
               "designModule":{"phases":["PHASE2"]},
               "statusModule":{"resultsFirstPostDateStruct":{"date":"2026-08-20"}}},
               "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[
                   {"type":"PRIMARY","title":"Endpoint","analyses":[]}]}}}
        rows,flag=extract(study,P2,"BIO","2026-10-10T15:00:00Z")
        self.assertEqual(rows,[])
        self.assertEqual(flag,"PRIMARY_P_NOT_REPORTED")

    def test_no_phase2_link_is_explicit_missing(self):
        row=queue()
        row.loc[0,"Phase 2 NCT Links"]=""
        out=join_phase2_p(row,observation(),as_of=AS_OF)
        self.assertEqual(out.iloc[0]["Phase 2 p Evidence"],"NO LINKED PHASE 2 NCT")

    def test_pre_readout_pipeline_displays_observation_without_scoring_from_it(self):
        from pathlib import Path
        app=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
        self.assertIn('join_phase2_p(_p3_candidates, _phase2_p, as_of=cutoff)',app)
        self.assertIn('"data/phase2_primary_p_evidence.csv"',app)
        self.assertIn("A small p-value",app)
        self.assertIn("require_protocol=True",app)

if __name__=="__main__":
    unittest.main()
