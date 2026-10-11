"""Pre-readout score REVIEW worklist must not invent clinical numbers."""
import unittest

from pre_phase3_scoring_review import COLUMNS, scoring_review_queue


def trial(**changes):
    base = {
        "Ticker": "TRVI",
        "NCT ID": "NCT07671911",
        "Drug": "Example therapy",
        "Indication": "Cough",
        "Trial phase": "Phase 3",
        "Registry status": "RECRUITING",
        "Registry results posted": "",
        "NCT source": "https://clinicaltrials.gov/study/NCT07671911",
        "Registry check": "RECENT",
        "Protocol check": "RECENT",
        "Company/program identity": "VERIFIED",
        "Market cap state": "VERIFIED RECENT",
        "Phase 2 PRIMARY evidence count": 3,
        "Linked Phase 2 PRIMARY p": "NCT05964335 p=0.0028",
        "Phase 2 PRIMARY registry sources": "https://clinicaltrials.gov/study/NCT05964335",
        "Pre-readout research score /100": None,
        "Score status": "NOT SCORED — EVIDENCE INCOMPLETE",
    }
    base.update(changes)
    return base


class ScoreReviewQueueTests(unittest.TestCase):
    def test_priority_and_unscored_pilot_only(self):
        reviewed = trial(**{"Ticker":"DONE", "NCT ID":"NCT87654321",
                            "NCT source":"https://clinicaltrials.gov/study/NCT87654321",
                            "Score status":"100-POINT RESEARCH SCORE — UNCALIBRATED",
                            "Pre-readout research score /100":92.0})
        low = trial(**{"Ticker":"ABC","NCT ID":"NCT00000001",
                       "NCT source":"https://clinicaltrials.gov/study/NCT00000001",
                       "Phase 2 PRIMARY evidence count":0,
                       "Protocol check":"STALE"})
        found = scoring_review_queue([low,trial(),trial(),reviewed])
        self.assertEqual(len(found), 2)
        self.assertEqual(list(found[0]), list(COLUMNS))
        self.assertEqual(found[0]["Ticker"], "TRVI")
        self.assertIsNone(found[0]["Pre-readout research score /100"])
        self.assertIn("Issuer topline status",found[0]["Needed before clinical score"])
        self.assertGreater(found[0]["Review priority"],found[1]["Review priority"])

    def test_inactive_posted_and_wrong_provenance_excluded(self):
        for change in (
            {"Trial phase":"Phase 2"},
            {"Registry status":"COMPLETED"},
            {"Registry results posted":"2026-10-10"},
            {"NCT ID":"NCTINVALID"},
            {"Ticker":""},
            {"NCT source":"https://clinicaltrials.gov/study/NCT00000002"},
        ):
            self.assertEqual(scoring_review_queue([trial(**change)]), [],change)

    def test_unverified_inputs_stay_action_items(self):
        row=trial(**{"Registry check":"STALE","Protocol check":"NO TIMESTAMP",
                     "Company/program identity":"REVIEW", "Market cap state":"UNVERIFIED",
                     "Phase 2 PRIMARY evidence count":0})
        found=scoring_review_queue([row])[0]
        msg=found["Needed before clinical score"]
        for warning in ("protocol", "trial snapshot", "identity", "market cap",
                        "Phase 2 PRIMARY"):
            self.assertIn(warning,msg)
        self.assertIsNone(found["Pre-readout research score /100"])

    def test_no_synthetic_score_or_positive_conclusion(self):
        found=scoring_review_queue([trial()])[0]
        self.assertNotIn("ENTRY READY",str(found))
        self.assertNotIn("APPROVED",str(found))
        self.assertEqual(found["Score status"],"NOT SCORED — EVIDENCE INCOMPLETE")
        with self.assertRaises(ValueError):
            scoring_review_queue([trial()], limit=0)
        self.assertEqual(scoring_review_queue([]),[])


if __name__ == "__main__":
    unittest.main()
