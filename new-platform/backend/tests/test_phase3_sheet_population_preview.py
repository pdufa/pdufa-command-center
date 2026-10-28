import unittest
from app.phase3_sheet_population_preview import build_sheet_population_preview
class SheetPreviewTests(unittest.TestCase):
    def test_blocked_excluded(self):
        x=build_sheet_population_preview({"rows":[{"exactKey":"X","deepAnalysisEligible":False,"analysis":None}]})
        self.assertEqual(x["rows"],[])
        self.assertFalse(x["writtenToSheet"])
    def test_unverified_gate_cannot_be_bypassed(self):
        x=build_sheet_population_preview({"rows":[{"exactKey":"X","deepAnalysisEligible":True,"analysis":{"gate":{"deepAnalysisEligible":False}}}]})
        self.assertEqual(x["rows"],[])
    def test_invalid_batch(self):
        with self.assertRaises(ValueError): build_sheet_population_preview({})
if __name__=="__main__": unittest.main()
