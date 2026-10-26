import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_phase3_original_registry_pilot import (
    SOURCE_CSV, STATUSES, dated_census_sample, extract_original_study,
    fetch_public_original, run_pilot,
)


class Phase3RegistryOriginalPilotTests(unittest.TestCase):
    def setUp(self):
        self.samples = dated_census_sample(SOURCE_CSV.read_text(encoding="utf-8-sig"))
        self.example = self.samples[0]
        self.payload = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": self.example["nct_id"], "briefTitle": "Exact NCT study title"
                },
                "statusModule": {
                    "overallStatus": self.example["status"], "lastUpdatePostDate": "2026-01-11"
                },
                "designModule": {"phases": ["PHASE3"]},
                "sponsorCollaboratorsModule": {"leadSponsor": {"name": self.example["company"]}},
            }
        }

    def test_real_census_sampler_covers_eight_statuses_exact_nct_and_source(self):
        self.assertEqual(len(self.samples), len(STATUSES))
        self.assertEqual([item["status"] for item in self.samples], list(STATUSES))
        self.assertEqual(len({r["nct_id"] for r in self.samples}), 8)
        for row in self.samples:
            self.assertRegex(row["nct_id"], r"^NCT\d{8}$")
            self.assertEqual(row["source_url"],
                             "https://clinicaltrials.gov/study/" + row["nct_id"])

    def test_identity_checked_source_never_promotes_pipeline_or_fda(self):
        raw = json.dumps(self.payload).encode("utf-8")
        source = extract_original_study(raw, self.example, "2026-10-26T14:00:00+00:00")
        self.assertEqual(source["nct_id"], self.example["nct_id"])
        self.assertEqual(source["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(source["status_matches_dated_census"])
        self.assertTrue(source["phase3_in_current_registry"])
        self.assertEqual(source["qualified_pipeline"], None)
        self.assertEqual(source["fda_approval_probability"], None)
        self.assertFalse(source["verified_us_fda_pdufa"])
        self.assertFalse(source["verified_current_commercial_development_rights"])

    def test_registry_changed_status_is_a_warning_not_disqualification_or_promotion(self):
        self.payload["protocolSection"]["statusModule"]["overallStatus"] = "SUSPENDED"
        r = extract_original_study(json.dumps(self.payload).encode(), self.example, "2026-10-26T14:00:00Z")
        self.assertFalse(r["status_matches_dated_census"])
        self.assertIsNone(r["qualified_pipeline"])
        self.assertEqual(r["current_registry_status"], "SUSPENDED")

    def test_wrong_study_missing_identity_or_bad_json_fail_closed(self):
        for invalid in ["NCT00000000", "", "NCT123"]:
            self.payload["protocolSection"]["identificationModule"]["nctId"] = invalid
            with self.assertRaisesRegex(ValueError, "NCT identity mismatch"):
                extract_original_study(json.dumps(self.payload).encode(), self.example, "2026-10-26T14:00:00Z")
        with self.assertRaisesRegex(ValueError, "not JSON"):
            extract_original_study(b"<html>login</html>", self.example, "2026-10-26T14:00:00Z")
        with self.assertRaisesRegex(ValueError, "size blocked"):
            extract_original_study(b"x" * 800001, self.example, "2026-10-26T14:00:00Z")

    def test_incomplete_or_forged_census_does_not_start_network_fetch(self):
        original = SOURCE_CSV.read_text(encoding="utf-8")
        for bad in [
            original[:-120],
            original.replace("nct_id,ticker,company,status,source_url", "nct_id,ticker,company,pdufa,source_url"),
            original.replace("NCT", "FCT", 1),
            original.replace("RECRUITING", "APPROVED", 1),
        ]:
            with self.assertRaises(ValueError):
                dated_census_sample(bad)

    def test_report_on_source_failure_retains_unknown_qualification_and_includes_all_eight_groups(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch("check_phase3_original_registry_pilot._fetch_catching",
                       side_effect=lambda row: {"nct_id": row["nct_id"], "error": "URLError"}):
                report_path = Path(tmp) / "evidence.json"
                result = run_pilot(report_path)
            self.assertEqual(result, 1)
            saved = json.loads(report_path.read_text())
            self.assertEqual(saved["sample_size"], 8)
            self.assertEqual(len(saved["source_errors"]), 8)
            self.assertEqual(saved["original_source_records"], [])
            self.assertFalse(saved["source_connection_operational"])
            self.assertIsNone(saved["qualified_pipeline_total"])
            self.assertIsNone(saved["verified_us_fda_pdufa_count"])
            self.assertIsNone(saved["validated_approval_probabilities"])

    def test_network_request_has_fixed_origin_no_redirect_and_read_only_get(self):
        import inspect
        code = inspect.getsource(fetch_public_original)
        self.assertIn('f"{ORIGIN}/api/v2/studies/{nct}"', code)
        self.assertIn('method="GET"', code)
        self.assertIn("timeout=15", code)
        self.assertNotIn("PDUFA_INTERNAL_API_KEY", code)
        self.assertNotIn("POST", code)


if __name__ == "__main__":
    unittest.main()
