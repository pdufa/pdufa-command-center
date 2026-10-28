import unittest
from app.phase3_research_batch import evaluate_candidate_batch

def ev(day, target=None):
    x={"review_status":"VERIFIED","source_url":"https://example.org/record",
       "published_at":day,"event_date":day}
    if target: x["pdufa_target_date"]=target
    return x

class BatchTests(unittest.TestCase):
    def test_mixed_candidates(self):
        rows=[{"exact_key":"A","list_memberships":["Pipeline"]},
              {"exact_key":"B","list_memberships":["GEM JR"],
               "phase3_results":ev("2026-08-01"),
               "pdufa_assignment":ev("2026-09-01","2027-04-01")}]
        r=evaluate_candidate_batch(rows,as_of="2026-10-27")
        self.assertEqual(r["totalDiscovered"],2)
        self.assertEqual(r["eligibleForResearch"],1)
        self.assertEqual(r["blockedFromResearch"],1)
        self.assertEqual(r["sheetPopulationStatus"],"NOT_WRITTEN")
        self.assertFalse(r["tradeAuthorized"])
    def test_duplicate_identity_fails(self):
        with self.assertRaises(ValueError):
            evaluate_candidate_batch([{"exact_key":"A"},{"exact_key":"A"}],as_of="2026-10-27")
    def test_limit(self):
        with self.assertRaises(ValueError):
            evaluate_candidate_batch([{"exact_key":str(i)} for i in range(201)],as_of="2026-10-27")
    def test_sheet_preview_only_includes_verified_candidates(self):
        from app.phase3_sheet_population_preview import build_sheet_population_preview
        rows=[{"exact_key":"A","list_memberships":["Pipeline"]},
              {"exact_key":"B","list_memberships":["GEM JR"],
               "phase3_results":ev("2026-08-01"),
               "pdufa_assignment":ev("2026-09-01","2027-04-01")}]
        batch=evaluate_candidate_batch(rows,as_of="2026-10-27")
        preview=build_sheet_population_preview(batch)
        self.assertEqual(preview["mode"],"PREVIEW_ONLY")
        self.assertFalse(preview["writtenToSheet"])
        self.assertEqual(len(preview["rows"]),1)
        self.assertEqual(preview["rows"][0]["trialExactKey"],"B")
        self.assertIsNone(preview["rows"][0]["approvalProbability"])

    def test_empty_batch(self):
        self.assertEqual(evaluate_candidate_batch([],as_of="2026-10-27")["totalDiscovered"],0)

if __name__=="__main__":
    unittest.main()
