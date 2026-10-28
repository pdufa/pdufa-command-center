import unittest
from app.phase3_deep_analysis_orchestrator import prepare_deep_analysis

def verified(day, target=None):
    x={"review_status":"VERIFIED","source_url":"https://example.org/primary",
       "published_at":day,"event_date":day}
    if target is not None: x["pdufa_target_date"]=target
    return x

class DeepAnalysisOrchestratorTests(unittest.TestCase):
    def run_case(self, phase3=None, pdufa=None):
        return prepare_deep_analysis(
            exact_key="NCT-TEST", phase3_results=phase3 or {},
            pdufa_assignment=pdufa or {}, scientific_evidence={},
            as_of="2026-10-27")
    def test_no_phase3_blocks_all(self):
        r=self.run_case(pdufa=verified("2026-10-01","2027-06-01"))
        self.assertEqual(r["status"],"BLOCKED")
        self.assertIsNone(r["science"])
        self.assertIsNone(r["outcome"])
        self.assertIsNone(r["main"])
    def test_no_pdufa_blocks_all(self):
        self.assertEqual(self.run_case(phase3=verified("2026-09-01"))["status"],"BLOCKED")
    def test_both_verified_starts_research_not_prediction(self):
        r=self.run_case(verified("2026-09-01"),verified("2026-10-01","2027-06-01"))
        self.assertEqual(r["status"],"RESEARCH_IN_PROGRESS")
        self.assertEqual(r["science"]["reviewed"],0)
        self.assertIsNone(r["approvalProbability"])
        self.assertFalse(r["tradeAuthorized"])
    def test_no_early_work_with_malformed_scientific_evidence(self):
        r=prepare_deep_analysis(exact_key="X",phase3_results={},
            pdufa_assignment={},scientific_evidence=None,as_of="2026-10-27")
        self.assertEqual(r["status"],"BLOCKED")

if __name__=="__main__":
    unittest.main()
