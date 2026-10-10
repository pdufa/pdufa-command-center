import unittest
from datetime import date
import pandas as pd
from phase2_pre_readout_p import attach_phase2_p
from scripts.phase2_pvalues_intake import linked_trials, evidence_from_study


class Phase2PIntegrationTests(unittest.TestCase):
    def test_exact_pre_cutoff_nct_ticker_and_published_p(self):
        queue = pd.DataFrame([{"NCT ID":"NCT12345678","Ticker":"AAA",
                               "Phase 3 Success Probability %":pd.NA,
                               "Pre-Readout Evidence Points":pd.NA}])
        evidence = pd.DataFrame([{
            "phase3_nct_id":"NCT12345678", "phase2_nct_id":"NCT87654321",
            "ticker":"AAA", "result_first_posted":"2026-09-12",
            "p_value":"0.012", "source_url":"https://clinicaltrials.gov/study/NCT87654321"
        }])
        result=attach_phase2_p(queue,evidence,date(2026,10,10))
        self.assertIn("YES",result.iloc[0]["Phase 2 Primary p Recorded"])
        self.assertEqual(result.iloc[0]["Phase 2 Primary p Values"],"0.012")
        self.assertTrue(pd.isna(result.iloc[0]["Phase 3 Success Probability %"]))
        self.assertTrue(pd.isna(result.iloc[0]["Pre-Readout Evidence Points"]))
        for col,value in [("result_first_posted","2026-10-10"),("ticker","BBB"),
                          ("phase3_nct_id","NCT22222222"),("source_url","https://example.com")]:
            corrupted=evidence.copy()
            corrupted.loc[0,col]=value
            o=attach_phase2_p(queue,corrupted,date(2026,10,10))
            self.assertEqual(o.iloc[0]["Phase 2 Primary p Recorded"],"")

    def test_only_phase2_protocol_with_results_primary_analyses(self):
        study={"protocolSection":{
            "designModule":{"phases":["PHASE2"]},
            "statusModule":{"resultsFirstPostDateStruct":{"date":"2026-09-12"}}},
            "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[
                {"type":"PRIMARY","title":"Clinical response",
                 "analyses":[{"pValue":"0.02","statisticalMethod":"Fisher"}]},
                {"type":"SECONDARY","title":"Exploratory",
                 "analyses":[{"pValue":"0.001"}]}
            ]}}}
        o=evidence_from_study("NCT87654321",study,"2026-10-10T01:00:00Z")
        self.assertEqual(len(o),1)
        self.assertEqual(o[0]["p_value"],"0.02")
        self.assertEqual(o[0]["result_first_posted"],"2026-09-12")
        study["protocolSection"]["designModule"]["phases"]=["PHASE3"]
        self.assertEqual(evidence_from_study("NCT87654321",study,"2026-10-10"),[])
        study["protocolSection"]["designModule"]["phases"]=["PHASE2"]
        study["protocolSection"]["statusModule"]["resultsFirstPostDateStruct"]={}
        self.assertEqual(evidence_from_study("NCT87654321",study,"2026-10-10"),[])

    def test_links_phase2_to_matching_phase3_record(self):
        rows=[{"phases":"PHASE3","nct_id":"NCT12345678",
               "phase2_nct_ids":"NCT87654321 | NCT87654322","ticker":"ABC",
               "program_key":"ABC|drug|condition"},
              {"phases":"PHASE2","nct_id":"NCT99999999",
               "phase2_nct_ids":"NCT00000001","ticker":"ABC"}]
        links=linked_trials(rows)
        self.assertEqual(len(links),2)
        self.assertEqual(links["NCT87654321"],
                         {("NCT12345678","ABC","ABC|drug|condition")})


if __name__=="__main__":
    unittest.main()
