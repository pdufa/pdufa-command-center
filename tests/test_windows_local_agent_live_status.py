"""Offline tests for the four-hour FOCUS live-registry receipt verifier."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from windows_local_agent_live_focus_registry import capture_batch
from windows_local_agent_live_status import verify_live_summary

NOW = datetime(2026, 11, 11, 22, 0, tzinfo=timezone.utc)


class ScheduledLiveStatusTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.roster = {
            "schemaVersion": 1,
            "asOf": "2026-11-11",
            "records": [
                {"nct": f"NCT{i:08d}", "ticker": "TEST", "company": "Synthetic"}
                for i in range(1, 30)
            ],
        }
        self.raw = json.dumps(self.roster).encode("utf-8")
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def fake_fetch(self, nct, timeout=20):
        data = {"protocolSection": {"identificationModule": {"nctId": nct}}}
        meta = {
            "nct": nct,
            "source_url": "https://clinicaltrials.gov/api/v2/studies/" + nct,
            "source_type": "PRIMARY_REGISTRY",
            "retrieved_at_utc": NOW.isoformat(),
            "sha256": hashlib.sha256(nct.encode()).hexdigest(),
            "scientific_adjudication": "NOT_ADJUDICATED",
            "fda_probability": None,
        }
        return data, meta

    def run_batch(self, limit=10, fetcher=None):
        return capture_batch(
            [r["nct"] for r in self.roster["records"]],
            self.digest, self.directory, limit,
            fetcher=fetcher or self.fake_fetch, now=NOW,
        )

    def test_partial_10_of_29_is_valid_but_not_full(self):
        report = self.run_batch(10)
        self.assertEqual(report["source_state"], "PARTIAL_SOURCE_CAPTURE")
        self.assertEqual(report["fresh_exact_registry_captures"], 10)
        self.assertTrue(verify_live_summary(report, self.raw, self.directory, NOW))

    def test_all_fresh_29_reports_valid_zero_network_refresh(self):
        self.run_batch(29)
        report = self.run_batch(10)
        self.assertEqual(report["network_attempts_this_run"], 0)
        self.assertEqual(report["source_state"], "ALL_FRESH_SOURCE_ONLY")
        self.assertTrue(verify_live_summary(report, self.raw, self.directory, NOW))

    def test_falsified_complete_count_rejected(self):
        report = self.run_batch(10)
        report["fresh_exact_registry_captures"] = 29
        report["remaining_without_fresh_capture"] = 0
        report["source_state"] = "ALL_FRESH_SOURCE_ONLY"
        self.assertFalse(verify_live_summary(report, self.raw, self.directory, NOW))

    def test_tampered_saved_receipt_fails_verification(self):
        report = self.run_batch(10)
        path = self.directory / "NCT00000001.json"
        stored = json.loads(path.read_text())
        stored["record"]["protocolSection"]["identificationModule"]["nctId"] = "NCT00000002"
        path.write_text(json.dumps(stored), encoding="utf-8")
        self.assertFalse(verify_live_summary(report, self.raw, self.directory, NOW))

    def test_scientific_prediction_and_modified_production_rejected(self):
        report = self.run_batch(10)
        for key, value in (
            ("scientific_levels_completed", 2),
            ("fda_approval_probability", 0.9),
            ("clinical_prediction", "APPROVE"),
            ("production_modified", True),
            ("roster_live_membership_verified", True),
        ):
            with self.subTest(field=key):
                candidate = dict(report)
                candidate[key] = value
                self.assertFalse(
                    verify_live_summary(candidate, self.raw, self.directory, NOW)
                )

    def test_wrong_cohort_and_oversized_scheduled_batch_rejected(self):
        report = self.run_batch(10)
        other = json.dumps({**self.roster, "asOf": "2026-11-10"}).encode()
        self.assertFalse(verify_live_summary(report, other, self.directory, NOW))
        candidate = dict(report)
        candidate["network_attempts_this_run"] = 11
        candidate["newly_captured_this_run"] = 11
        self.assertFalse(
            verify_live_summary(candidate, self.raw, self.directory, NOW)
        )

    def test_partial_network_failures_not_reported_full(self):
        def fail_one(nct, timeout=20):
            if nct == "NCT00000001":
                raise TimeoutError("synthetic temporary outage")
            return self.fake_fetch(nct, timeout)
        report = self.run_batch(10, fetcher=fail_one)
        self.assertEqual(report["failed_attempts_this_run"], 1)
        self.assertEqual(report["fresh_exact_registry_captures"], 9)
        self.assertTrue(verify_live_summary(report, self.raw, self.directory, NOW))
        self.assertEqual(report["source_state"], "PARTIAL_SOURCE_CAPTURE")


if __name__ == "__main__":
    unittest.main()
