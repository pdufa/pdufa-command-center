"""Offline safeguards for new-ticker/NCT identities retained in published scan reports."""
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import phase3_results_intake as intake
from scripts import nightly_clinical_collection as runner
from scripts import pdufa_scan_audit as audit

DETAIL = {
    "ticker": "TEST", "drug": "Investigational antibody",
    "nct_id": "NCT01234567", "results_posted_at": "2026-10-19",
    "source_url": "https://clinicaltrials.gov/study/NCT01234567",
    "verification_status": "REGISTERED_RESULTS_POSTED",
}


class NewResultIdentitiesTests(unittest.TestCase):
    def test_intake_retains_exact_new_registry_identity_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (root / "company_registry.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["company", "ticker"])
                writer.writeheader()
                writer.writerow({"company": "Example Biotech", "ticker": "TEST"})
            study = {"protocolSection": {
                "identificationModule": {"nctId": "NCT01234567"},
                "statusModule": {"resultsFirstPostDateStruct": {"date": "2026-10-19"}},
                "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Biotech"}},
                "designModule": {"phases": ["PHASE3"]},
                "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Investigational antibody"}]},
                "conditionsModule": {"conditions": ["Study condition"]},
            }}
            with patch.object(intake,"fetch",return_value={"studies":[study]}):
                intake.scan("daily",1,root)
                first=json.loads((root/"phase3_intake_status.json").read_text())
                self.assertEqual(first["new_records"],1)
                self.assertEqual(first["new_record_details"][0]["ticker"],"TEST")
                self.assertEqual(first["new_record_details"][0]["nct_id"],"NCT01234567")
                self.assertEqual(first["new_record_details"][0]["source_url"],DETAIL["source_url"])
                self.assertEqual(first["stored_results"],1)
                intake.scan("daily",1,root)
                second=json.loads((root/"phase3_intake_status.json").read_text())
                self.assertEqual(second["new_records"],0)
                self.assertEqual(second["new_record_details"],[])

    def test_only_complete_gem_jr_collection_passes_new_identity_rows(self):
        source={"status":"COMPLETE","new_records":1,"new_record_details":[DETAIL],"errors":[]}
        output=runner.summarize("4",source,0,True)
        self.assertEqual(output["new_record_details"],[DETAIL])
        self.assertNotIn("new_record_details",runner.summarize("4",source,1,True))
        self.assertNotIn("new_record_details",runner.summarize("4",source,0,False))
        self.assertNotIn("new_record_details",runner.summarize("3",source,0,True))

    def audit_row(self,details,source_details=None):
        report={
            "scan":"4","scan_kind":"CLINICAL_SOURCE_COLLECTION_ONLY",
            "full_coverage_verified":False,"collector_status":"COMPLETE",
            "collector_exit_code":0,"status":"PARTIAL","errors_count":0,
            "new_records":1,"new_record_details":details,
            "created_at_utc":"2026-10-20T04:33:25Z"
        }
        state={"status":"COMPLETE","errors":[],"new_records":1,
               "new_record_details":details if source_details is None else source_details}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/"reports").mkdir()
            (root/"data").mkdir()
            (root/"reports/nightly-clinical-4.json").write_text(json.dumps(report))
            (root/"data/phase3_intake_status.json").write_text(json.dumps(state))
            return audit.inspect_artifact("4",{}, "unused",extracted_dir=root)

    def test_audit_publishes_exact_source_matched_identity(self):
        result=self.audit_row([DETAIL])
        self.assertEqual(result["artifact_integrity"],"PASS")
        self.assertEqual(result["new_record_details"],[DETAIL])
        self.assertEqual(result["new_records"],1)

    def test_audit_rejects_substituted_ticker_duplicate_or_invalid_link(self):
        for detail,reason in (
            ({**DETAIL,"source_url":"https://example.test/study/NCT01234567"},"link"),
            ({**DETAIL,"nct_id":"not-an-NCT"},"nct"),
            ({**DETAIL,"ticker":"INVALID TICKER"},"ticker"),
        ):
            with self.subTest(reason=reason):
                result=self.audit_row([detail])
                self.assertNotEqual(result["artifact_integrity"],"PASS")
                self.assertEqual(result["new_record_details"],[])
        conflict=self.audit_row([DETAIL],[{**DETAIL,"ticker":"OTHER"}])
        self.assertEqual(conflict["artifact_integrity"],"ISSUES")
        self.assertEqual(conflict["new_record_details"],[])

    def test_missing_identity_details_on_historical_reports_do_not_fabricate_tickers(self):
        report={
            "scan":"4","scan_kind":"CLINICAL_SOURCE_COLLECTION_ONLY",
            "full_coverage_verified":False,"collector_status":"COMPLETE",
            "collector_exit_code":0,"status":"PARTIAL","errors_count":0,
            "new_records":1,"created_at_utc":"2026-10-20T04:33:25Z"
        }
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/"reports").mkdir()
            (root/"data").mkdir()
            (root/"reports/nightly-clinical-4.json").write_text(json.dumps(report))
            (root/"data/phase3_intake_status.json").write_text(json.dumps({"status":"COMPLETE","errors":[]}))
            result=audit.inspect_artifact("4",{}, "unused",extracted_dir=root)
            self.assertEqual(result["new_records"],1)
            self.assertEqual(result["new_record_details"],[])
            self.assertEqual(result["artifact_integrity"],"PASS")


if __name__=="__main__":
    unittest.main()
