"""Corporate readout precedes registry posting: no false prospective scores."""
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from phase3_issuer_readouts import ANNOUNCED, issuer_readout_index
from pre_readout_score import candidate_queue
from pre_readout import build_scorecard
from pre_phase3_scoring_review import scoring_review_queue
from scripts.phase3_results_intake import scan, FIELDS
from step7_live import build_snapshot

NOW = datetime(2026, 10, 11, 6, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def released(**changes):
    row = dict(ticker="ABVX", nct_id="NCT05535946", drug="ABX464",
               indication="Ulcerative Colitis", phase3_results_posted_at="2026-06-01",
               source_type="ISSUER_TOPLINE_RELEASE",
               verification_status="ISSUER_TOPLINE_EXACT_TRIAL_REVIEW",
               phase3_results_source="https://abivax.gcs-web.com/news-releases/maintenance",
               source_list_note="Exact study https://clinicaltrials.gov/study/NCT05535946",
               first_seen_at="2026-10-11T05:59:00+00:00", last_checked_at="2026-10-11T05:59:00+00:00")
    row.update(changes)
    return row


class IssuerReadoutTests(unittest.TestCase):
    def test_primary_sources_dates_and_review_attestation_are_required(self):
        self.assertEqual(len(issuer_readout_index([released()], NOW)), 1)
        for change in (
            dict(verification_status="UNVERIFIED"), dict(source_list_note=""),
            dict(phase3_results_source="https://news.example/maintenance"),
            dict(first_seen_at="2026-10-11T07:00:00+00:00"),
            dict(last_checked_at="2026-10-11T06:01:00+00:00"),
            dict(phase3_results_posted_at="2026-10-12"),
            dict(nct_id="NCTINVALID"), dict(ticker="ACAD"),
        ):
            self.assertEqual(issuer_readout_index([released(**change)], NOW), {}, change)
        self.assertEqual(issuer_readout_index([released()], NOW-timedelta(days=1)), {})
        # Positive proof of an already published readout does not expire.
        self.assertEqual(len(issuer_readout_index([released()], NOW+timedelta(days=30))), 1)

    def test_exact_program_readout_blocks_score_but_never_other_trials(self):
        trial = dict(ticker="ABVX", nct_id="NCT05535946", drug="ABX464",
                     indication="Ulcerative Colitis", phases="PHASE3",
                     trial_status="ACTIVE_NOT_RECRUITING", results_first_posted="",
                     source_updated="2026-07-07", checked_at=NOW.isoformat())
        caps = pd.DataFrame([dict(ticker="ABVX",market_cap=1e9,market_cap_status="VERIFIED",
                                  market_cap_checked_at=NOW.isoformat())])
        announcement = pd.DataFrame([released()])
        self.assertTrue(candidate_queue(pd.DataFrame([trial]),announcement,caps,"2026-10-10").empty)
        with_placebo={**trial,"drug":"ABX464 | Placebo"}
        self.assertTrue(candidate_queue(pd.DataFrame([with_placebo]),announcement,caps,"2026-10-10").empty)
        self.assertTrue(build_scorecard(
            [{**with_placebo,"phase":"PHASE3","status":"ACTIVE_NOT_RECRUITING"}],
            announcements=[released()], as_of=NOW.date(), cap_filter=False,
        ).empty)
        for change in (dict(drug="Other drug"),dict(indication="Other disease"),
                       dict(nct_id="NCT05507203"),dict(drug="ABX464 | Other drug")):
            other = {**trial, **change}
            self.assertEqual(len(candidate_queue(pd.DataFrame([other]),announcement,caps,"2026-10-10")),1)
        work = {"Ticker":"ABVX","NCT ID":"NCT05535946",
                "Issuer Phase 3 readout":ANNOUNCED,
                "Phase 3 trial type":"PIVOTAL EFFICACY DESIGN — SOURCE CHECKED"}
        self.assertEqual(scoring_review_queue([work]), [])

    def test_registry_refresh_retains_separate_earlier_issuer_disclosure(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            with (root/"company_registry.csv").open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["ticker","company"]);w.writeheader()
                w.writerow(dict(ticker="ABVX",company="Abivax S.A."))
            original={key:released().get(key,"") for key in FIELDS}
            with (root/"phase3_announcements.csv").open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(original)
            payload={"studies":[{"protocolSection":{
                "identificationModule":{"nctId":"NCT05535946"},
                "statusModule":{"resultsFirstPostDateStruct":{"date":"2026-10-10"}},
                "sponsorCollaboratorsModule":{"leadSponsor":{"name":"Abivax S.A."}},
                "designModule":{"phases":["PHASE3"]},
                "armsInterventionsModule":{"interventions":[{"type":"DRUG","name":"ABX464"}]},
                "conditionsModule":{"conditions":["Ulcerative Colitis"]},
            }}]}
            with patch("scripts.phase3_results_intake.fetch",return_value=payload):
                scan("daily",1,root)
            with (root/"phase3_announcements.csv").open() as f: rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),2)
            issuer=next(r for r in rows if r["source_type"]=="ISSUER_TOPLINE_RELEASE")
            self.assertEqual(issuer,original)
            registry=next(r for r in rows if r["source_type"]=="CLINICALTRIALS_RESULTS")
            self.assertEqual(registry["phase3_results_posted_at"],"2026-10-10")

    def test_persisted_real_readouts_remain_visible_but_not_pre_scored(self):
        with (ROOT/"data/phase3_announcements.csv").open() as f:
            rows=list(csv.DictReader(f))
        reviews=[r for r in rows if r.get("source_type")=="ISSUER_TOPLINE_RELEASE"]
        self.assertEqual({r["nct_id"] for r in reviews},{"NCT05535946","NCT06173531"})
        now=max(datetime.fromisoformat(r["last_checked_at"]) for r in reviews)+timedelta(seconds=1)
        trials, _, _ = build_snapshot(ROOT/"data",now)
        for nct in ("NCT05535946","NCT06173531"):
            row=next(r for r in trials if r["NCT ID"]==nct)
            self.assertEqual(row["Issuer Phase 3 readout"],ANNOUNCED)
            self.assertTrue(row["Issuer readout source"].startswith("https://"))
            self.assertEqual(row["Registry results posted"],"")
            self.assertIsNone(row["Pre-readout research score /100"])
            self.assertIsNone(row["Preliminary clinical score /100"])
            self.assertEqual(scoring_review_queue([row]),[])
            self.assertTrue(row["ENTRY READY"].startswith("NO"))


if __name__ == "__main__":
    unittest.main()
