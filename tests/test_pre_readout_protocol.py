"""Prospective Phase 3 protocol intake and coverage: no outcomes or future leakage."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pre_readout import build_scorecard
from scripts.pre_readout_protocol_intake import eligible_ids, protocol_only

TODAY = date(2026, 10, 10)


def trial(**other):
    x = dict(nct_id="NCT12345678", ticker="BIO", company="BIO INC",
             drug="BIO-1", indication="Condition A", phase="PHASE3",
             status="RECRUITING", results_posted="", primary_completion="2027-02-02",
             source_url="https://clinicaltrials.gov/study/NCT12345678",
             checked_at="2026-10-10T12:00:00Z",
             reported_p_values="p=0.001", actual_fda_decision="APPROVED")
    x.update(other)
    return x


def cap(**other):
    x = dict(ticker="BIO", market_cap="1200000000", market_cap_status="VERIFIED",
             market_cap_checked_at="2026-10-10T12:00:00Z")
    x.update(other)
    return x


def design(**other):
    x = dict(nct_id="NCT12345678", primary_endpoint="Change in symptom score",
             primary_timeframe="Week 24", allocation="RANDOMIZED",
             masking="DOUBLE", comparator="Placebo", enrollment="400",
             enrollment_type="ESTIMATED", study_type="INTERVENTIONAL",
             source_url="https://clinicaltrials.gov/study/NCT12345678",
             checked_at="2026-10-10T12:00:00Z")
    x.update(other)
    return x


class PreReadoutProtocolTests(unittest.TestCase):
    def test_current_protocol_coverage_is_not_success_probability(self):
        rows = build_scorecard([trial()], [design()], [cap()], as_of=TODAY)
        self.assertEqual(len(rows), 1)
        r = rows.iloc[0]
        self.assertEqual(r["Evidence Score / 100"], 75)
        self.assertEqual(r["Phase 3 Success Probability"], "NOT CALIBRATED")
        self.assertIn("Phase 2 efficacy", r["Evidence Gaps"])
        self.assertIn("FDA alignment", r["Evidence Gaps"])
        self.assertNotIn("0.001", str(r))
        self.assertNotIn("APPROVED", str(r))

    def test_no_results_past_or_present_and_no_stopped_trials(self):
        for item in (
            trial(results_posted="2026-10-09"),
            trial(results_posted="2026-10-11"),
            trial(status="COMPLETED"),
            trial(status="TERMINATED"),
            trial(status="SUSPENDED"),
        ):
            self.assertTrue(build_scorecard([item], [design()], [cap()],
                                            as_of=TODAY).empty)
        notice = [{"nct_id":"NCT12345678",
                   "phase3_results_posted_at":"2026-10-09"}]
        self.assertTrue(build_scorecard([trial()], [design()], [cap()],
                                        announcements=notice, as_of=TODAY).empty)

    def test_pre_readout_historical_cutoff_cannot_use_future_snapshot(self):
        old = date(2026, 10, 8)
        self.assertTrue(build_scorecard([trial()], [design()], [cap()],
                                        as_of=old).empty)
        x = trial(checked_at="2026-10-01")
        y = cap(market_cap_checked_at="2026-10-01")
        result = build_scorecard([x], [design()], [y], as_of=old)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Coverage"], "PROTOCOL NOT COLLECTED")

    def test_unverified_market_cap_never_qualifies(self):
        for state in ("REVIEW", "UNAVAILABLE", ""):
            out = build_scorecard([trial()], [design()],
                                  [cap(market_cap_status=state)], as_of=TODAY)
            self.assertTrue(out.empty)

    def test_collector_never_reads_results_section(self):
        study = {
            "protocolSection": {
                "identificationModule":{"nctId":"NCT12345678"},
                "statusModule":{"studyFirstPostDateStruct":{"date":"2025-01-10"}},
                "designModule":{
                    "studyType":"INTERVENTIONAL",
                    "designInfo":{"allocation":"RANDOMIZED",
                                  "maskingInfo":{"masking":"DOUBLE"}},
                    "enrollmentInfo":{"count":400,"type":"ESTIMATED"},
                },
                "outcomesModule":{"primaryOutcomes":[
                    {"measure":"Symptom score","timeFrame":"Week 24"}]},
                "armsInterventionsModule":{
                    "interventions":[{"name":"Placebo","type":"DRUG"}],
                    "armGroups":[{"label":"Placebo group","type":"PLACEBO_COMPARATOR"}],
                },
            },
            "resultsSection":{
                "outcomeMeasuresModule":{"outcomeMeasures":[
                    {"type":"PRIMARY","analyses":[{"pValue":"0.000001"}]}]},
                "adverseEventsModule":{"seriousNumAffected":"37"},
            },
        }
        safe = protocol_only(study,checked_at="2026-10-10")
        text = repr(safe)
        self.assertEqual(safe["allocation"], "RANDOMIZED")
        self.assertEqual(safe["primary_endpoint"], "Symptom score")
        self.assertNotIn("0.000001", text)
        self.assertNotIn("37", text)
        self.assertEqual(safe["registry_results_first_posted"], "")
        self.assertEqual(safe["registry_overall_status"], "")
        self.assertEqual(set(safe), {
            "nct_id","primary_endpoint","primary_timeframe","allocation","masking",
            "intervention_model","comparator","enrollment","enrollment_type",
            "study_type","first_posted","source_updated","source_url","checked_at",
            "registry_overall_status","registry_results_first_posted",
        })

    def test_collector_does_not_collect_excluded_phase_or_bad_cap(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def write(name,records):
                with (root/name).open("w",newline="",encoding="utf-8") as f:
                    writer=csv.DictWriter(f,fieldnames=list(records[0]))
                    writer.writeheader();writer.writerows(records)
            write("all_phase_trials.csv",[trial(),trial(nct_id="NCT99999999",phase="PHASE2")])
            write("phase_pipeline_market_caps.csv",[cap()])
            write("phase3_announcements.csv",[
                {"nct_id":"", "phase3_results_posted_at":""}
            ])
            self.assertEqual(set(eligible_ids(root,TODAY)),{"NCT12345678"})
            write("phase3_announcements.csv",[
                {"nct_id":"NCT12345678","phase3_results_posted_at":"2026-10-09"}
            ])
            self.assertFalse(eligible_ids(root,TODAY))


if __name__=="__main__":
    unittest.main()
