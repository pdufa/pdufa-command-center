"""Exact-NCT source evidence collector tests: no invented trial results or scores."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "scripts/raas_collect_registry_evidence.py"
spec = importlib.util.spec_from_file_location("raas_collect_registry_evidence", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
row = {"nct_id":"NCT12345678","ticker":"TEST","company":"Test Therapeutics",
       "status":"COMPLETED","source_url":"https://clinicaltrials.gov/study/NCT12345678"}

def protocol(nct="NCT12345678", posted=False):
    data={"protocolSection":{
      "identificationModule":{"nctId":nct},
      "statusModule":{"overallStatus":"COMPLETED","lastUpdatePostDate":"2026-10-30"},
      "designModule":{"phases":["PHASE3"]},
      "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Test Sponsor"}},
      "armsInterventionsModule":{"interventions":[{"name":"Study drug"}]},
      "conditionsModule":{"conditions":["Test condition"]},
      "outcomesModule":{"primaryOutcomes":[{"measure":"Primary endpoint","timeFrame":"Week 12"}]}},
      "hasResults":posted}
    if posted:
        data["resultsSection"]={"outcomeMeasuresModule":{"outcomeMeasures":[
          {"type":"PRIMARY","title":"Primary endpoint","timeFrame":"Week 12",
           "analyses":[{"pValue":"0.03","statisticalMethod":"ANOVA"}]}]},
          "adverseEventsModule":{"seriousEvents":[{"term":"Serious event"}]}}
    return data

class ClinicalSourceCollectorTests(unittest.TestCase):
    def test_registry_protocol_is_not_efficacy_result_or_rating(self):
        r=mod.canonical_result(protocol(),row,"2026-11-04T14:00:00Z","a"*64)
        self.assertEqual(r["evidenceState"],"REGISTRY_PROTOCOL_ONLY")
        self.assertEqual(r["registeredPrimaryEndpoints"][0]["measure"],"Primary endpoint")
        self.assertFalse(r["postedResults"])
        self.assertEqual(r["reportedStatisticalAnalyses"],0)
        self.assertIsNone(r["raasOverallScore"])
        self.assertIsNone(r["verifiedPipeline"])

    def test_only_posted_result_records_supply_analyses(self):
        r=mod.canonical_result(protocol(posted=True),row,"2026-11-04T14:00:00Z","b"*64)
        self.assertEqual(r["evidenceState"],"POSTED_RESULTS")
        self.assertEqual(r["reportedStatisticalAnalyses"],1)
        self.assertEqual(r["reportedPValuesInSample"],1)
        self.assertEqual(r["reportedOutcomeMeasures"][0]["analyses"][0]["pValue"],"0.03")
        self.assertIsNone(r["raasOverallScore"])

    def test_fail_closed_on_identity_and_results_flag(self):
        with self.assertRaisesRegex(ValueError,"NCT_MISMATCH"):
            mod.canonical_result(protocol("NCT99999999"),row,"2026-11-04T14:00:00Z","a")
        bad=protocol()
        bad["resultsSection"]={"outcomeMeasuresModule":{"outcomeMeasures":[{"title":"Made up"}]}}
        with self.assertRaisesRegex(ValueError,"FLAG_CONFLICT"):
            mod.canonical_result(bad,row,"2026-11-04T14:00:00Z","a")

    def test_strict_population_input_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"cohort.csv"
            line="nct_id,ticker,company,status,source_url\\n"
            record="NCT12345678,TEST,Test Therapeutics,COMPLETED,https://clinicaltrials.gov/study/NCT12345678\\n"
            path.write_text(line+record)
            self.assertEqual(len(mod.load_cohort(path)),1)
            path.write_text(line+record+record)
            with self.assertRaisesRegex(ValueError,"duplicated"):
                mod.load_cohort(path)

    def test_reuse_cached_evidence_but_not_missing_or_stale(self):
        rows=[row, {**row,"nct_id":"NCT12345679","source_url":"https://clinicaltrials.gov/study/NCT12345679"}]
        good=mod.canonical_result(protocol(),row,mod.current_day(),"a"*64)
        prior={"records":[good]}
        def fetch(x):
            return {"nctId":x["nct_id"],"ticker":x["ticker"],
                    "evidenceState":"FETCH_FAILED","postedResults":None,
                    "sourceError":"HTTP_404","raasOverallScore":None,"verifiedPipeline":None}
        with patch.object(mod,"fetch_one",side_effect=fetch) as mock:
            out=mod.collect(rows,prior,max_age_days=7,workers=2)
        self.assertEqual(mock.call_count,1)
        self.assertEqual(out["summary"]["totalNctIds"],2)
        self.assertEqual(out["summary"]["usableRegistryRecords"],1)
        self.assertEqual(out["summary"]["unavailableSourceRecords"],1)
        self.assertEqual(out["summary"]["overallRaasScores"],0)

if __name__=="__main__":
    unittest.main()
