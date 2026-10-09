import csv
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts import all_phase_scan as scan

def study(nct, status, sponsor="Renamed Subsidiary"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}},
        "designModule": {"phases": ["PHASE3"]},
        "statusModule": {"overallStatus": status}}}

class Response:
    def __init__(self, studies): self.studies = studies
    def raise_for_status(self): pass
    def json(self): return {"studies": self.studies}

class Session:
    def __init__(self):
        self.calls = []
        self.missing = False
        self.fail = False
        self.status = "TERMINATED"
    def get(self, url, params, timeout):
        self.calls.append(dict(params))
        if "query.spons" in params:
            return Response([study("NCT00000001", "COMPLETED", "Parent")])
        if self.fail:
            raise scan.requests.RequestException("Registry unavailable")
        studies = {"NCT00000001": study("NCT00000001", "COMPLETED"),
                   "NCT00000002": study("NCT00000002", self.status)}
        return Response([studies[nct] for nct in params["filter.ids"].split(",")
                         if not (self.missing and nct == "NCT00000002")])
    def close(self): pass

class DailyTrialRecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "company_registry.csv").write_text("ticker,company\nA,Parent\n")
        (self.root / "phase_pipeline.csv").write_text("nct_id,ticker,company\nNCT00000002,A,Parent\n")
        scan.save_csv(self.root / "all_phase_trials.csv", [
            {"nct_id": "NCT00000001", "ticker": "A", "company": "Parent",
             "phase": "PHASE3", "status": "RECRUITING"}])
        self.session = Session()

    def run_scan(self):
        with patch.object(scan.requests, "Session", return_value=self.session), \
             patch.object(scan.time, "sleep"), redirect_stdout(io.StringIO()):
            scan.scan(self.root)
        return json.loads((self.root / "all_phase_scan_state.json").read_text())

    def test_direct_ids_cover_old_trials_independently_of_sponsor_names(self):
        state = self.run_scan()
        self.assertEqual(state["status"], "COMPLETE")
        self.assertEqual(state["tracked_trials_total"], 2)
        self.assertEqual(state["tracked_trials_checked"], 2)
        records = {row["nct_id"]: row for row in scan.rows(self.root / "all_phase_trials.csv")}
        self.assertEqual(records["NCT00000002"]["status"], "TERMINATED")
        self.assertEqual(records["NCT00000002"]["ticker"], "A")
        self.assertEqual(state["changed_trials_today"], 1)

    def test_checkpoints_resume_same_day_and_all_trials_recheck_next_day(self):
        state = self.run_scan()
        calls = len(self.session.calls)
        self.run_scan()
        self.assertEqual(len(self.session.calls), calls)
        state["run_date"] = "2000-01-01"
        scan.save(self.root / "all_phase_scan_state.json", state)
        self.session.status = "ACTIVE_NOT_RECRUITING"
        state = self.run_scan()
        self.assertGreater(len(self.session.calls), calls)
        rows = {row["nct_id"]: row for row in scan.rows(self.root / "all_phase_trials.csv")}
        self.assertEqual(rows["NCT00000002"]["status"], "ACTIVE_NOT_RECRUITING")

    def test_missing_trial_is_flagged_and_its_saved_record_is_preserved(self):
        state = self.run_scan()
        state["tracked_trial_checks"] = {}
        scan.save(self.root / "all_phase_scan_state.json", state)
        self.session.missing = True
        state = self.run_scan()
        self.assertEqual(state["status"], "COMPLETE WITH WARNINGS")
        self.assertFalse(state["complete"])
        self.assertEqual(state["tracked_trials_with_warnings"], 1)
        self.assertEqual(len(scan.rows(self.root / "all_phase_trials.csv")), 2)

    def test_failed_batch_is_flagged_and_saved_records_are_preserved(self):
        state = self.run_scan()
        state["tracked_trial_checks"] = {}
        scan.save(self.root / "all_phase_scan_state.json", state)
        self.session.fail = True
        state = self.run_scan()
        self.assertEqual(state["tracked_trials_with_warnings"], 2)
        self.assertEqual(state["status"], "COMPLETE WITH WARNINGS")
        self.assertEqual(len(scan.rows(self.root / "all_phase_trials.csv")), 2)

if __name__ == "__main__":
    unittest.main()
