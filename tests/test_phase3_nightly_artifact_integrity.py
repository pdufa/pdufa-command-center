"""Nightly source artifact integrity tests: actual files, scope and hash checks."""
import csv
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from phase3_nightly_artifact_integrity import (
    EXPECTED_FILES, MANIFEST_NAME, make_manifest, verify_manifest,
    check_file, load_json,
)


def sample_runner_folder(root):
    ncts=[f"NCT{i:08d}" for i in range(1,742)]
    rows=[{"nct_id":nct, "source_sha256":hashlib.sha256(nct.encode()).hexdigest(),
           "census_ticker":"TEST", "current_registry_status":"RECRUITING",
           "status_matches_dated_census":True, "phase3_in_current_registry":True} for nct in ncts]
    status_rows=[{"nct_id":r["nct_id"], "registry_source_sha256":r["source_sha256"],
                 "census_ticker":r["census_ticker"],
                 "current_registry_status":r["current_registry_status"],
                 "status_matches_census":r["status_matches_dated_census"],
                 "phase3_in_current_registry":r["phase3_in_current_registry"],
                 "commercial_rights_verified":False, "qualified_pipeline":None}
                 for r in rows]
    def obj(name,**extra):
        return {"report_type":name,**extra}
    reports={
        "main_phase3_registry_status_recency.json":obj(
            "MAIN_PHASE3_REGISTRY_STATUS_SOURCE_RECENCY_RESEARCH_ONLY",
            historical_trial_count=741,source_identity_verified=741,
            source_posted_update_age_counts={"POSTED_LAST_90_DAYS":741,
                "POSTED_OVER_365_DAYS":0,"POSTED_DATE_MISSING":0},
            research_priority_counts={"P4_STANDARD_REGISTRY_REVIEW":741},
            registry_status_group_counts={"REGISTRY_ACTIVE_STATUS_ONLY":741},
            registry_status_changed_since_saved_census=0,
            not_currently_registered_as_phase3=0,
            original_source_posted_update_over_365_days=0,
            original_source_posted_update_missing=0,
            registration_freshness_gate_verified_count=0,
            independently_verified_commercial_rights=0,
            items=status_rows,qualified_pipeline_total=None),
        "main_phase3_registry.json": obj(
            "MAIN_ORIGINAL_PHASE3_FULL_CENSUS_RESEARCH_ONLY",
            census_total=741,source_identity_verified=741,source_errors=[],
            original_source_records=rows,qualified_pipeline_total=None),
        "main_phase3_qualification_ledger.json": obj(
            "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY",
            total=741,records=rows,qualified_pipeline_total=None),
        "main_phase3_sponsor_rights_queue.json":obj("SPONSOR_QUEUE_RESEARCH_ONLY",total=741),
        "main_phase3_rights_gaps.json":obj("RIGHTS_GAPS_RESEARCH_ONLY",total=741),
        "main_phase3_rights_casebook.json":obj(
            "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",total_trials=741,
            saved_issuer_pointers=130,rights_verified_trials=0,items=rows,
            qualified_pipeline_total=None),
        "main_phase3_program_identity.json":obj(
            "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY",
            total_trials=741,independently_verified_commercial_rights=0,
            items=rows,qualified_pipeline_total=None),
        "main_phase3_sec_rights_leads.json":obj(
            "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY",
            total_trials=741,total_issuers=130,issuer_metadata_fetched=130,
            issuers=[{"cik":i} for i in range(130)],trials=rows,
            qualified_pipeline_total=None),
        "main_phase3_sec_primary_documents_pilot.json":obj(
            "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY",
            total_trials=741,total_issuers=130,independently_verified_current_rights=0,
            documents_attempted=0,documents_retrieved=0,
            issuers=[{"cik":i} for i in range(130)],qualified_pipeline_total=None),
        "main_phase3_sec_trial_rights_join.json":obj(
            "MAIN_PHASE3_TRIAL_DRUG_SEC_RIGHTS_JOIN_RESEARCH_ONLY",
            total_trials=741,total_issuers=130,verified_current_commercial_rights=0,
            items=rows,qualified_pipeline_total=None),
        "main_phase3_rights_review_worklist.json":obj(
            "MAIN_PHASE3_COMMERCIAL_RIGHTS_REVIEW_WORKLIST_RESEARCH_ONLY",
            total_trials=741,total_issuer_research_pointers=130,
            independently_verified_current_rights=0,items=rows,
            qualified_pipeline_total=None),
        "main_phase3_rights_review_submissions_coverage.json":obj(
            "MAIN_PHASE3_RIGHTS_REVIEW_SUBMISSIONS_COVERAGE_RESEARCH_ONLY",
            trial_denominator=741,checklist_slot_denominator=4446,
            independently_verified_commercial_rights=0,
            distinct_review_slots_with_submissions=0,
            review_slots_without_submissions=4446,
            items=rows,qualified_pipeline_total=None),
        "main_phase3_qualification_scorecard.json":obj(
            "MAIN_PHASE3_QUALIFICATION_PROGRESS_SCORECARD_RESEARCH_ONLY",
            historical_trial_count=741,issuer_research_pointer_count=130,
            gate_checks_denominator=6669,gate_checks_pass=741,
            gate_checks_review=5928,gate_checks_fail=0,
            rights_review_checklist_slots=4446,rights_slots_with_submissions=0,
            rights_slots_without_submissions=4446,sec_issuer_indexes_fetched=130,
            sec_primary_documents_attempted=0,sec_primary_documents_fetched=0,
            independently_verified_current_rights_trials=0,
            qualified_trial_count=None,qualifying_pipeline_count=None),
    }
    for name,data in reports.items():
        (root/name).write_text(json.dumps(data),encoding="utf-8")
    with (root/"main_phase3_registry_status_review.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=[
            "nct_id","review_position","registry_source_sha256",
            "commercial_rights_verified","qualified_pipeline"])
        writer.writeheader()
        for i,row in enumerate(status_rows,1):
            writer.writerow({
                "nct_id":row["nct_id"],"review_position":i,
                "registry_source_sha256":row["registry_source_sha256"],
                "commercial_rights_verified":"False","qualified_pipeline":""
            })
    with (root/"main_phase3_rights_review_worklist.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=[
            "nct_id","review_position","commercial_rights_verified","qualified_pipeline"])
        writer.writeheader()
        for i,nct in enumerate(ncts,1):
            writer.writerow({"nct_id":nct,"review_position":i,
                             "commercial_rights_verified":"False",
                             "qualified_pipeline":""})
    (root/"main_phase3_qualification_summary.md").write_text(
        "# MAIN Phase 3 — research qualification progress\n"
        "| Mandatory gate checks verified PASS | 741/6669 |\n"
        "**Qualified Pipeline total:** **UNKNOWN** (not zero)\n"
        "<details><summary>All nine mandatory gates\n",encoding="utf-8")
    assert all((root/n).exists() for n in EXPECTED_FILES)


class NightlyResearchArtifactIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        sample_runner_folder(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return make_manifest(self.root,"schedule","2026-10-26","40399999999","a"*40)

    def rewrite(self,name,transform):
        p=self.root/name
        contents=json.loads(p.read_text())
        transform(contents)
        p.write_text(json.dumps(contents),encoding="utf-8")

    def test_complete_16_file_research_manifest_has_source_hashes_and_counts(self):
        x=self.manifest()
        self.assertEqual(x["verified_file_count"],16)
        self.assertEqual(x["reconciled_scope"]["registry_status_review_rows"],741)
        self.assertEqual(x["github_event"],"schedule")
        self.assertEqual(x["github_run_id"],40399999999)
        self.assertEqual(x["pacific_research_date"],"2026-10-26")
        self.assertEqual(x["reconciled_scope"]["historical_trial_count"],741)
        self.assertEqual(x["reconciled_scope"]["mandatory_gate_checks"],6669)
        self.assertEqual(x["reconciled_scope"]["commercial_rights_review_slots"],4446)
        self.assertIsNone(x["reconciled_scope"]["qualified_pipeline_total"])
        self.assertTrue(all(re.fullmatch(r"[a-f0-9]{64}",f["sha256"]) for f in x["files"]))
        self.assertTrue(verify_manifest(self.root,x))

    def test_registry_status_report_nct_scope_is_exact(self):
        self.rewrite("main_phase3_registry_status_recency.json",lambda x:
                     x["items"].__setitem__(0,{"nct_id":"NCT12345678"}))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_status_report_source_hash_conflict_fails(self):
        self.rewrite("main_phase3_registry_status_recency.json",lambda x:
                     x["items"][0].__setitem__("registry_source_sha256","e"*64))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_status_csv_forged_pipeline_claim_fails(self):
        p=self.root/"main_phase3_registry_status_review.csv"
        p.write_text(p.read_text().replace("False,", "True,",1),encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_status_breakdown_bad_denominator_fails(self):
        self.rewrite("main_phase3_registry_status_recency.json",lambda x:
                     x["source_posted_update_age_counts"].__setitem__("POSTED_LAST_90_DAYS",740))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_missing_required_primary_source_fails_before_upload(self):
        (self.root/"main_phase3_registry.json").unlink()
        with self.assertRaises(ValueError):
            self.manifest()

    def test_blank_optional_research_file_fails_before_upload(self):
        (self.root/"main_phase3_rights_gaps.json").write_bytes(b"")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_tampering_original_source_after_manifest_detected(self):
        original=self.manifest()
        with (self.root/"main_phase3_sec_rights_leads.json").open("a") as handle:
            handle.write(" ")
        with self.assertRaises(ValueError):
            verify_manifest(self.root,original)

    def test_duplicate_original_registry_nct_fails(self):
        self.rewrite("main_phase3_registry.json",lambda x:
                     x["original_source_records"].__setitem__(0,{"nct_id":"NCT00000002"}))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_missing_original_registry_nct_fails(self):
        self.rewrite("main_phase3_registry.json",lambda x:
                     x["original_source_records"].pop())
        with self.assertRaises(ValueError):
            self.manifest()

    def test_different_nct_scope_across_join_fails(self):
        self.rewrite("main_phase3_sec_trial_rights_join.json",lambda x:
                     x["items"].__setitem__(0,{"nct_id":"NCT90000001"}))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_incomplete_130_issuer_coverage_fails(self):
        self.rewrite("main_phase3_sec_rights_leads.json",lambda x:
                     x["issuers"].pop())
        with self.assertRaises(ValueError):
            self.manifest()

    def test_promoted_pipeline_claim_fails(self):
        self.rewrite("main_phase3_qualification_scorecard.json",lambda x:
                     x.__setitem__("qualified_trial_count",50))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_falsified_commercial_rights_rejected(self):
        self.rewrite("main_phase3_rights_casebook.json",lambda x:
                     x.__setitem__("rights_verified_trials",1))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_gate_denominator_drift_fails(self):
        self.rewrite("main_phase3_qualification_scorecard.json",lambda x:
                     x.__setitem__("gate_checks_review",5927))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_review_evidence_denominators_must_reconcile(self):
        self.rewrite("main_phase3_rights_review_submissions_coverage.json",lambda x:
                     x.__setitem__("distinct_review_slots_with_submissions",2))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_csv_missing_trial_fails(self):
        p=self.root/"main_phase3_rights_review_worklist.csv"
        p.write_text("\n".join(p.read_text().splitlines()[:-1])+"\n",encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_csv_forged_qualification_fails(self):
        p=self.root/"main_phase3_rights_review_worklist.csv"
        p.write_text(p.read_text().replace("False,", "True,",1),encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_markdown_falsified_qualified_count_fails(self):
        p=self.root/"main_phase3_qualification_summary.md"
        p.write_text("# Qualified Pipeline: 741\n",encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_duplicated_json_keys_fails_closed(self):
        p=self.root/"main_phase3_rights_gaps.json"
        p.write_text('{"total":741,"total":742}',encoding="utf-8")
        with self.assertRaises(ValueError):
            self.manifest()

    def test_invalid_or_non_source_run_metadata_rejected(self):
        for event,date_value,sha in (
            ("push","2026-10-26","a"*40),
            ("schedule","2026-22-26","a"*40),
            ("workflow_dispatch","2026-10-26","fake"),
        ):
            with self.subTest(event=event,date=date_value),self.assertRaises(ValueError):
                make_manifest(self.root,event,date_value,"40399999999",sha)

    def test_missing_source_run_id_rejected(self):
        with self.assertRaises(ValueError):
            make_manifest(self.root,"schedule","2026-10-26","", "a"*40)

    def test_symlink_to_external_file_is_rejected(self):
        path=self.root/"main_phase3_rights_gaps.json"
        target=self.root/"elsewhere.json"
        target.write_text(path.read_text(),encoding="utf-8")
        path.unlink()
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.manifest()

    def test_manifest_forged_file_count_fails_verification(self):
        x=self.manifest()
        x["verified_file_count"]=15
        with self.assertRaises(ValueError):
            verify_manifest(self.root,x)


if __name__=="__main__":
    unittest.main()
