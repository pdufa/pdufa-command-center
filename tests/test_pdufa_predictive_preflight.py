"""Offline audit of predictable PDUFA 4-20 install/development issues."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("predictive",
                                             ROOT/"scripts/pdufa_predictive_preflight.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
manifest=json.loads((ROOT/"automation/scientific-level-completion-queue.json")
                    .read_text(encoding="utf-8"))

class PredictivePreflightTests(unittest.TestCase):
    def test_all_17_levels_audited_without_fabricated_scientific_completion(self):
        result=M.audit(manifest,ROOT)
        self.assertEqual([row["level"] for row in result["levels"]],list(range(4,21)))
        self.assertTrue(all(x["scientific_level_complete"] is False for x in result["levels"]))
        self.assertFalse(result["windows_restart_confirmed"])
        self.assertFalse(result["scientific_reviews_automatically_completed"])

    def test_all_known_future_level_implementations_recognized_as_missing(self):
        out=M.audit(manifest,ROOT)
        self.assertEqual(out["future_levels_with_missing_approved_domain_implementation"],
                         list(range(8,21)))
        self.assertFalse(out["all_future_levels_implementation_ready"])
        for row in out["levels"][4:]:
            self.assertIn("DOMAIN_IMPLEMENTATION_NOT_APPROVED",
                          [x["code"] for x in row["predictable_findings"]])

    def test_level7_preparatory_code_optional_but_never_an_approved_model(self):
        out=M.audit(manifest,ROOT)
        level7=out["levels"][3]
        self.assertFalse(level7["engineering_release_ready"])
        codes=[x["code"] for x in level7["predictable_findings"]]
        self.assertNotIn("DOMAIN_IMPLEMENTATION_NOT_APPROVED",codes)
        self.assertEqual(level7["implementation_pr_registered"],1169)
        if (ROOT/"scripts/level7_model_validation_readiness.py").is_file():
            self.assertIn("PREPARATORY_ONLY_NOT_APPROVED_FOR_ENGINEERING_ADVANCEMENT",
                          codes)
        else:
            self.assertIn("LEVEL7_PREPARATORY_MODULE_NOT_INSTALLED",codes)

    def test_partial_windows_install_without_level7_does_not_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=M.audit(manifest,Path(tmp))
            level7=out["levels"][3]
            self.assertFalse(level7["engineering_release_ready"])
            self.assertIn("LEVEL7_PREPARATORY_MODULE_NOT_INSTALLED",
                          [x["code"] for x in level7["predictable_findings"]])

    def test_missing_source_file_is_predicted_before_worker_reaches_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            out=M.audit(manifest,root)
            self.assertGreater(out["known_shared_installation_blockers"],0)
            self.assertIn("REQUIRED_DOMAIN_FILE_MISSING",
                          [x["code"] for x in out["levels"][2]["predictable_findings"]])

    def test_install_manifest_and_git_blob_pins_checked(self):
        problems=M.inspect_installer(ROOT)
        known=[x for x in problems if x["classification"]=="KNOWN_BLOCK"]
        self.assertEqual(known,[],known)

    def test_host_checks_are_explicitly_unknown_not_faked_passes(self):
        result=M.audit(manifest,ROOT)
        host=[x for x in result["shared_installation_findings"]
              if x["classification"]=="HOST_CHECK_REQUIRED"]
        self.assertGreaterEqual(len(host),5)
        self.assertTrue(all(x["code"]=="HOST_RUNTIME_PREFLIGHT_REQUIRED" for x in host))
        self.assertEqual(result["status"],
                         "STATIC_PREDICTIVE_PREFLIGHT_NOT_WINDOWS_HOST_CERTIFICATION")

    def test_network_failure_checked_before_installing_and_restarting(self):
        body=(ROOT/"scripts/windows_pdufa_level6_unblock.ps1").read_text()
        for name in ("CLINICAL_REGISTRY_HOST_CONNECTIVITY_FAILED",
                     "GITHUB_RAW_RELEASE_DOWNLOAD_BLOCKED"):
            self.assertIn(name,body)
            self.assertLess(body.index(name),body.index("$stage=Join-Path"))
        self.assertLess(body.index("if($Preflight)"),
                        body.index("$stage=Join-Path"))

    def test_no_auto_merges_or_prediction_signoffs_permitted(self):
        for unsafe in ("automatic_merges","production_deployments",
                       "scientific_level_completion_by_agent"):
            mutated=copy.deepcopy(manifest)
            mutated["safety"][unsafe]=True
            with self.subTest(unsafe=unsafe),self.assertRaises(ValueError):
                M.audit(mutated,ROOT)
        wrong=copy.deepcopy(manifest)
        wrong["levels"][9]["completed_scientific_level"]=True
        with self.assertRaises(ValueError):
            M.audit(wrong,ROOT)

    def test_phase_evidence_requirements_required_at_every_level(self):
        wrong=copy.deepcopy(manifest)
        wrong["levels"][8]["required_evidence_fields"]=[]
        with self.assertRaises(ValueError):
            M.audit(wrong,ROOT)
        wrong=copy.deepcopy(manifest)
        wrong["levels"][7]["scientific_acceptance_criteria"].remove(
            "no_unblinded_historical_data_leakage")
        with self.assertRaises(ValueError):
            M.audit(wrong,ROOT)

if __name__=="__main__":
    unittest.main()
