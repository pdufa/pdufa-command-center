import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path(__file__).with_name("blind_l1_2026_backtest.py")
spec = importlib.util.spec_from_file_location("blind_l1", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

HEADER = ("event_id,ticker,drug,indication,decision_date,evidence_asof,"
          "submission_accepted,pivotal_primary_endpoint_met,"
          "major_safety_signal,documented_regulatory_deficiency\n")

class BlindL1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.events = self.base / "blind.csv"
        self.locked = self.base / "locked.json"
        self.outcomes = self.base / "outcomes.csv"
        self.scored = self.base / "scored.csv"

    def prepare(self):
        runner.prepare(SimpleNamespace(events=str(self.events),
             output=str(self.locked), cutoff_days=30))

    def test_locked_prediction_and_scoring(self):
        self.events.write_text(HEADER +
            "x1,AAA,Drug A,Ind A,2026-06-01,2026-04-01,yes,yes,no,no\n" +
            "x2,BBB,Drug B,Ind B,2026-06-01,2026-04-01,yes,no,no,no\n" +
            "x3,CCC,Drug C,Ind C,2026-06-01,2026-04-01,,yes,no,no\n")
        self.prepare()
        preds = json.loads(self.locked.read_text())["predictions"]
        self.assertEqual([p["prediction"] for p in preds],
                         ["APPROVE", "CRL", "ABSTAIN"])
        self.outcomes.write_text("event_id,actual_outcome\n"
                                 "x1,APPROVE\nx2,APPROVE\nx3,CRL\n")
        runner.score(SimpleNamespace(locked=str(self.locked),
                      outcomes=str(self.outcomes), output=str(self.scored)))
        self.assertTrue(self.scored.exists())

    def test_rejects_outcome_leakage_column(self):
        self.events.write_text(HEADER.rstrip("\n") +
            ",actual_outcome\nx1,AAA,Drug A,Ind A,2026-06-01,"
            "2026-04-01,yes,yes,no,no,APPROVE\n")
        with self.assertRaises(ValueError):
            self.prepare()

    def test_rejects_post_cutoff_evidence(self):
        self.events.write_text(HEADER +
            "x1,AAA,Drug A,Ind A,2026-06-01,2026-05-20,yes,yes,no,no\n")
        with self.assertRaises(ValueError):
            self.prepare()

    def test_rejects_duplicate_ids(self):
        self.events.write_text(HEADER +
            "x1,AAA,Drug A,Ind A,2026-06-01,2026-04-01,yes,yes,no,no\n" +
            "x1,BBB,Drug B,Ind B,2026-06-01,2026-04-01,yes,yes,no,no\n")
        with self.assertRaises(ValueError):
            self.prepare()

    def test_rejects_tampered_lock(self):
        self.events.write_text(HEADER +
            "x1,AAA,Drug A,Ind A,2026-06-01,2026-04-01,yes,yes,no,no\n")
        self.prepare()
        data = json.loads(self.locked.read_text())
        data["predictions"][0]["prediction"] = "CRL"
        self.locked.write_text(json.dumps(data))
        self.outcomes.write_text("event_id,actual_outcome\nx1,APPROVE\n")
        with self.assertRaises(ValueError):
            runner.score(SimpleNamespace(locked=str(self.locked),
                         outcomes=str(self.outcomes), output=str(self.scored)))

if __name__ == "__main__":
    unittest.main()
