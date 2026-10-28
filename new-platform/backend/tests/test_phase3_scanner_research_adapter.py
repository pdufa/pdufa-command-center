import unittest
from app.phase3_scanner_research_adapter import route_scanned_candidate

def event(day, target=None):
    e={"review_status":"VERIFIED","source_url":"https://example.org/fda",
       "published_at":day,"event_date":day}
    if target: e["pdufa_target_date"]=target
    return e

class ScannerResearchAdapterTests(unittest.TestCase):
    def route(self, candidate):
        return route_scanned_candidate(candidate, as_of="2026-10-27")
    def test_discovery_kept_without_gate(self):
        r=self.route({"exact_key":"NCT-A","list_memberships":["Pipeline","GEM JR"]})
        self.assertTrue(r["discoveryVisible"])
        self.assertEqual(r["listMemberships"],["Pipeline","GEM JR"])
        self.assertFalse(r["deepAnalysisEligible"])
        self.assertIsNone(r["analysis"])
    def test_only_phase3_not_enough(self):
        r=self.route({"exact_key":"NCT-B","phase3_results":event("2026-09-01")})
        self.assertEqual(r["deepAnalysisStatus"],"BLOCKED")
    def test_both_start_science_without_trade(self):
        r=self.route({"exact_key":"NCT-C","list_memberships":["GEM"],
                      "phase3_results":event("2026-09-01"),
                      "pdufa_assignment":event("2026-10-01","2027-05-01")})
        self.assertTrue(r["deepAnalysisEligible"])
        self.assertIsNotNone(r["analysis"]["science"])
        self.assertFalse(r["tradeAuthorized"])
    def test_invalid_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.route({"list_memberships":["Pipeline"]})

if __name__=="__main__":
    unittest.main()
