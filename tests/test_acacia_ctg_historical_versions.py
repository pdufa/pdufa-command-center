"""Synthetic guard tests and offline checks of preserved original public-source receipts."""
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
    def test_fetch_keeps_exact_source_bytes_matching_digest(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import hashlib
        raw=b'{  "studyVersion": 25, "note": "original whitespace" }\n'
        class Response:
            url="https://clinicaltrials.gov/api/int/studies/NCT06081894/history/25"
            headers={"content-type":"application/json"}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return raw
        with TemporaryDirectory() as tmp, patch.object(module.urllib.request,"urlopen",return_value=Response()):
            artifact=Path(tmp)/"original.json"
            parsed,digest=module.fetch(Response.url,artifact=artifact)
            self.assertEqual(parsed["studyVersion"],25)
            self.assertEqual(artifact.read_bytes(),raw)
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),digest)

    def test_original_version_and_date_must_both_match_not_just_url(self):
        body={"studyVersion":25,"study":study(["KCCQ-CSS"])}
        body["study"]["protocolSection"]["statusModule"]["lastUpdateSubmitDate"]="2025-01-11"
        self.assertEqual(len(module.validate_original_version(body,25,"2025-01-11")["primary"]),1)
        with self.assertRaisesRegex(ValueError,"VERSION_ID_MISMATCH"):
            module.validate_original_version(body,26,"2025-05-15")
        with self.assertRaisesRegex(ValueError,"SUBMISSION_DATE_MISMATCH"):
            module.validate_original_version(body,25,"2026-09-21")
        del body["studyVersion"]
        with self.assertRaisesRegex(ValueError,"VERSION_ID_MISMATCH"):
            module.validate_original_version(body,25,"2025-01-11")

    def test_original_definitions_are_not_truncated_or_silently_dropped(self):
        record=study(["Original endpoint"])
        record["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["description"]="x"*1900
        self.assertEqual(len(module.safe_outcomes(record)["primary"][0]["description"]),1900)
        record["protocolSection"]["outcomesModule"]["primaryOutcomes"].append(None)
        with self.assertRaisesRegex(ValueError,"MALFORMED_ORIGINAL_ENDPOINT"):
            module.safe_outcomes(record)

    def test_description_changes_are_visible_even_when_endpoint_titles_match(self):
        before=module.safe_outcomes(study(["Same title"]))
        after=module.safe_outcomes(study(["Same title"]))
        after["primary"][0]["description"]="Changed definition with the same title"
        delta=module.verified_primary_endpoint_delta(before,after)
        self.assertEqual(len(delta["primaryDescriptionChanges"]),1)
        self.assertEqual(delta["primaryMeasureAdded"],[])

    def test_real_public_browser_receipts_crosscheck_all_four_versions(self):
        from tempfile import TemporaryDirectory
        import shutil
        original=Path(__file__).resolve().parents[1]/"docs/medical-review-pilot-20261108/revision36-original-history"
        with TemporaryDirectory() as tmp:
            shutil.copytree(original,tmp,dirs_exist_ok=True)
            result=module.reconcile_public_browser_capture(tmp)
            self.assertEqual((result["directV26V27"]["primaryBefore"],result["directV26V27"]["primaryAfter"]),(1,2))
            self.assertEqual((result["directV29V30"]["primaryBefore"],result["directV29V30"]["primaryAfter"]),(2,2))
            self.assertEqual(result["gradedMethods"],0)
            p=Path(tmp)/"v26_original_registry.json"
            p.write_bytes(p.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError,"DIGEST_MISMATCH"):
                module.reconcile_public_browser_capture(tmp)

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
