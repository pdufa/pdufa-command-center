"""Clinical pilot scoring: exact-NCT, dated source, and strict separation tests."""
import json
import unittest
from datetime import date
from pathlib import Path

from pre_phase3_pilot_scores import RUBRIC, attach_preliminary_scores, review_index, reviewed_phase2_link

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / "data/pre_phase3_pilot_clinical_reviews.json").read_text(encoding="utf-8"))


def trial(ticker="TRVI", nct="NCT07671911", **updates):
    r = {
        "Ticker": ticker, "NCT ID": nct,
        "Drug": "NAL ER", "Indication": "Idiopathic Pulmonary Fibrosis",
        "Trial phase": "Phase 3", "Registry status": "RECRUITING",
        "Registry results posted": "",
        "NCT source": f"https://clinicaltrials.gov/study/{nct}",
        "Registry check": "RECENT", "Protocol check": "RECENT",
        "Company/program identity": "VERIFIED",
        "Pre-readout research score /100": None,
        "Score status": "NOT SCORED — EVIDENCE INCOMPLETE",
        "ENTRY READY": "NO — NOT VERIFIED",
    }
    r.update(updates)
    return r


def protocol(nct="NCT07671911", **updates):
    r = {
        "nct_id": nct,
        "source_url": f"https://clinicaltrials.gov/study/{nct}",
        "primary_endpoint": "Relative Change from Baseline in 24-hour Cough Frequency at Week 26",
        "comparator": "Placebo",
        "registry_overall_status": "RECRUITING",
        "allocation": "RANDOMIZED",
        "checked_at": "2026-10-10T16:50:00+00:00",
        "source_updated": "2026-09-14",
    }
    r.update(updates)
    return r


class PilotClinicalScoreTests(unittest.TestCase):
    def test_actual_provisional_numbers_are_present_and_not_a_success_probability(self):
        self.assertEqual(sum(RUBRIC.values()), 100)
        inputs = [
            trial(),
            trial("LBRX", "NCT07363577", **{"Drug":"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",
                 "Indication":"Schizophrenia", "Company/program identity":"REVIEW"}),
        ]
        p = [protocol(), protocol("NCT07363577", **{
            "primary_endpoint":"Change from baseline to Week 6 on the Positive and Negative Syndrome Scale",
        })]
        rated = attach_preliminary_scores(inputs, p, LEDGER, date(2026,10,10))
        self.assertEqual([x["Preliminary clinical score /100"] for x in rated], [80,72])
        self.assertEqual(rated[0]["Phase 2 Efficacy /25"], 22)
        self.assertEqual(rated[1]["Phase 3 Design /30"], 24)
        for row in rated:
            self.assertIsNone(row["Pre-readout research score /100"])
            self.assertTrue(row["Score status"].startswith("NOT SCORED"))
            self.assertTrue(row["ENTRY READY"].startswith("NO"))
            self.assertIn("NOT AUDITED", row["Preliminary score status"])

    def test_safety_only_open_label_trial_never_inherits_efficacy_score(self):
        impostor=trial("LBRX","NCT07369154",**{
            "Drug":"LB-102","Indication":"Schizophrenia",
        })
        # Even if a mistaken ledger entry reuses the safety-only NCT.
        tampered=json.loads(json.dumps(LEDGER))
        tampered["records"][1]["nct_id"]="NCT07369154"
        rows=attach_preliminary_scores([impostor],[protocol("NCT07369154",
            primary_endpoint="Evaluate long term safety and tolerability of LB-102 by evaluating the number of adverse events",
            comparator="")],tampered,date(2026,10,10))
        self.assertIsNone(rows[0]["Preliminary clinical score /100"])

    def test_wrong_trial_or_future_or_published_results_blocks_score(self):
        for changes in (
            {"Ticker":"OTHER"},
            {"Registry status":"COMPLETED"},
            {"Trial phase":"Phase 2"},
            {"Registry results posted":"2026-10-01"},
            {"NCT source":"https://example.com/study/NCT07671911"},
            {"Registry check":"STALE"},
            {"Protocol check":"STALE"},
            {"Drug":"NAL ER plus another drug"},
            {"Indication":"Other disease | Idiopathic Pulmonary Fibrosis"},
        ):
            row=attach_preliminary_scores([trial(**changes)], [protocol()], LEDGER, date(2026,10,10))[0]
            self.assertIsNone(row["Preliminary clinical score /100"],changes)

    def test_missing_stale_and_future_protocol_dates_do_not_score(self):
        for changes in ({"checked_at":""}, {"checked_at":"2026-10-01"},
                        {"checked_at":"2026-10-11"}, {"source_updated":"2027-01-01"}):
            row=attach_preliminary_scores([trial()], [protocol(**changes)], LEDGER, date(2026,10,10))[0]
            self.assertIsNone(row["Preliminary clinical score /100"])

    def test_phase2_alias_link_requires_exact_trial_drug_and_dated_source(self):
        review=review_index(LEDGER,"2026-10-10")[("LBRX","NCT07363577")]
        row={"ticker":"LBRX","nct_id":"NCT07363577", "drug":review["registry_drug"],
             "indication":"Schizophrenia"}
        link, source=reviewed_phase2_link(row,review,"2026-10-10")
        self.assertEqual(link,"NCT06179108")
        self.assertTrue(source.startswith("https://ir.lbpharma.us/"))
        for updates in ({"ticker":"OTHER"},{"nct_id":"NCT07369154"},
                        {"drug":"LB-102 plus another drug"},{"indication":"Other disease"}):
            self.assertEqual(reviewed_phase2_link(row | updates,review,"2026-10-10"),("",""))
        wrong_source=json.loads(json.dumps(review))
        wrong_source["phase2_link_source"]["published"]="2027-01-01"
        self.assertEqual(reviewed_phase2_link(row,wrong_source,"2026-10-10"),("",""))

    def test_untrusted_and_future_dated_sources_fail_closed(self):
        for field,value in (
            ("url","https://untrusted.example/press-release"),
            ("published","2026-10-10"),
            ("published","2027-01-01"),
        ):
            changed=json.loads(json.dumps(LEDGER))
            changed["records"][0]["domain_sources"]["phase2_efficacy"][field]=value
            scored=attach_preliminary_scores([trial()],[protocol()],changed,date(2026,10,10))[0]
            self.assertIsNone(scored["Preliminary clinical score /100"],field)

    def test_invalid_points_or_duplicate_identity_fail(self):
        broken=json.loads(json.dumps(LEDGER))
        broken["records"][0]["domain_points"]["phase2_efficacy"]=26
        self.assertNotIn(("TRVI","NCT07671911"),review_index(broken,"2026-10-10"))
        repeated=json.loads(json.dumps(LEDGER))
        repeated["records"].append(repeated["records"][0])
        self.assertNotIn(("TRVI","NCT07671911"),review_index(repeated,"2026-10-10"))


if __name__ == "__main__":
    unittest.main()
