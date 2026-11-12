"""Offline phase-first tests for L6 clinical/preclinical/regulatory evidence gap inventory."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("l6",ROOT/"scripts/level6_cross_disciplinary_inventory.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

NCT="NCT05507203"
def fixture(phase="PHASE3",nct=NCT):
    return ({
        "protocolSection":{
            "identificationModule":{"nctId":nct},
            "designModule":{"studyType":"INTERVENTIONAL","phases":[phase]},
            "statusModule":{"overallStatus":"RECRUITING"},
            "outcomesModule":{"primaryOutcomes":[{"measure":"Disease score","timeFrame":"12 weeks"}]},
            "referencesModule":{"references":[{"pmid":"12345678","citation":"unverified lead"}]}
        }
    },{"nct":nct,"source_url":"https://clinicaltrials.gov/api/v2/studies/"+nct,
       "sha256":"a"*64,"retrieved_at_utc":"2026-11-12T18:00:00Z"})

class CrossDomainTests(unittest.TestCase):
    def test_clinical_source_exact_receipt_but_other_domains_unverified(self):
        record,receipt=fixture()
        result=M.collect(record,receipt)
        self.assertEqual(result["clinical_sources"][0]["source_sha256"],"a"*64)
        self.assertEqual(result["clinical_sources"][0]["source_url"],receipt["source_url"])
        self.assertEqual(result["preclinical_sources"],[])
        self.assertEqual(result["regulatory_sources"],[])
        self.assertFalse(result["clinical_preclinical_regulatory_integrated"])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertIsNone(result["fda_prediction"])

    def test_phase2_does_not_require_nda_application_records(self):
        record,receipt=fixture("PHASE2")
        result=M.collect(record,receipt)
        self.assertEqual(result["registry_phase_context"]["phase_bucket"],"PHASE2")
        self.assertEqual(result["missing_or_unverified_by_phase"]["regulatory_sources"],
                         "APPLICATION_DOCUMENTS_NOT_YET_EXPECTED_BY_TRIAL_PHASE")
        self.assertEqual(result["missing_or_unverified_by_phase"]["nonpublic_CMC_or_inspection"],
                         "UNKNOWN_NOT_A_DEFICIENCY")

    def test_phase3_not_assumed_nda_filed(self):
        record,receipt=fixture()
        result=M.collect(record,receipt)
        self.assertEqual(result["missing_or_unverified_by_phase"]["regulatory_sources"],
                         "APPLICATION_STATUS_UNKNOWN_NOT_PROOF_OF_MISSING_FILING")
        self.assertFalse(result["application_level_linkage_verified"])

    def test_missing_phase_not_treated_as_negative(self):
        record,receipt=fixture()
        record["protocolSection"]["designModule"].pop("phases")
        result=M.collect(record,receipt)
        self.assertEqual(result["registry_phase_context"]["phase_bucket"],
                         "UNKNOWN_OR_NOT_APPLICABLE")
        self.assertIn("UNKNOWN",result["missing_or_unverified_by_phase"]["regulatory_sources"])
        self.assertIsNone(result["approval_probability"])

    def test_bibliography_is_not_counted_as_preclinical_primary_evidence(self):
        record,receipt=fixture()
        result=M.collect(record,receipt)
        self.assertEqual(result["registry_reference_count"],1)
        self.assertEqual(result["registry_references"]["source_evidence_count"],0)
        self.assertEqual(result["preclinical_sources"],[])

    def test_original_source_sha_url_and_trial_identity_fail_closed(self):
        record,receipt=fixture()
        bad=dict(receipt,sha256="bad")
        with self.assertRaises(ValueError):
            M.collect(record,bad)
        bad=dict(receipt,source_url="https://example.com/registry")
        with self.assertRaises(ValueError):
            M.collect(record,bad)
        record["protocolSection"]["identificationModule"]["nctId"]="NCT00000001"
        with self.assertRaises(ValueError):
            M.collect(record,receipt)

    def test_partial_batch_does_not_claim_domain_completion(self):
        def fetch(nct):
            if nct==NCT:return fixture()
            raise TimeoutError("no source")
        result=M.process_ncts([NCT,"NCT00000001"],fetcher=fetch)
        self.assertEqual(result["total"],2)
        self.assertEqual(result["retrieved"],1)
        self.assertFalse(result["scientific_level_complete"])
        self.assertEqual(result["preclinical_primary_sources_verified"],0)
        self.assertEqual(result["regulatory_primary_sources_verified"],0)
        self.assertEqual(result["reports"][1]["status"],
                         "SOURCE_RETRIEVAL_OR_IDENTITY_VALIDATION_BLOCKED")

    def test_exact_nct_batch_32_cap_and_no_duplicate(self):
        with self.assertRaises(ValueError):
            M.process_ncts([NCT,NCT],fetcher=lambda x:fixture())
        with self.assertRaises(ValueError):
            M.process_ncts(["NCT٠٥٥٠٧٢٠٣"],fetcher=lambda x:fixture())
        with self.assertRaises(ValueError):
            M.process_ncts([f"NCT{i:08d}" for i in range(33)],
                           fetcher=lambda x:fixture())
        ids=[f"NCT{i:08d}" for i in range(1,33)]
        r=M.process_ncts(ids,fetcher=lambda n:fixture(nct=n))
        self.assertEqual(r["retrieved"],32)
        self.assertEqual(len(r["reports"]),32)
        self.assertTrue(all(x["clinical_preclinical_regulatory_integrated"] is False
                            for x in r["reports"]))

    def test_requested_nct_mismatch_never_counted_as_retrieved(self):
        r=M.process_ncts(["NCT00000001"],fetcher=lambda n:fixture(nct=NCT))
        self.assertEqual(r["retrieved"],0)
        self.assertEqual(r["reports"][0]["reason"],"ValueError")

if __name__=="__main__":
    unittest.main()
