"""Both GEM stage checklists show every existing criterion once, unchanged."""
import unittest

from gem_730_requirement_scan import (
    CRITERIA, TRADING_CRITERIA, TRIAL_CRITERIA, TRADING_CRITERION_KEYS, scan
)
from gem_benchmark_checklist import (
    ADVISORIES, RESEARCH_ADVISORIES, TRADING_ADVISORIES,
    TRADING_ADVISORY_KEYS, BENCHMARKS, UMBRELLA, filter_programs
)


class TradingSectionTests(unittest.TestCase):
    def test_scan_criteria_partition_is_exact_and_disjoint(self):
        self.assertFalse(set(TRADING_CRITERIA) & set(TRIAL_CRITERIA))
        self.assertEqual(set(TRADING_CRITERIA) | set(TRIAL_CRITERIA),
                         set(CRITERIA))
        self.assertEqual(set(TRADING_CRITERIA),set(TRADING_CRITERION_KEYS))
        self.assertIn("phase3_verified", TRIAL_CRITERIA)
        self.assertIn("pdufa_source", TRIAL_CRITERIA)
        self.assertIn("price_base", TRADING_CRITERIA)
        self.assertIn("market_quote", TRADING_CRITERIA)

    def test_combined_scan_matches_ungrouped_selection(self):
        rows=[
            {"status":"COMPLETED"},
            {"status":"RECRUITING"},
            {"status":"TERMINATED"},
        ]
        chosen=["phase3_active_or_completed","price_base","market_quote"]
        expected=scan(rows,chosen)
        grouped=scan(rows,
                     [x for x in TRIAL_CRITERIA if x in chosen]+
                     [x for x in TRADING_CRITERIA if x in chosen])
        self.assertEqual(expected,grouped)
        self.assertEqual(len(grouped[0]),0)  # unverifiable trading evidence

    def test_advisory_partition_is_exact_and_preserves_keys(self):
        all_keys=[k for k,_ in ADVISORIES]
        split=[k for k,_ in RESEARCH_ADVISORIES+TRADING_ADVISORIES]
        self.assertEqual(set(all_keys),set(split))
        self.assertEqual(len(split),len(set(split)))
        self.assertEqual({k for k,_ in TRADING_ADVISORIES},
                         set(TRADING_ADVISORY_KEYS))
        self.assertIn("clinical_quality",dict(RESEARCH_ADVISORIES))
        self.assertIn("price_base",dict(TRADING_ADVISORIES))
        self.assertIn("pdufa_window",dict(TRADING_ADVISORIES))

    def test_advisories_remain_optional_view_filters(self):
        rows=[{"Ticker":"TEST","NCT ID":"NCT00000001",
               "Exact Program / Event":"TEST|DRUG"},
              {"Ticker":"ABC","NCT ID":"NCT00000002",
               "Exact Program / Event":"ABC|DRUG"}]
        checks={
            "EVENT|TEST|DRUG":{"phase3_verified":{"checked":True},
                              "price_base":{"checked":True},
                              "dilution":{"checked":True}},
            "EVENT|ABC|DRUG":{"phase3_verified":{"checked":True},
                             "price_base":{"checked":False},
                             "dilution":{"checked":True}}}
        original=filter_programs(rows,checks,["phase3_verified","price_base","dilution"])
        split_selected=["phase3_verified","dilution","price_base"]
        self.assertEqual(original,filter_programs(rows,checks,split_selected))
        self.assertEqual(len(original),1)


if __name__ == "__main__":
    unittest.main()
