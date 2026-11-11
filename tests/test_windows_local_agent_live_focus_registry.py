"""Offline safety tests for bounded live ClinicalTrials.gov FOCUS capture."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts/windows_local_agent_live_focus_registry.py"
SPEC = importlib.util.spec_from_file_location("windows_local_agent_live_focus_registry", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
NOW = datetime(2026, 11, 11, 15, 0, tzinfo=timezone.utc)
COHORT = "1" * 64


class LiveFocusRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.ncts = [f"NCT{n:08d}" for n in range(1, 30)]
        self.calls = []

    def fake_fetch(self, nct, timeout=20):
        self.calls.append((nct, timeout))
        record = {"protocolSection": {
            "identificationModule": {"nctId": nct},
            "statusModule": {"overallStatus": "RECRUITING"},
        }}
        meta = {
            "nct": nct,
            "source_url": "https://clinicaltrials.gov/api/v2/studies/" + nct,
            "source_type": "PRIMARY_REGISTRY",
            "retrieved_at_utc": NOW.isoformat(),
            "sha256": hashlib.sha256(("source:" + nct).encode()).hexdigest(),
            "scientific_adjudication": "NOT_ADJUDICATED",
            "fda_probability": None,
        }
        return record, meta

    def batch(self, limit=5, fetcher=None, now=NOW):
        return MODULE.capture_batch(
            self.ncts, COHORT, self.dir, limit,
            fetcher=self.fake_fetch if fetcher is None else fetcher, now=now,
        )

    def test_real_saved_roster_29_distinct_ncts(self):
        source = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
        ncts = MODULE.verified_roster(json.loads(source.read_text(encoding="utf-8")))
        self.assertEqual(len(ncts), 29)
        self.assertEqual(len(set(ncts)), 29)

    def test_default_batch_captures_five_only_and_abstains(self):
        result = self.batch()
        self.assertEqual(result["network_attempts_this_run"], 5)
        self.assertEqual(result["newly_captured_this_run"], 5)
        self.assertEqual(result["fresh_exact_registry_captures"], 5)
        self.assertEqual(result["remaining_without_fresh_capture"], 24)
        self.assertEqual(result["source_state"], "PARTIAL_SOURCE_CAPTURE")
        self.assertEqual(result["source_adjudication"], "NOT_COMPLETED")
        self.assertIsNone(result["clinical_prediction"])
        self.assertIsNone(result["fda_approval_probability"])
        self.assertFalse(result["production_modified"])
        self.assertFalse(result["roster_live_membership_verified"])
        self.assertEqual([x[0] for x in self.calls], self.ncts[:5])
        data = json.loads((self.dir / f"{self.ncts[0]}.json").read_text())
        self.assertFalse(data["scientific_assessment_completed"])
        self.assertIsNone(data["fda_prediction"])
        self.assertEqual(data["record"]["protocolSection"]["identificationModule"]["nctId"], self.ncts[0])

    def test_second_batch_reuses_fresh_cache_and_captures_next_five(self):
        first = self.batch()
        second = self.batch()
        self.assertEqual(first["fresh_exact_registry_captures"], 5)
        self.assertEqual(second["fresh_exact_registry_captures"], 10)
        self.assertEqual(second["network_attempts_this_run"], 5)
        self.assertEqual([c[0] for c in self.calls], self.ncts[:10])

    def test_all_29_captured_with_explicit_extended_limit(self):
        result = self.batch(limit=29)
        self.assertEqual(result["fresh_exact_registry_captures"], 29)
        self.assertEqual(result["remaining_without_fresh_capture"], 0)
        self.assertEqual(result["source_state"], "ALL_FRESH_SOURCE_ONLY")
        self.assertEqual(result["scientific_levels_completed"], 0)

    def test_mismatched_registry_record_is_rejected_without_saving(self):
        def bad(nct, timeout=20):
            record, meta = self.fake_fetch(nct, timeout)
            record["protocolSection"]["identificationModule"]["nctId"] = "NCT99999999"
            return record, meta
        result = self.batch(limit=1, fetcher=bad)
        self.assertEqual(result["failed_attempts_this_run"], 1)
        self.assertEqual(result["fresh_exact_registry_captures"], 0)
        self.assertFalse((self.dir / f"{self.ncts[0]}.json").exists())

    def test_bad_fda_claim_in_source_metadata_is_rejected(self):
        def bad(nct, timeout=20):
            record, meta = self.fake_fetch(nct, timeout)
            meta["fda_probability"] = 0.99
            return record, meta
        result = self.batch(limit=1, fetcher=bad)
        self.assertEqual(result["failed_attempts_this_run"], 1)
        self.assertEqual(result["fresh_exact_registry_captures"], 0)

    def test_invalid_cache_checksum_forces_refetch(self):
        self.batch(limit=1)
        path = self.dir / f"{self.ncts[0]}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["record"]["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
        path.write_text(json.dumps(doc), encoding="utf-8")
        self.assertFalse(MODULE.valid_cache(path, self.ncts[0], COHORT, NOW))
        self.batch(limit=1)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(MODULE.valid_cache(path, self.ncts[0], COHORT, NOW))

    def test_expired_24_hour_cache_forces_refetch(self):
        self.batch(limit=1)
        tomorrow = NOW + timedelta(hours=24, minutes=1)
        self.assertFalse(MODULE.valid_cache(self.dir / f"{self.ncts[0]}.json", self.ncts[0], COHORT, tomorrow))
        # With a later time the mocked fetch must also use a later receipt.
        def later_fetch(nct, timeout=20):
            record, meta = self.fake_fetch(nct, timeout)
            meta["retrieved_at_utc"] = tomorrow.isoformat()
            return record, meta
        result = self.batch(limit=1, fetcher=later_fetch, now=tomorrow)
        self.assertEqual(result["newly_captured_this_run"], 1)

    def test_failed_request_is_partial_not_fake_full_success(self):
        def fail_first(nct, timeout=20):
            if nct == self.ncts[0]:
                raise TimeoutError("synthetic failure")
            return self.fake_fetch(nct, timeout)
        result = self.batch(limit=5, fetcher=fail_first)
        self.assertEqual(result["newly_captured_this_run"], 4)
        self.assertEqual(result["failed_attempts_this_run"], 1)
        self.assertEqual(result["fresh_exact_registry_captures"], 4)
        self.assertEqual(result["source_state"], "PARTIAL_SOURCE_CAPTURE")
        self.assertFalse((self.dir / f"{self.ncts[0]}.json").exists())

    def test_live_batch_uses_end_clock_when_receipts_follow_start(self):
        # Reproduces the observed bug: all requests succeed, but their receipt
        # timestamps are newer than the clock captured at batch start.
        times = iter([NOW - timedelta(seconds=2), NOW, NOW + timedelta(seconds=1)])
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return next(times)
        with patch.object(MODULE, "datetime", Clock):
            result = MODULE.capture_batch(
                self.ncts, COHORT, self.dir, 1, fetcher=self.fake_fetch
            )
        self.assertEqual(result["network_attempts_this_run"], 1)
        self.assertEqual(result["newly_captured_this_run"], 1)
        self.assertEqual(result["failed_attempts_this_run"], 0)
        self.assertEqual(result["fresh_exact_registry_captures"], 1)
        self.assertEqual(result["remaining_without_fresh_capture"], 28)

    def test_prior_successful_downloads_are_recounted_without_network(self):
        first = self.batch(limit=29)
        self.assertEqual(first["fresh_exact_registry_captures"], 29)
        def network_must_not_run(nct, timeout=20):
            raise AssertionError("Already cached NCT was fetched again")
        later = self.batch(limit=29, fetcher=network_must_not_run,
                           now=NOW + timedelta(minutes=5))
        self.assertEqual(later["network_attempts_this_run"], 0)
        self.assertEqual(later["newly_captured_this_run"], 0)
        self.assertEqual(later["fresh_exact_registry_captures"], 29)
        self.assertEqual(later["source_state"], "ALL_FRESH_SOURCE_ONLY")

    def test_duplicate_or_malformed_nct_blocks_capture(self):
        for bad in ([*self.ncts[:-1], self.ncts[0]], ["../private", *self.ncts[1:]]):
            with self.subTest(value=bad[0]):
                with self.assertRaises(ValueError):
                    MODULE.capture_batch(bad, COHORT, self.dir, 5, fetcher=self.fake_fetch, now=NOW)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
