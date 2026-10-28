"""Read-only historical GEM/GEM JR NCT-candidate audit safety tests.

The fixture archive IDs below simulate archived metadata. No live Neon or
Render records are imported; real archive availability must be separately
verified by read-only provider queries.
"""
import json
import unittest
from copy import deepcopy
from pathlib import Path

from app.scientific_historical_crosswalk import audit_historical_crosswalk

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "snapshot" / "gem_stage_membership.json"


def saved_snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def hints(snapshot):
    result = set()
    for stage in ("GEM", "GEM_JR"):
        for entry in snapshot["stages"][stage]["entries"].values():
            raw = entry.get("nct_id", "")
            if raw:
                result.update(raw.split("|"))
    return result


def assess(snapshot=None, archived=None):
    snapshot = saved_snapshot() if snapshot is None else snapshot
    return audit_historical_crosswalk(
        snapshot, reference_date="2026-10-25",
        archived_nct_ids=hints(snapshot) if archived is None else archived,
    )


class HistoricalStageCrosswalkTests(unittest.TestCase):
    def test_real_saved_october_snapshot_never_becomes_current_membership(self):
        report = assess()
        self.assertEqual(report["historical_entries"], 19)
        self.assertEqual(report["one_trial_hint_entries"], 16)
        self.assertEqual(report["multi_trial_hint_entries"], 1)
        self.assertEqual(report["no_trial_hint_entries"], 2)
        self.assertEqual(report["direct_trial_source_entries"], 3)
        self.assertEqual(report["application_trial_review_queue"], 14)
        self.assertEqual(report["distinct_hinted_trials"], 17)
        self.assertEqual(report["distinct_archived_hinted_trials"], 17)
        self.assertEqual(report["snapshot_ages_days"], {"GEM": 9, "GEM_JR": 9})
        self.assertTrue(report["freshness_lapsed"])
        self.assertTrue(report["historical_snapshot_only"])
        self.assertFalse(report["current_membership_verified"])
        self.assertEqual(report["approved_regulatory_trial_crosswalks"], 0)
        self.assertEqual(report["independently_verified_clinical_sources"], 0)
        self.assertEqual(report["suggested_automatic_import_batches"], [])
        self.assertFalse(report["import_executed"])
        self.assertFalse(report["presets_modified"])
        self.assertIsNone(report["fda_approval_probability"])

    def test_pipe_delimited_multiple_trials_preserved_without_arbitrary_pick(self):
        report = assess()
        entries = [r for r in report["records"] if len(r["hinted_nct_ids"]) > 1]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["hinted_nct_ids"],
                         ["NCT05630807", "NCT05630820"])
        self.assertEqual(entries[0]["association_status"],
                         "APPLICATION_TRIAL_ASSOCIATION_REQUIRES_REVIEW")
        self.assertFalse(entries[0]["automatic_crosswalk_performed"])
        self.assertFalse(entries[0]["scientifically_verified"])

    def test_missing_neon_archive_is_explicit_and_not_invented(self):
        snapshot = saved_snapshot()
        all_ids = hints(snapshot)
        absent = "NCT05630820"
        report = assess(snapshot, archived=all_ids - {absent})
        self.assertEqual(report["distinct_hinted_trials"], 17)
        self.assertEqual(report["distinct_archived_hinted_trials"], 16)
        self.assertEqual(report["missing_archive_nct_ids"], [absent])
        self.assertEqual(report["suggested_automatic_import_batches"], [])

    def test_no_nct_hint_never_inferred_from_ticker_or_drug(self):
        report = assess()
        missing = [r for r in report["records"] if not r["hinted_nct_ids"]]
        self.assertEqual(len(missing), 2)
        self.assertTrue(all(r["association_status"] == "NO_EXACT_TRIAL_HINT"
                            for r in missing))
        self.assertTrue(all(r["archive_matched_nct_ids"] == [] for r in missing))

    def test_unparseable_source_nct_hints_fail_closed(self):
        snapshot = saved_snapshot()
        key = "APPLICATION|IONS|BEPIROVIRSEN_CHB_20261026"
        for invalid in ("NCT05630807|BAD", "NCT05630807|NCT05630807",
                        "NCT05630807|", "TRIAL|NCT05630807", "NCT1"):
            changed = deepcopy(snapshot)
            changed["stages"]["GEM_JR"]["entries"][key]["nct_id"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                assess(changed)

    def test_direct_trial_source_must_match_expressed_trial_identity(self):
        snapshot = saved_snapshot()
        key = "TRIAL|NCT06445023"
        snapshot["stages"]["GEM_JR"]["entries"][key]["nct_id"] = "NCT06641076"
        with self.assertRaises(ValueError):
            assess(snapshot)

    def test_future_snapshots_and_malformed_source_keys_rejected(self):
        snapshot = saved_snapshot()
        snapshot["stages"]["GEM"]["last_complete_snapshot"] = "2026-11-01"
        with self.assertRaises(ValueError):
            assess(snapshot)
        snapshot = saved_snapshot()
        first = next(iter(snapshot["stages"]["GEM"]["entries"]))
        snapshot["stages"]["GEM"]["entries"][first]["pipeline_id"] = "TRIAL|NCT00000000"
        with self.assertRaises(ValueError):
            assess(snapshot)


if __name__ == "__main__":
    unittest.main()
