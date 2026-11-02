"""Offline safety tests for automatic Phase 3 registry-posting table refresh."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/refresh_phase3_registry_postings.py"
spec = importlib.util.spec_from_file_location("refresh_phase3_registry_postings", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def census(count=741):
    return [{
        "nct_id": f"NCT{i:08d}", "ticker": "TEST",
        "company": "Fictional Issuer", "status": "COMPLETED",
        "source_url": f"https://clinicaltrials.gov/study/NCT{i:08d}"
    } for i in range(1, count + 1)]


def response(ids, posted=None, duplicate=False, missing=False):
    studies = []
    for nct in ids:
        date = (posted or {}).get(nct, "")
        study = {
            "protocolSection": {
                "identificationModule": {"nctId": nct},
                "statusModule": {
                    "resultsFirstPostDateStruct": {"date": date} if date else None
                },
            },
        }
        studies.append(study)
    if missing:
        studies.pop()
    if duplicate:
        studies[0] = studies[1]
    return {"studies": studies}


class RefreshRegistryPostingTests(unittest.TestCase):
    def setUp(self):
        self.rows = census()
        self.now = datetime(2026, 11, 1, tzinfo=timezone.utc)

    def test_full_741_NCTs_split_without_duplicates(self):
        first = self.rows[0]["nct_id"]
        second = self.rows[1]["nct_id"]
        def requester(ids):
            return response(ids, {first:"2026-10-28", second:"2026-10-29"})
        result = module.build_snapshot(self.rows, requester, self.now, 25)
        self.assertEqual(result["total"], 741)
        self.assertEqual(result["resultsPosted"], 2)
        self.assertEqual(result["noResultsPosted"], 739)
        self.assertEqual(len(set(r["nctId"] for r in result["records"])), 741)
        self.assertEqual(result["records"][0]["resultsFirstPostedDate"],"2026-10-28")
        self.assertEqual(result["sourceKind"],"OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT")

    def test_different_refresh_moves_one_NCT_only(self):
        nct = self.rows[10]["nct_id"]
        old = module.build_snapshot(self.rows, lambda ids:response(ids), self.now)
        new = module.build_snapshot(
            self.rows,lambda ids:response(ids,{nct:"2026-10-31"}),self.now
        )
        self.assertEqual(old["noResultsPosted"],741)
        self.assertEqual(new["noResultsPosted"],740)
        self.assertEqual(new["resultsPosted"],1)

    def test_missing_duplicate_or_pagination_refused(self):
        for requester in (
            lambda ids:response(ids,missing=True),
            lambda ids:response(ids,duplicate=True),
            lambda ids:dict(response(ids),nextPageToken="unread"),
        ):
            with self.assertRaises(ValueError):
                module.build_snapshot(self.rows,requester,self.now)

    def test_future_result_date_refused(self):
        nct=self.rows[0]["nct_id"]
        with self.assertRaises(ValueError):
            module.build_snapshot(self.rows,lambda ids:response(ids,{nct:"2026-11-05"}),self.now)

    def test_publish_atomic_and_old_snapshot_preserved_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"phase3-results.json"
            baseline={"total":730,"previous":"last good"}
            module.atomic_publish(out,baseline)
            before=out.read_bytes()
            with self.assertRaises(ValueError):
                module.build_snapshot(
                    self.rows,lambda ids:response(ids,missing=True),self.now
                )
            self.assertEqual(out.read_bytes(),before)
            self.assertEqual(json.loads(out.read_text()),baseline)

    def test_invalid_census_not_published(self):
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/"census.csv"
            f.write_text("nct_id,ticker,company,status,source_url\nNCT00000001,TEST,Fictional,COMPLETED,https://clinicaltrials.gov/study/NCT00000001\n")
            with self.assertRaises(ValueError):
                module.census_rows(f)


if __name__=="__main__":
    unittest.main()
