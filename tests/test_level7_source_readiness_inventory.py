"""No fabricated model predictions or FDA outcomes in Level 7 engineering."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import level7_source_readiness_inventory as M

NCTS=[f"NCT{n:08d}" for n in range(1,33)]
BLOB="b"*40
NOW="2026-11-12T12:00:00+00:00"

def case(nct,phase="PHASE3"):
    return {
        "nct": nct, "status": M.LEAD_STATUS,
        "registry_phase_context": {"phase_bucket":phase},
        "clinical_preclinical_regulatory_integrated":False,
        "clinical_sources":[{
            "domain":"CLINICAL_REGISTRY_ONLY",
            "source_url":"https://clinicaltrials.gov/study/"+nct,
            "source_sha256":"a"*64,
            "retrieved_at_utc":"2026-11-11T23:00:00Z",
            "source_revision":"CURRENT_STATE_NOT_HISTORICAL_FREEZE",
            "verified_receipt":True,
            "independently_reviewed":False,
        }],
    }

def payload():
    return {"level":6,"retrieved":32,"total":32,"reports":[case(nct) for nct in NCTS]}

class Level7SourceAudit(unittest.TestCase):
    def run_inventory(self, val=None):
        return M.inventory(payload() if val is None else val,ncts=NCTS,
                           freeze_as_of="2026-11-11",source_roster_blob_sha1=BLOB)

    def test_32_original_registry_receipts_preserved(self):
        r=self.run_inventory()
        self.assertEqual(r["exact_nct_identity_matched"],32)
        self.assertEqual(r["original_registry_receipts_audited"],32)
        self.assertEqual(len(r["case_reports"]),32)
        self.assertEqual(r["source_roster_git_blob_sha1"],BLOB)
        self.assertEqual(r["status"],"MODEL_VALIDATION_EVIDENCE_GAPS_INVENTORIED_NOT_PREDICTIONS")

    def test_phase_appropriate_uncertainty_not_misclassified_as_fda_failure(self):
        p=payload()
        p["reports"][0]=case(NCTS[0],phase="PHASE2")
        r=self.run_inventory(p)
        self.assertEqual(r["phase_context"][0]["phase_bucket"],"PHASE2")
        self.assertTrue(r["phase_context"][0]["not_yet_expected_phase_data_is_not_a_failure"])
        self.assertFalse(r["phase_context"][0]["fda_application_identity_verified"])
        self.assertFalse(r["current_canonical_focus_verified"])

    def test_future_registry_does_not_satisfy_outcome_blind_history(self):
        r=self.run_inventory()
        self.assertEqual(r["historical_pre_cutoff_source_freezes_verified"],0)
        self.assertEqual(r["outcome_blind_historical_validations_performed"],0)
        self.assertTrue(all(x["registry_current_state_not_historical_freeze"]
                            for x in r["phase_context"]))

    def test_no_training_calibration_or_approval_predictions(self):
        r=self.run_inventory()
        for x in ("calibration_evidence_verified","model_validation_plan_approved",
                  "predictive_model_trained","approval_probabilities_generated",
                  "scientific_level_complete","independently_reviewed"):
            self.assertFalse(r[x],x)
        self.assertEqual(r["source_publication_dates_independently_verified"],0)
        self.assertTrue(all(x["fda_probability"] is None for x in r["case_reports"]))
        self.assertTrue(all(not x["eligible_for_blinded_model_input"] for x in r["case_reports"]))

    def test_unverified_publication_time_not_claimed_to_be_known(self):
        r=self.run_inventory()
        self.assertTrue(all("SOURCE_ACCESS_OR_PUBLICATION_DATE_UNVERIFIED"
                            in x["review_leads"] for x in r["case_reports"]))

    def test_registry_identity_mismatch_rejected(self):
        p=payload()
        p["reports"][0]["nct"]="NCT99999999"
        with self.assertRaisesRegex(ValueError,"Unexpected Level6 original trial ID"):
            self.run_inventory(p)

    def test_unverified_hash_and_wrong_source_domain_fail(self):
        for key,value in (("source_sha256","abc"),("domain","FDA_APPLICATION"),
                          ("source_url","https://bad.example.org")):
            with self.subTest(key=key):
                p=payload()
                p["reports"][0]["clinical_sources"][0][key]=value
                with self.assertRaises(ValueError):
                    self.run_inventory(p)

    def test_fake_approvals_and_source_flags_fail(self):
        for key,value in (("verified_receipt",False),("independently_reviewed",True)):
            with self.subTest(key=key):
                p=payload()
                p["reports"][0]["clinical_sources"][0][key]=value
                with self.assertRaises(ValueError):
                    self.run_inventory(p)
        p=payload()
        p["reports"][0]["clinical_preclinical_regulatory_integrated"]=True
        with self.assertRaises(ValueError):
            self.run_inventory(p)

    def test_missing_one_registry_receipt_blocks(self):
        p=payload()
        p["reports"].pop()
        p["retrieved"]=31
        with self.assertRaisesRegex(ValueError,"incomplete"):
            self.run_inventory(p)

    def test_duplicate_nct_blocks_and_roster_reordering_not_accepted(self):
        p=payload()
        p["reports"][1]=copy.deepcopy(p["reports"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            self.run_inventory(p)

    def test_invalid_phase_and_source_timestamp_fail(self):
        p=payload()
        p["reports"][0]["registry_phase_context"]["phase_bucket"]="PHASE9"
        with self.assertRaisesRegex(ValueError,"phase classification"):
            self.run_inventory(p)
        p=payload()
        p["reports"][0]["clinical_sources"][0]["retrieved_at_utc"]="2026-11-11"
        with self.assertRaises(ValueError):
            self.run_inventory(p)

    def test_invalid_nct_roster_and_source_blob_fail_closed(self):
        for ids,sha in [(NCTS[:31],BLOB),(NCTS,"wrong")]:
            with self.assertRaises(ValueError):
                M.inventory(payload(),ncts=ids,freeze_as_of="2026-11-11",
                            source_roster_blob_sha1=sha)

if __name__=="__main__":
    unittest.main()
