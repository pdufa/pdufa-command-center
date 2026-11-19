#!/usr/bin/env python3
"""Regression tests for six-level blind historical scoring.
Run: python -m unittest discover -s tests -p 'test_blind_six_levels_2026.py'
"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "blind_six_levels_2026.py"
sys.path.insert(0, str(ROOT / "scripts"))
import blind_six_levels_2026 as engine

class BlindSixLevelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.events = self.dir / "events.csv"
        self.locked = self.dir / "locked.json"
        self.outcomes = self.dir / "outcomes.csv"
        self.scored = self.dir / "scored.json"
        self.row = {"event_id":"EXAMPLE-001","ticker":"TEST","drug":"example",
                    "indication":"test indication","decision_date":"2026-10-01",
                    "evidence_asof":"2026-08-20","source_publication_date":"2026-08-20",
                    "source_url":"https://example.org/predecision"}
        for level, gates in engine.GATES.items():
            for gate in gates:
                self.row[gate] = "NO" if gate in engine.BAD[level] else "YES"

    def write_events(self, rows, extra_cols=()):
        columns = list(self.row) + list(extra_cols)
        with self.events.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=columns)
            w.writeheader()
            w.writerows(rows)

    def run_script(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],
                              text=True,capture_output=True)

    def prepare(self):
        return self.run_script("prepare","--events",self.events,
                               "--output",self.locked,"--expected-events","1")

    def test_six_predictions_lock_and_accuracy(self):
        self.write_events([self.row])
        result=self.prepare()
        self.assertEqual(result.returncode,0,result.stderr)
        locked=json.loads(self.locked.read_text())
        self.assertEqual(len(locked["predictions"]),6)
        self.assertEqual({x["prediction"] for x in locked["predictions"]},{"APPROVE"})
        with self.outcomes.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["event_id","actual_outcome"])
            w.writeheader();w.writerow({"event_id":"EXAMPLE-001","actual_outcome":"APPROVE"})
        result=self.run_script("score","--locked",self.locked,
                               "--outcomes",self.outcomes,"--output",self.scored,
                               "--expected-lock-sha256", locked["lock_sha256"])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(all(x["accuracy"]==1 for x in json.loads(self.scored.read_text())))

    def test_missing_evidence_abstains_not_crl(self):
        self.row["trial_design_valid"]=""
        self.write_events([self.row])
        self.assertEqual(self.prepare().returncode,0)
        preds=json.loads(self.locked.read_text())["predictions"]
        self.assertEqual(next(x for x in preds if x["level"]=="L02")["prediction"],"ABSTAIN")

    def test_outcome_leakage_rejected(self):
        self.row["actual_outcome"]="APPROVE"
        self.write_events([self.row])
        self.assertNotEqual(self.prepare().returncode,0)

    def test_post_cutoff_source_rejected(self):
        self.row["source_publication_date"]="2026-09-15"
        self.write_events([self.row])
        self.assertNotEqual(self.prepare().returncode,0)

    def test_no_padding_to_196(self):
        self.write_events([self.row])
        result=self.run_script("prepare","--events",self.events,"--output",self.locked)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Expected 196 events",result.stderr)

    def test_prediction_lock_tampering_rejected(self):
        self.write_events([self.row])
        self.assertEqual(self.prepare().returncode,0)
        data=json.loads(self.locked.read_text())
        data["predictions"][0]["prediction"]="CRL"
        self.locked.write_text(json.dumps(data))
        with self.outcomes.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["event_id","actual_outcome"])
            w.writeheader();w.writerow({"event_id":"EXAMPLE-001","actual_outcome":"APPROVE"})
        result=self.run_script("score","--locked",self.locked,
                               "--outcomes",self.outcomes,"--output",self.scored,
                               "--expected-lock-sha256", data["lock_sha256"])
        self.assertNotEqual(result.returncode,0)
        self.assertIn("integrity failure",result.stderr)

    def test_score_requires_external_digest(self):
        self.write_events([self.row])
        self.assertEqual(self.prepare().returncode, 0)
        result = self.run_script(
            "score", "--locked", self.locked, "--outcomes", self.outcomes,
            "--output", self.scored,
        )
        self.assertIn("independently recorded lock digest", result.stderr)

    def test_no_overwrite_of_frozen_lock(self):
        self.write_events([self.row])
        self.assertEqual(self.prepare().returncode, 0)
        original = self.locked.read_bytes()
        self.row["trial_design_valid"] = "NO"
        self.write_events([self.row])
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertEqual(self.locked.read_bytes(), original)

    def test_rejects_undeclared_and_ragged_manifest_columns(self):
        self.row["decision_label"] = "APPROVE"
        self.write_events([self.row])
        self.assertIn("Unexpected blind manifest columns", self.prepare().stderr)
        self.row.pop("decision_label")
        self.write_events([self.row])
        original = self.events.read_text()
        self.events.write_text(original.rstrip("\n") + ",APPROVE\n")
        self.assertIn("CSV row does not match the header width", self.prepare().stderr)

    def test_lock_binds_features_rules_and_predictions(self):
        self.row["trial_design_valid"] = "UNKNOWN"
        self.row["inspection_risk_material"] = "YES"
        self.write_events([self.row])
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        lock = json.loads(self.locked.read_text())
        digest = lock["lock_sha256"]
        self.assertEqual(lock["rule_set"], engine.EXPERIMENTAL_RULES)
        predictions = {row["level"]: row for row in engine.verify_lock(lock, digest)}
        self.assertEqual(predictions["L02"]["prediction"], "ABSTAIN")
        self.assertEqual(predictions["L02"]["unknown_gates"], ["trial_design_valid"])
        self.assertEqual(predictions["L05"]["prediction"], "CRL")
        self.assertEqual(predictions["L05"]["failed_gates"], ["inspection_risk_material"])
        self.assertEqual(predictions["L06"]["prediction"], "APPROVE")
        lock["feature_snapshots"][0]["event"]["source_publication_date"] = "2026-08-21"
        with self.assertRaisesRegex(ValueError, "integrity failure"):
            engine.verify_lock(lock, digest)
        lock.pop("lock_sha256")
        lock["feature_snapshots_sha256"] = engine.canonical_digest(lock["feature_snapshots"])
        lock["lock_sha256"] = engine.canonical_digest(lock)
        with self.assertRaisesRegex(ValueError, "Frozen lock digest mismatch"):
            engine.verify_lock(lock, digest)


if __name__=="__main__":
    unittest.main()
