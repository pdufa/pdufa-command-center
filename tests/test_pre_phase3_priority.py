"""Full-universe review ranking, source boundaries and clinical separation."""
import copy
import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase3_issuer_readouts import ANNOUNCED
from pre_phase3_priority import attach_review_priorities, POINT_COLUMNS, _timing
from pre_phase3_scoring_review import scoring_review_queue
from step7_live import build_snapshot, write_csv

NOW = datetime(2026, 10, 11, 14, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(hours=1)).isoformat()


def trial(**updates):
    row = {
        "Ticker": "ABC", "NCT ID": "NCT12345678", "Drug": "Drug A", "Indication": "Disease A",
        "NCT source": "https://clinicaltrials.gov/study/NCT12345678",
        "Trial phase": "Phase 3", "Registry status": "RECRUITING",
        "Registry results posted": "", "Issuer Phase 3 readout": "NOT VERIFIED HERE",
        "Phase 3 trial type": "PIVOTAL EFFICACY DESIGN — SOURCE CHECKED",
        "Company/program identity": "VERIFIED", "Registry check": "RECENT",
        "Last trial check UTC": RECENT, "Protocol check": "RECENT",
        "Protocol as of UTC": RECENT, "Protocol source": "https://clinicaltrials.gov/study/NCT12345678",
        "Design inputs present /6": 6, "Phase 2 PRIMARY evidence count": 1,
        "Phase 2 PRIMARY first observed UTC": RECENT,
        "Phase 2 PRIMARY registry sources": "https://clinicaltrials.gov/study/NCT11112222",
        "Linked Phase 2 PRIMARY p": "NCT11112222 p=0.2",
        "Registry primary completion": "2026-11-15", "Market cap state": "VERIFIED RECENT",
        "Market cap USD": 500_000_000, "Market cap as of UTC": RECENT,
        "Market source": "https://api.nasdaq.com/api/quote/ABC/summary",
        "Preliminary clinical score /100": None, "Pre-readout research score /100": None,
        "Score status": "NOT SCORED — EVIDENCE INCOMPLETE", "ENTRY READY": "NO — unverified",
    }
    row.update(updates)
    return row


class ReviewPriorityTests(unittest.TestCase):
    def score(self, row):
        return attach_review_priorities([row], NOW)[0]

    def test_full_readiness_can_score_100_without_inventing_clinical_score(self):
        source = trial()
        before = copy.deepcopy(source)
        row = self.score(source)
        self.assertEqual(row["Review priority /100"], 100)
        self.assertEqual(row["Review priority rank"], 1)
        self.assertIsNone(row["Pre-readout research score /100"])
        self.assertIsNone(row["Preliminary clinical score /100"])
        self.assertEqual(source, before)
        self.assertEqual(row["ENTRY READY"], before["ENTRY READY"])
        self.assertIn("ISSUER STATUS UNCHECKED", row["Review priority status"])

    def test_clinical_judgments_do_not_change_priority_points(self):
        baseline = self.score(trial())
        changed = self.score(trial(**{"Preliminary clinical score /100": 99,
                                     "Pre-readout research score /100": 88}))
        self.assertEqual(changed["Review priority /100"], baseline["Review priority /100"])
        self.assertEqual(changed["Preliminary clinical score /100"], 99)
        self.assertEqual(changed["Pre-readout research score /100"], 88)

    def test_explicit_scope_exclusions_get_zero_and_no_rank(self):
        cases = [
            {"Issuer Phase 3 readout": ANNOUNCED},
            {"Registry results posted": "2026-10-10"},
            {"Registry status": "COMPLETED"}, {"Registry status": "TERMINATED"},
            {"Registry status": "UNKNOWN"}, {"Market cap state": "NOT LISTED — MERGER CLOSED"},
            {"Phase 3 trial type": "NON-PIVOTAL EFFICACY — SAFETY / OPEN LABEL"},
            {"NCT source": "https://clinicaltrials.gov/study/NCT87654321"},
            {"NCT ID": "INVALID"}, {"Ticker": ""}, {"Trial phase": "Unknown"}, {"Drug": "Placebo"},
        ]
        for change in cases:
            with self.subTest(change=change):
                row = self.score(trial(**change))
                self.assertEqual(row["Review priority /100"], 0)
                self.assertIsNone(row["Review priority rank"])
                self.assertTrue(row["Review priority status"].startswith("EXCLUDED"))
                self.assertIsNone(row["Pre-readout research score /100"])
                self.assertEqual(sum(row[c] for c in POINT_COLUMNS), 0)

    def test_missing_inputs_are_gaps_not_negative_clinical_verdicts(self):
        row = self.score(trial(**{"Company/program identity": "REVIEW", "Drug": "",
                                 "Registry check": "STALE", "Protocol check": "STALE",
                                 "Phase 2 PRIMARY evidence count": 0, "Registry primary completion": "",
                                 "Market cap USD": None}))
        self.assertEqual(row["Review priority /100"], 30)
        self.assertIn("IDENTITY REVIEW FIRST", row["Review priority status"])
        self.assertIn("PRIMARY", row["Review priority gaps"])
        self.assertIn("Verify exact", row["Review priority next action"])

    def test_fresh_flags_cannot_override_missing_naive_future_or_stale_timestamps(self):
        for stamp in ("", "2026-10-11T13:00:00", (NOW + timedelta(seconds=1)).isoformat(),
                      (NOW - timedelta(days=4)).isoformat()):
            with self.subTest(stamp=stamp):
                row = self.score(trial(**{"Last trial check UTC": stamp, "Protocol as of UTC": stamp,
                                         "Market cap as of UTC": stamp}))
                for key in ("Priority registry /10", "Priority protocol /15", "Priority market cap /5"):
                    self.assertEqual(row[key], 0)

    def test_exact_protocol_source_and_bounded_field_count_required(self):
        wrong = self.score(trial(**{"Protocol source": "https://clinicaltrials.gov/study/NCT87654321"}))
        self.assertEqual(wrong["Priority protocol /15"], 0)
        for count, expected in ((-5, 0), (5, 12), (99, 15), ("unknown", 0)):
            self.assertEqual(self.score(trial(**{"Design inputs present /6": count}))["Priority protocol /15"], expected)

    def test_p_magnitude_and_number_of_analyses_do_not_boost_priority(self):
        weak = self.score(trial(**{"Linked Phase 2 PRIMARY p": "NCT11112222 p=0.9"}))
        strong = self.score(trial(**{"Linked Phase 2 PRIMARY p": "NCT11112222 p=0.000001",
                                     "Phase 2 PRIMARY evidence count": 100}))
        self.assertEqual(weak["Review priority /100"], strong["Review priority /100"])
        self.assertEqual(strong["Priority Phase 2 evidence /15"], 15)

    def test_linked_evidence_requires_source_identity_and_observation_cutoff(self):
        for update in ({"Phase 2 PRIMARY first observed UTC": ""},
                       {"Phase 2 PRIMARY first observed UTC": (NOW + timedelta(seconds=1)).isoformat()},
                       {"Phase 2 PRIMARY registry sources": "https://example.com/NCT11112222"},
                       {"Phase 2 PRIMARY registry sources": "https://clinicaltrials.gov/study/NCT33334444"}):
            self.assertEqual(self.score(trial(**update))["Priority Phase 2 evidence /15"], 0)

    def test_month_precision_uses_entire_interval_and_past_dates_need_recheck(self):
        today = NOW.date()
        self.assertEqual(_timing("2027-01-09", today)[0], 10)
        self.assertEqual(_timing("2027-01", today)[0], 7)
        current = _timing("2026-10", today)
        self.assertEqual(current[0], 7)
        self.assertIn("exact day unknown", current[1])
        self.assertEqual(_timing("2026-09", today)[0], 5)
        self.assertEqual(_timing("2025-09", today)[0], 0)
        self.assertEqual(_timing("2026-13", today)[0], 0)

    def test_priority_date_uses_pacific_day(self):
        midnight_utc = datetime(2026, 10, 12, 1, tzinfo=timezone.utc)
        row = attach_review_priorities([trial(**{"Registry primary completion": "2027-01-09"})], midnight_utc)[0]
        self.assertEqual(row["Priority timing /10"], 10, "Pacific day is still October 11")
        with self.assertRaises(ValueError):
            attach_review_priorities([trial()], datetime(2026, 10, 11))

    def test_stable_global_rank_uses_exact_trial_ties_and_survives_filtering(self):
        a = trial()
        b = trial(**{"Ticker": "XYZ"})
        excluded = trial(**{"Ticker": "ZZZ", "Registry status": "COMPLETED"})
        left = attach_review_priorities([b, excluded, a], NOW)
        right = attach_review_priorities([a, b, excluded], NOW)
        ranks = lambda rows: {(r["Ticker"], r["NCT ID"]): r["Review priority rank"] for r in rows}
        self.assertEqual(ranks(left), ranks(right))
        filtered = [r for r in left if r["Ticker"] == "XYZ"]
        self.assertEqual(filtered[0]["Review priority rank"], 2)
        worklist = scoring_review_queue(filtered)
        self.assertEqual(worklist[0]["Review priority rank"], 2)
        self.assertEqual(worklist[0]["Review priority /100"], filtered[0]["Review priority /100"])

    def test_market_fit_points_do_not_remove_large_companies(self):
        row = self.score(trial(**{"Market cap USD": 100_000_000_000, "Market cap state": "OUTSIDE $300M–$10B"}))
        self.assertEqual(row["Priority market cap /5"], 0)
        self.assertIsNotNone(row["Review priority rank"])
        self.assertEqual(self.score(trial(**{"Market cap USD": float("inf")}))["Priority market cap /5"], 0)

    def test_repository_snapshot_and_csv_cover_every_exact_trial(self):
        rows, _, manifest = build_snapshot(Path(__file__).resolve().parents[1] / "data", NOW)
        self.assertGreater(len(rows), 1000)
        self.assertEqual(manifest["review_priority_rows"], len(rows))
        self.assertEqual(manifest["review_priority_ranked"] + manifest["review_priority_excluded"], len(rows))
        ranks = []
        for row in rows:
            self.assertIsInstance(row["Review priority /100"], int)
            self.assertTrue(0 <= row["Review priority /100"] <= 100)
            self.assertEqual(row["Review priority /100"], sum(row[c] for c in POINT_COLUMNS))
            if row["Review priority rank"] is not None:
                ranks.append(row["Review priority rank"])
            else:
                self.assertEqual(row["Review priority /100"], 0)
        self.assertEqual(sorted(ranks), list(range(1, len(ranks) + 1)))
        self.assertEqual(len({(r["Ticker"], r["NCT ID"]) for r in rows}), len(rows))
        for ticker, nct in [("ABVX", "NCT05535946"), ("ACAD", "NCT06173531"), ("LBRX", "NCT07369154")]:
            found = next(r for r in rows if r["Ticker"] == ticker and r["NCT ID"] == nct)
            self.assertEqual(found["Review priority /100"], 0)
            self.assertIsNone(found["Review priority rank"])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "priorities.csv"
            write_csv(path, rows)
            with path.open(newline="", encoding="utf-8") as handle:
                exported = list(csv.DictReader(handle))
            self.assertEqual(len(exported), len(rows))
            self.assertTrue(all(r["Review priority /100"] != "" for r in exported))


if __name__ == "__main__":
    unittest.main()
