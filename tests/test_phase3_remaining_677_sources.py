import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_phase3_original_registry_pilot import SOURCE_CSV
from check_phase3_64_original_sources import select_64_original_studies
from check_phase3_remaining_677_sources import (
    select_remaining_677, bulk_group_url, reconcile_bulk_group,
    summarize_677, run_remaining, BATCH_SIZE, EXPECTED_REMAINING,
)


CENSUS = SOURCE_CSV.read_text(encoding="utf-8-sig")
VERSION = {"dataTimestamp": "2026-10-26T09:00:00", "apiVersion": "2.0.5"}
DATE = "2026-10-26T15:00:00+00:00"


def sample():
    return select_remaining_677(CENSUS)


def registry_payload(row):
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": row["nct_id"],
                "briefTitle": "Public research registry study for exact NCT",
            },
            "statusModule": {
                "overallStatus": row["status"], "lastUpdatePostDate": "2026-05-20",
            },
            "designModule": {"phases": ["PHASE3"]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": row["company"]}},
        }
    }


def reconciled_results(rows):
    out = []
    for start in range(0, len(rows), BATCH_SIZE):
        group = rows[start:start+BATCH_SIZE]
        out.extend(reconcile_bulk_group({
            "studies": [registry_payload(row) for row in group],
        }, group, DATE))
    return out


class Remaining677ResearchTests(unittest.TestCase):
    def test_exact_complement_of_64_coverage_covers_all_original_741(self):
        remaining = sample()
        first = select_64_original_studies(CENSUS)
        self.assertEqual(len(remaining), EXPECTED_REMAINING)
        self.assertEqual(len({row["nct_id"] for row in remaining}), EXPECTED_REMAINING)
        self.assertFalse({row["nct_id"] for row in first}.intersection(
            row["nct_id"] for row in remaining))
        self.assertEqual(len({r["nct_id"] for r in remaining + first}), 741)
        self.assertEqual(remaining, sample())

    def test_25_exact_nct_request_has_no_arbitrary_source_hosts(self):
        group = sample()[:25]
        url = bulk_group_url(group)
        self.assertTrue(url.startswith("https://clinicaltrials.gov/api/v2/studies?"))
        self.assertIn("filter.ids=NCT", url)
        self.assertIn("pageSize=25", url)
        self.assertEqual(len(group), 25)
        for wrong in ([], group + [group[0]], group[:24] + [group[0]],
                      [{**group[0], "nct_id": "https://attacker.com"}]):
            with self.assertRaises(ValueError):
                bulk_group_url(wrong)

    def test_batch_exact_ids_reconcile_and_canonical_hashes_never_qualify_pipeline(self):
        group = sample()[:25]
        raw = {"studies": [registry_payload(r) for r in reversed(group)]}
        observations = reconcile_bulk_group(raw, group, DATE)
        self.assertEqual([o["nct_id"] for o in observations],
                         [r["nct_id"] for r in group])
        self.assertTrue(all(len(o["canonical_returned_study_sha256"]) == 64
                            for o in observations))
        self.assertTrue(all(o["qualified_pipeline"] is None
                            and o["fda_approval_probability"] is None
                            and not o["verified_us_fda_pdufa"]
                            and not o["verified_current_commercial_development_rights"]
                            for o in observations))
        self.assertTrue(all(o["source_retrieval_method"] == "batch_filter_ids"
                            for o in observations))
        self.assertTrue(all("source_sha256" not in o for o in observations))
        self.assertTrue(all(o["status_matches_dated_census"] for o in observations))

    def test_source_missing_study_never_appears_as_a_success(self):
        group = sample()[:25]
        payload = {"studies": [registry_payload(row) for row in group[:-1]]}
        results = reconcile_bulk_group(payload, group, DATE)
        self.assertEqual(len(results), 25)
        self.assertEqual(results[-1]["error"], "NOT_RETURNED_BY_ORIGINAL_REGISTRY")

    def test_forged_extra_duplicate_wrong_nct_and_overpagination_rejected(self):
        group = sample()[:25]
        originals = [registry_payload(row) for row in group]
        with self.assertRaises(ValueError):
            reconcile_bulk_group({"studies": originals + [originals[0]]}, group, DATE)
        with self.assertRaises(ValueError):
            reconcile_bulk_group({"studies": originals, "nextPageToken": "extra"}, group, DATE)
        wrong = copy.deepcopy(originals)
        wrong[0]["protocolSection"]["identificationModule"]["nctId"] = "NCT00000000"
        with self.assertRaises(ValueError):
            reconcile_bulk_group({"studies": wrong}, group, DATE)
        with self.assertRaises(ValueError):
            reconcile_bulk_group({"studies": "corrupted"}, group, DATE)
        with self.assertRaises(ValueError):
            reconcile_bulk_group({"studies": originals + [registry_payload(group[0])]},group,DATE)

    def test_all_677_success_preserves_unknown_fda_and_registry_snapshot_version(self):
        remaining = sample()
        report = summarize_677(remaining, reconciled_results(remaining), VERSION, VERSION)
        self.assertEqual(report["exact_registry_studies_retrieved"], 677)
        self.assertEqual(report["source_unavailable_count"], 0)
        self.assertTrue(report["registry_version_stable"])
        self.assertTrue(report["all_remaining_source_ids_retrieved"])
        self.assertEqual(report["status_differences_from_census"], [])
        self.assertEqual(report["phase3_not_currently_reported"], [])
        for flag in ("qualified_pipeline_count","verified_us_fda_pdufa_count",
                     "validated_fda_approval_probabilities"):
            self.assertIsNone(report[flag])
        self.assertEqual(len(report["source_observations"]), 677)

    def test_version_drift_or_missing_source_never_admits_complete_batch(self):
        remaining = sample()
        originals = reconciled_results(remaining)
        different = {**VERSION, "dataTimestamp": "2026-10-27T09:00:00"}
        for before, after in ((VERSION, different), (None, VERSION),
                              (VERSION, None), (VERSION, {**VERSION, "apiVersion": "3"})):
            report = summarize_677(remaining, originals, before, after)
            self.assertFalse(report["all_remaining_source_ids_retrieved"])
        originals[3] = {"nct_id": remaining[3]["nct_id"], "error": "BATCH_SOURCE_UNVERIFIED"}
        report = summarize_677(remaining, originals, VERSION, VERSION)
        self.assertFalse(report["all_remaining_source_ids_retrieved"])
        self.assertEqual(report["source_unavailable_count"], 1)
        self.assertEqual(report["exact_registry_studies_retrieved"], 676)
        self.assertEqual(report["source_failures"][0]["nct_id"], remaining[3]["nct_id"])

    def test_forged_pipeline_fda_source_ticker_and_count_fail_closed(self):
        remaining = sample()
        base = reconciled_results(remaining)
        for field, value in (
            ("qualified_pipeline", True),
            ("verified_us_fda_pdufa", True),
            ("verified_current_commercial_development_rights", True),
            ("fda_approval_probability", 0.8),
            ("census_ticker", "FAKE"),
            ("source", "https://invalid.tld/api/v2/studies/" + remaining[0]["nct_id"]),
            ("canonical_returned_study_sha256", "spoofed"),
            ("source_retrieval_method", "unknown"),
        ):
            changed = [dict(r) for r in base]
            changed[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize_677(remaining, changed, VERSION, VERSION)
        with self.assertRaises(ValueError):
            summarize_677(remaining, base[:-1], VERSION, VERSION)
        with self.assertRaises(ValueError):
            summarize_677(remaining, list(reversed(base)), VERSION, VERSION)

    def test_bulk_run_captures_disconnected_source_rows_without_fabricating_success(self):
        rem = sample()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "unverified.json"
            with patch("check_phase3_remaining_677_sources.registry_version",
                       return_value=VERSION), patch(
                    "check_phase3_remaining_677_sources.safe_fetch_group",
                    side_effect=lambda group: [
                        {"nct_id": row["nct_id"], "error": "BATCH_SOURCE_UNVERIFIED"}
                        for row in group]):
                outcome = run_remaining(output)
            self.assertEqual(outcome, 1)
            report = json.loads(output.read_text())
            self.assertFalse(report["all_remaining_source_ids_retrieved"])
            self.assertEqual(report["source_unavailable_count"], 677)
            self.assertEqual(report["requested_remaining_count"], 677)
            self.assertIsNone(report["qualified_pipeline_count"])
            self.assertEqual(report["requested_remaining_ids"], [r["nct_id"] for r in rem])


if __name__ == "__main__":
    unittest.main()
