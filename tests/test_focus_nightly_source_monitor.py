"""Regression checks for FOCUS nightly source change detection, no false FDA predictions."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/focus_nightly_source_monitor.py"
spec = importlib.util.spec_from_file_location("focus_nightly_source_monitor", MODULE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def examples():
    roster = {"asOf": "2026-11-09", "records": [
        {"nct": "NCT00000001", "ticker": "ONE", "company": "One"},
        {"nct": "NCT00000002", "ticker": "TWO", "company": "Two"},
    ]}
    applications = {"asOf": "2026-11-09", "records": [
        {"nct": "NCT00000001", "candidateApplications": [
            {"cycleId": "one-first", "ticker": "ONE"},
            {"cycleId": "one-followup", "ticker": "ONE"}]},
        {"nct": "NCT00000002", "candidateApplications": [
            {"cycleId": "two-first", "ticker": "TWO"}]},
    ]}
    return roster, applications


def registry(nct):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct},
        "statusModule": {"overallStatus": "COMPLETED",
                         "studyLastUpdatePostDateStruct": {"date": "2026-11-10"}},
        "designModule": {"phases": ["PHASE3"]},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Response"}]},
    }}


class FocusNightlySourceMonitorTest(unittest.TestCase):
    def setUp(self):
        self.roster, self.applications = examples()
        self.now = datetime(2026, 11, 11, 6, 31, tzinfo=timezone.utc)

    def run_check(self, prior=None, fetcher=registry):
        return monitor.build_report(self.roster, self.applications, prior or {}, fetcher, self.now)

    def test_first_source_observation_preserves_multiple_cycles(self):
        r = self.run_check()
        self.assertEqual(r["summary"]["focusTrials"], 2)
        self.assertEqual(r["summary"]["applicationCycles"], 3)
        self.assertEqual(r["summary"]["reassessmentQueueCycles"], 3)
        self.assertEqual(r["trials"][0]["applicationCycles"], ["one-first", "one-followup"])
        self.assertFalse(r["trials"][0]["scientificSignoff"])
        self.assertIsNone(r["trials"][0]["calibratedProbability"])
        self.assertEqual(r["summary"]["scientificAssessmentsRevalidated"], 0)

    def test_unchanged_registry_does_not_trigger_reassessment(self):
        first = self.run_check()
        second = self.run_check(first)
        self.assertEqual(second["summary"]["newOrChangedEvidenceTrials"], 0)
        self.assertEqual(second["reassessmentQueue"], [])
        self.assertEqual(second["summary"]["sourceRetrieved"], 2)

    def test_only_changed_application_cycles_queued(self):
        first = self.run_check()
        def changed(nct):
            packet = registry(nct)
            if nct == "NCT00000002":
                packet["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [{"title": "Result"}]}}
            return packet
        r = self.run_check(first, changed)
        self.assertEqual(r["summary"]["newOrChangedEvidenceTrials"], 1)
        self.assertEqual([x["cycleId"] for x in r["reassessmentQueue"]], ["two-first"])

    def test_outage_keeps_previous_fingerprint_and_marks_incomplete(self):
        first = self.run_check()
        def broken(nct):
            if nct == "NCT00000002":
                raise TimeoutError("unavailable")
            return registry(nct)
        r = self.run_check(first, broken)
        self.assertEqual(r["summary"]["sourceUnavailable"], 1)
        self.assertEqual(r["summary"]["newOrChangedEvidenceTrials"], 0)
        self.assertEqual(r["sourceRecoveryQueue"], ["NCT00000002"])
        self.assertEqual(r["trials"][1]["sourceHash"], first["trials"][1]["sourceHash"])
        self.assertEqual(r["summary"]["status"], "PARTIAL_SOURCE_MONITOR")

    def test_unmapped_application_ncts_remain_under_registry_monitoring(self):
        self.roster["records"].append(
            {"nct": "NCT00000003", "ticker": "THREE", "company": "Three"})
        report = self.run_check()
        self.assertEqual(report["summary"]["focusTrials"], 3)
        self.assertEqual(report["summary"]["unmappedApplicationNcts"], 1)
        self.assertEqual(report["applicationCrosswalkState"], "PARTIAL")
        self.assertEqual(report["trials"][2]["applicationCycles"], [])
        self.assertEqual(report["unmappedApplicationReviewQueue"][0]["nct"], "NCT00000003")
        self.assertEqual(report["summary"]["reassessmentQueueCycles"], 3)
        self.assertEqual(report["summary"]["scientificAssessmentsRevalidated"], 0)

    def test_wrong_nct_and_roster_conflicts_rejected(self):
        with self.assertRaises(ValueError):
            monitor.summarize_registry("NCT00000001", registry("NCT00000002"))
        self.roster["records"].append(dict(self.roster["records"][0]))
        with self.assertRaises(ValueError):
            self.run_check()
        self.roster, self.applications = examples()
        self.applications["records"][1]["candidateApplications"][0]["ticker"] = "ONE"
        with self.assertRaises(ValueError):
            self.run_check()

    def test_live_repository_crosswalk_matches_canonical_focus(self):
        roster = monitor.load_json(monitor.ROSTER_PATH)
        applications = monitor.load_json(monitor.APPLICATIONS_PATH)
        rows, links = monitor.roster_and_cycles(roster, applications)
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({c for ids in links.values() for c in ids}), 23)
        self.assertEqual(sum(map(len, links.values())), 30)
        self.assertEqual(sum(1 for nct in links if not links[nct]), 3)
        self.assertEqual({nct for nct in links if not links[nct]},
                         {"NCT05031780", "NCT06747468", "NCT06553768"})


if __name__ == "__main__":
    unittest.main()
