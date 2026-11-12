"""Synthetic offline tests for Level 5 contrary-source challenge inventory."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec=importlib.util.spec_from_file_location("level5",ROOT/"scripts/level5_contradictory_evidence.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

NCT = "NCT05507203"
URL = "https://clinicaltrials.gov/api/v2/studies/"+NCT

def fixture():
    return ({
        "protocolSection": {
            "identificationModule": {"nctId":NCT},
            "statusModule":{"overallStatus":"COMPLETED"},
            "designModule": {"studyType":"INTERVENTIONAL","phases":["PHASE3"],
                "designInfo":{"allocation":"RANDOMIZED","maskingInfo":{"masking":"DOUBLE"}}},
            "outcomesModule":{"primaryOutcomes":[
                {"measure":"Primary score","timeFrame":"Week 12"},
                {"measure":"Remission rate","timeFrame":"Week 12"}]}
        },
        "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[
            {"type":"PRIMARY","measure":"Primary score","timeFrame":"Week 12",
             "analyses":[{"pValue":"0.04"}]},
            {"type":"PRIMARY","measure":"Alternative score","timeFrame":"Week 12"}
        ]}}
    }, {"nct":NCT,"source_url":URL,"sha256":"a"*64,
        "retrieved_at_utc":"2026-11-12T15:00:00+00:00"})

class ChallengeTests(unittest.TestCase):
    def test_observed_endpoint_mismatch_is_only_a_review_lead(self):
        record,receipt=fixture()
        out=M.collect(record,receipt)
        self.assertEqual(out["nct"],NCT)
        self.assertEqual(out["observed_original_source"]["registry_endpoint_textual_mismatch_candidates"],2)
        self.assertEqual(len([x for x in out["candidate_challenges"] if "ENDPOINT" in x["flag"]]),2)
        self.assertEqual(out["source"]["raw_sha256"],"a"*64)
        self.assertFalse(out["contradiction_independently_verified"])
        self.assertFalse(out["negative_evidence_adjudicated"])
        self.assertFalse(out["scientific_stage_complete"])
        self.assertIsNone(out["fda_prediction"])

    def test_registry_result_missing_is_data_gap_not_negative_findings(self):
        record,receipt=fixture()
        del record["resultsSection"]
        out=M.collect(record,receipt)
        self.assertEqual(out["observed_original_source"]["registry_posted_primary_outcome_count"],0)
        self.assertIn("POSTED_PRIMARY_RESULTS_ABSENT",
                      [x["flag"] for x in out["candidate_challenges"]])
        self.assertFalse(out["negative_evidence_adjudicated"])
        self.assertIsNone(out["approval_probability"])

    def test_terminated_status_is_not_fda_failure(self):
        record,receipt=fixture()
        record["protocolSection"]["statusModule"]["overallStatus"]="TERMINATED"
        out=M.collect(record,receipt)
        flags=[x for x in out["candidate_challenges"] if x["flag"]=="REGISTRY_OVERALL_STATUS_REQUIRES_CONTEXT"]
        self.assertEqual(len(flags),1)
        self.assertEqual(flags[0]["observed_status"],"TERMINATED")
        self.assertIn("NOT_PROOF",flags[0]["interpretation"])
        self.assertFalse(out["scientific_stage_complete"])

    def test_exact_original_source_identity_and_hash_required(self):
        record,receipt=fixture()
        record["protocolSection"]["identificationModule"]["nctId"]="NCT00000002"
        with self.assertRaises(ValueError):
            M.collect(record,receipt)
        record["protocolSection"]["identificationModule"]["nctId"]=NCT
        receipt["sha256"]="unknown"
        with self.assertRaises(ValueError):
            M.collect(record,receipt)

    def test_non_randomized_allocation_is_a_limit_review_lead(self):
        record,receipt=fixture()
        record["protocolSection"]["designModule"]["designInfo"]["allocation"]="NON_RANDOMIZED"
        out=M.collect(record,receipt)
        self.assertIn("TRIAL_DESIGN_LIMITATION_REVIEW_LEAD",
                      [x["flag"] for x in out["candidate_challenges"]])
        self.assertFalse(out["study_limitations_independently_adjudicated"])

    def test_batch_continues_when_one_original_source_unavailable(self):
        record,receipt=fixture()
        def fetch(nct):
            if nct==NCT: return record,receipt
            raise TimeoutError("registry unavailable")
        result=M.process_ncts([NCT,"NCT00000002"],fetcher=fetch)
        self.assertEqual(result["retrieved"],1)
        self.assertEqual(result["total"],2)
        self.assertEqual(result["reports"][1]["status"],"ORIGINAL_SOURCE_UNAVAILABLE_OR_INVALID")
        self.assertFalse(result["scientific_level_complete"])
        with self.assertRaises(ValueError):
            M.process_ncts([NCT,NCT],fetcher=fetch)
        with self.assertRaises(ValueError):
            M.process_ncts(["NCT٠٥٥٠٧٢٠٣"],fetcher=fetch)

    def test_current_state_never_poses_as_outcome_blind_historical_data(self):
        record,receipt=fixture()
        out=M.collect(record,receipt,historical_cutoff="2026-01-01")
        self.assertEqual(out["source"]["source_revision"],"CURRENT_STATE_NOT_HISTORICAL_FREEZE")
        self.assertEqual(out["source"]["requested_as_of"],"2026-01-01")
        self.assertEqual(out["historical_blinding"],"CURRENT_REGISTRY_NOT_AS_OF_CUTOFF")
        self.assertIsNone(out["clinical_score"])

    def test_no_contradiction_proof_when_all_text_matches(self):
        record,receipt=fixture()
        record["protocolSection"]["outcomesModule"]["primaryOutcomes"]=[{
            "measure":"Primary score","timeFrame":"Week 12"}]
        record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]=[{
            "type":"PRIMARY","measure":"Primary score","timeFrame":"Week 12"}]
        out=M.collect(record,receipt)
        self.assertEqual(out["observed_original_source"]["registry_endpoint_textual_mismatch_candidates"],0)
        self.assertFalse(out["source_facts_independently_verified"])
        self.assertFalse(out["scientific_stage_complete"])

if __name__=="__main__":
    unittest.main()
