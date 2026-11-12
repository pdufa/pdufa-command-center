"""Offline fail-closed serial engineering planner tests; no worker mutation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("planner",ROOT/"scripts/pdufa_level_remediation_planner.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
BASE=json.loads((ROOT/"automation/scientific-level-completion-queue.json").read_text())

def ledger(n=2):
    return {"mode":"ENGINEERING_ADVANCE_REVIEW_SEPARATE",
            "engineering_completed_levels":[
                {"level":x["level"],"scope":x["implementation_scope"],
                 "evidence_sha256":"a"*64} for x in BASE["levels"][:n]]}

def progress():
    return {"levels":{
        "6":{"steps":{
            "AUDIT_EXISTING_DRAFTS":{"status":"DONE",
                                     "evidence":{"scientific_signoff":False}},
            "COLLECT_ORIGINAL_SOURCE":{"status":"BLOCKED",
                                       "blocker":"DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED"},
            "IMPLEMENT_FUNCTIONAL_GATES":{"status":"BLOCKED",
                                          "blocker":"DOMAIN_IMPLEMENTATION_NOT_APPROVED"},
            "RUN_REGRESSION_TESTS":{"status":"BLOCKED",
                                    "blocker":"DOMAIN_REGRESSION_SUITE_NOT_APPROVED"},
            "PREPARE_REVIEW_PR":{"status":"BLOCKED",
                                 "blocker":"DOMAIN_IMPLEMENTATION_PR_NOT_AVAILABLE"},
        }}}
    }

class SerialRemediationTests(unittest.TestCase):
    def test_missing_ledger_never_invents_current_level(self):
        p=M.plan_work(BASE)
        self.assertIsNone(p["active_level"])
        self.assertIsNone(p["engineering_levels_recorded_complete"])
        self.assertIsNone(p["next_repair"])
        self.assertEqual(p["levels"][0]["state"],"ENGINEERING_LEDGER_NOT_PROVIDED")
        self.assertFalse(p["automatic_installation_proven"])

    def test_two_completed_slices_means_level6_and_first_real_blocker(self):
        p=M.plan_work(BASE,engineering_state=ledger(),completion_state=progress())
        self.assertEqual(p["active_level"],6)
        self.assertEqual(p["engineering_levels_recorded_complete"],2)
        self.assertEqual(p["next_repair"]["checkpoint"],"COLLECT_ORIGINAL_SOURCE")
        self.assertEqual(p["next_repair"]["category"],"SOURCE_EVIDENCE")
        lvl6=p["levels"][2]
        self.assertEqual([x["checkpoint"] for x in lvl6["checkpoints_to_repair"]],
                         ["COLLECT_ORIGINAL_SOURCE","IMPLEMENT_FUNCTIONAL_GATES",
                          "RUN_REGRESSION_TESTS","PREPARE_REVIEW_PR"])
        self.assertEqual(lvl6["implementation_draft_pr"],1163)
        self.assertTrue(lvl6["can_start_engineering_now"])
        self.assertFalse(lvl6["scientific_completion_verified"])

    def test_future_level7_can_have_reviewed_draft_without_skipping_level6(self):
        p=M.plan_work(BASE,engineering_state=ledger(),completion_state=progress(),
                      focus_level=7)
        self.assertEqual(p["selected_level"]["level"],7)
        self.assertEqual(p["selected_level"]["name"],"Predictive Modeling and Uncertainty")
        self.assertFalse(p["selected_level"]["can_start_engineering_now"])
        self.assertEqual(p["selected_level"]["implementation_draft_pr"],1169)
        self.assertFalse(p["selected_level"]["scientific_completion_verified"])
        self.assertEqual(p["active_level"],6)

    def test_proper_contiguous_sequence_cannot_skip_level6(self):
        wrong=ledger()
        wrong["engineering_completed_levels"].append(
            {"level":8,"scope":BASE["levels"][4]["implementation_scope"],
             "evidence_sha256":"a"*64})
        with self.assertRaisesRegex(ValueError,"noncontiguous"):
            M.plan_work(BASE,engineering_state=wrong)

    def test_ledger_invalid_sha_and_scope_not_trusted(self):
        for field,bad in [("evidence_sha256","x"*64),("scope","all science done")]:
            with self.subTest(field=field):
                wrong=ledger()
                wrong["engineering_completed_levels"][0][field]=bad
                with self.assertRaises(ValueError):
                    M.plan_work(BASE,engineering_state=wrong)

    def test_manifest_does_not_allow_fabricated_scientific_complete(self):
        for mutate in [
            lambda x:x["levels"][2].update(completed_scientific_level=True),
            lambda x:x["levels"].pop(4),
            lambda x:x["levels"][2].update(level=8),
            lambda x:x["safety"].update(automatic_merges=True),
            lambda x:x["levels"][3].update(required_evidence_fields=[]),
        ]:
            bad=copy.deepcopy(BASE)
            mutate(bad)
            with self.assertRaises(ValueError):
                M.plan_work(bad,engineering_state=ledger())

    def test_all_completed_engineering_still_not_scientific_review(self):
        # Synthetic structurally valid evidence hashes are NOT actual verification.
        p=M.plan_work(BASE,engineering_state=ledger(17))
        self.assertIsNone(p["active_level"])
        self.assertFalse(p["engineering_ledger_verified_by_authoritative_controller"])
        self.assertTrue(all(x["scientific_completion_verified"] is False
                            for x in p["levels"]))
        self.assertEqual(p["engineering_levels_recorded_complete"],17)

    def test_invalid_level_and_wrong_mode_fail_closed(self):
        for n in (0,3,21,True,"7"):
            with self.subTest(n=n),self.assertRaises(ValueError):
                M.plan_work(BASE,engineering_state=ledger(),focus_level=n)
        with self.assertRaises(ValueError):
            M.plan_work(BASE,engineering_state={"mode":"UNKNOWN"})

    def test_no_engineering_receipts_means_level4_not_all_done(self):
        p=M.plan_work(BASE,engineering_state=ledger(0))
        self.assertEqual(p["active_level"],4)
        self.assertEqual(sum(x["can_start_engineering_now"] for x in p["levels"]),1)
        self.assertEqual(len(p["levels"]),17)
        self.assertTrue(all(x["scientific_completion_verified"] is False
                            for x in p["levels"]))

if __name__=="__main__":
    unittest.main()
