"""Pure read-only scientific transfer planner safety tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.scientific_cohort_import_plan import MAX_BATCH, plan_from_inventory


def sample(nct, cohorts=("GEM_JR",), phases=("PHASE3",),
           results=True, pval="REPORTED", hash_char="a"):
    return {
        "nct_id": nct,
        "cohorts": list(cohorts),
        "phases": list(phases),
        "has_posted_results": results,
        "p_value_status": pval,
        "source_sha256": hash_char * 64,
    }


class ScientificArchiveCohortPlannerTest(unittest.TestCase):
    def test_conservative_scientific_scope_and_no_automatic_import(self):
        rows = [
            sample("NCT02142738", cohorts=("GEM_JR", "GEM")),
            sample("NCT04280705", cohorts=("WT",), phases=("PHASE2",),
                   results=False, pval="NO_POSTED_RESULTS"),
        ]
        plan = plan_from_inventory(rows)
        self.assertEqual(plan["schema_version"], "science-archive-transfer-plan-v1")
        self.assertEqual(plan["mode"], "read_only_proposal")
        self.assertEqual(plan["unique_trials"], 2)
        self.assertEqual(plan["with_phase_3_or_4"], 1)
        self.assertEqual(plan["with_posted_results"], 1)
        self.assertEqual(plan["with_reported_pvalue_status"], 1)
        self.assertEqual(plan["cohort_memberships"], {"WT": 1, "GEM": 1, "GEM_JR": 1})
        self.assertEqual(plan["planned_batches"][0]["nct_ids"],
                         ["NCT04280705", "NCT02142738"])
        self.assertTrue(plan["planned_batches"][0]["operator_approval_required"])
        self.assertFalse(plan["import_executed"])
        self.assertFalse(plan["source_byte_hashes_independently_verified"])
        self.assertEqual(plan["scientific_findings_independently_verified"], 0)
        for label in ("analysis_grade", "reluctance_grade", "fda_approval_probability"):
            self.assertIsNone(plan[label])

    def test_dedupe_only_same_exact_identity_and_snapshot(self):
        a = sample("NCT02142738", cohorts=("GEM_JR",))
        b = sample("NCT02142738", cohorts=("GEM", "WT"))
        plan = plan_from_inventory([a, b])
        self.assertEqual(plan["input_rows"], 2)
        self.assertEqual(plan["unique_trials"], 1)
        self.assertEqual(plan["trials"][0]["cohorts"], ["WT", "GEM", "GEM_JR"])
        self.assertEqual(len(plan["planned_batches"]), 1)

    def test_conflicting_content_hash_or_posted_state_rejected(self):
        a = sample("NCT02142738")
        for override in ({"source_sha256": "b"*64},
                         {"has_posted_results": False, "p_value_status": "NO_POSTED_RESULTS"},
                         {"phases": ["PHASE4"]}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                plan_from_inventory([a, {**a, **override}])

    def test_malformed_identity_membership_phase_and_no_results_rejected(self):
        trial = sample("NCT02142738")
        failures = (
            {"nct_id": "IRD"},
            {"nct_id": "NCT02142738?foo=bar"},
            {"cohorts": ["GEM_JR", "GEM_JR"]},
            {"cohorts": ["PIPELINE"]},
            {"cohorts": []},
            {"phases": ["PDUFA"]},
            {"phases": ["PHASE3", "PHASE3"]},
            {"has_posted_results": "true"},
            {"p_value_status": "P=0.05"},
            {"has_posted_results": False},
            {"source_sha256": "abc"},
        )
        for override in failures:
            with self.subTest(override=override), self.assertRaises(ValueError):
                plan_from_inventory([{**trial, **override}])

    def test_prioritization_and_stable_input_independence(self):
        entries = [
            sample("NCT00000001", cohorts=("GEM_JR",), phases=("PHASE3",)),
            sample("NCT00000002", cohorts=("WT",), phases=("PHASE2",), results=False,
                   pval="NO_POSTED_RESULTS"),
            sample("NCT00000003", cohorts=("GEM",), phases=("PHASE4",)),
            sample("NCT00000004", cohorts=("WT",), phases=("PHASE3",)),
        ]
        a = plan_from_inventory(entries)
        b = plan_from_inventory(list(reversed(entries)))
        self.assertEqual(a["snapshot_sha256"], b["snapshot_sha256"])
        self.assertEqual([x["nct_id"] for x in a["trials"]],
                         ["NCT00000004", "NCT00000002", "NCT00000003", "NCT00000001"])
        self.assertEqual(a["trials"], b["trials"])

    def test_bounded_batches_25_without_auto_execution(self):
        entries = [sample(f"NCT{i:08d}") for i in range(1, 58)]
        plan = plan_from_inventory(entries)
        self.assertEqual(len(plan["planned_batches"]), 3)
        self.assertEqual([len(b["nct_ids"]) for b in plan["planned_batches"]],
                         [MAX_BATCH, MAX_BATCH, 7])
        for batch in plan["planned_batches"]:
            self.assertTrue(batch["operator_approval_required"])
            self.assertFalse(batch["executed"])

    def test_reject_empty_oversized_or_malformed_input(self):
        for item in (None, {}, [], [1], [sample("NCT02142738")] * 50001):
            with self.subTest(type=str(type(item))), self.assertRaises(ValueError):
                plan_from_inventory(item)

    def test_cli_dry_run_creates_nonoverwriting_local_manifest_only(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as dirname:
            folder = Path(dirname)
            inventory = folder / "inputs.json"
            output = folder / "proposed_manifest.json"
            inventory.write_text(json.dumps([sample("NCT02142738")]), encoding="utf-8")
            command = [sys.executable, "-m", "app.scientific_cohort_import_plan",
                       "--inventory", str(inventory), "--output", str(output)]
            first = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                   check=False, timeout=15)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(result["import_executed"])
            self.assertEqual(json.loads(first.stdout)["status"], "DRY_RUN_ONLY")
            second = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                    check=False, timeout=15)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(json.loads(second.stdout)["status"], "PLAN_REJECTED")
            self.assertFalse(result["planned_batches"][0]["executed"])


if __name__ == "__main__":
    unittest.main()
