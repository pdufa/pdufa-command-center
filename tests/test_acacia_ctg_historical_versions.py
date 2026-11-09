"""Exact, synthetic-only tests for independent official historical endpoint-diff guard."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/medical/acacia_ctg_historical_versions.py"
spec = importlib.util.spec_from_file_location("acacia_ctg_historical_versions", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def study(primary, enrollment=420, nct="NCT06081894"):
    return {"protocolSection":{
        "identificationModule":{"nctId":nct},
        "outcomesModule":{"primaryOutcomes":[{"measure":n,"timeFrame":"Week 36","description":"Recorded original endpoint definition"} for n in primary]},
        "designModule":{"enrollmentInfo":{"count":enrollment},"phases":["PHASE3"]},
        "statusModule":{"overallStatus":"ACTIVE_NOT_RECRUITING"}
    }}

class OfficialVersionGuardTests(unittest.TestCase):
    def test_original_two_version_diff_identifies_change_without_clinical_judgment(self):
        before=module.safe_outcomes(study(["KCCQ-CSS"],420))
        after=module.safe_outcomes(study(["KCCQ-CSS","Peak VO2"],500))
        a=module.verified_primary_endpoint_delta(before,after)
        self.assertEqual((a["primaryBefore"],a["primaryAfter"]),(1,2))
        self.assertEqual(a["primaryMeasureAdded"],[{"measure":"Peak VO2","timeFrame":"Week 36"}])
        self.assertEqual(a["primaryMeasureRemoved"],[])
        self.assertEqual((a["enrollmentBefore"]["count"],a["enrollmentAfter"]["count"]),(420,500))
        self.assertTrue(a["originalVersionTextsVerifiedByApi"])
        self.assertEqual(a["clinicalIntegrityJudgment"],"AWAITING_FULL_PROTOCOL_SAP_TIMELINE_ADJUDICATION")
    def test_same_text_changes_nothing(self):
        x=module.safe_outcomes(study(["KCCQ-CSS"]))
        y=module.verified_primary_endpoint_delta(x,x)
        self.assertEqual(y["primaryMeasureAdded"],[])
        self.assertEqual(y["primaryMeasureRemoved"],[])
    def test_source_cross_trial_rejected(self):
        with self.assertRaisesRegex(ValueError,"CROSS_STUDY_ID_MISMATCH"):
            module.safe_outcomes(study(["Endpoint"],nct="NCT99999999"))
    def test_missing_endpoints_fail_closed(self):
        with self.assertRaises(ValueError):
            module.verified_primary_endpoint_delta({"primary":None},{"primary":[]})
        with self.assertRaises(ValueError):
            module.verified_primary_endpoint_delta({"primary":[{"measure":""}]},{"primary":[]})
    def test_duplicate_endpoint_is_not_valid_source(self):
        with self.assertRaises(ValueError):
            module.verified_primary_endpoint_delta({"primary":[{"measure":"A"},{"measure":"A"}]},{"primary":[]})
    def test_version_labels_are_the_documented_official_dates(self):
        self.assertEqual(module.NCT,"NCT06081894")
        self.assertEqual(module.VERSIONS[25],("v26","2025-01-11"))
        self.assertEqual(module.VERSIONS[26],("v27","2025-05-15"))
        self.assertEqual(module.VERSIONS[28],("v29","2026-01-29"))
        self.assertEqual(module.VERSIONS[29],("v30","2026-08-03"))

if __name__=="__main__":
    unittest.main()
