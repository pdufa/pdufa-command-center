import unittest
from app.phase3_pdufa_eligibility import phase3_pdufa_eligibility

def event(day="2026-09-01", target=None):
    x={"review_status":"VERIFIED","source_url":"https://example.org/source",
       "published_at":day,"event_date":day}
    if target: x["pdufa_target_date"]=target
    return x

class EligibilityTests(unittest.TestCase):
    def gate(self,p=None,d=None,as_of="2026-10-27"):
        return phase3_pdufa_eligibility(exact_key="TRIAL-1",phase3_results=p or {},
                 pdufa_assignment=d or {},as_of=as_of)
    def test_both_required(self):
        self.assertFalse(self.gate(p=event())["deepAnalysisEligible"])
        self.assertFalse(self.gate(d=event(target="2027-05-01"))["deepAnalysisEligible"])
    def test_verified_both(self):
        x=self.gate(p=event(),d=event("2026-10-01","2027-05-01"))
        self.assertTrue(x["deepAnalysisEligible"])
        self.assertFalse(x["tradeAuthorized"])
    def test_future_release_blocks(self):
        self.assertFalse(self.gate(p=event("2026-11-01"),d=event(target="2027-05-01"))["deepAnalysisEligible"])
    def test_unverified_source_blocks(self):
        p=event();p["review_status"]="PENDING"
        self.assertFalse(self.gate(p=p,d=event(target="2027-05-01"))["deepAnalysisEligible"])
    def test_pdufa_date_not_yet_announced(self):
        self.assertFalse(self.gate(p=event(),d=event("2026-11-01","2027-05-01"))["deepAnalysisEligible"])
    def test_future_target_allowed(self):
        self.assertEqual(self.gate(p=event(),d=event(target="2028-01-01"))["pdufaTargetDate"],"2028-01-01")

if __name__=="__main__":
    unittest.main()
