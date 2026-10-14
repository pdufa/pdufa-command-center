"""GEM source-research picker regression for verified + pending list indexing.

A verified GEM can appear before the potential research list. The Streamlit
format_func must use the exact same universe as its index options.
"""
import unittest
from pathlib import Path

from gem_potential_ui import research_program_label


ROOT = Path(__file__).resolve().parents[1]


class GEMPotentialPickerRegressionTests(unittest.TestCase):
    @staticmethod
    def verified(ticker, drug, event, nct):
        return {"Ticker": ticker, "Drug": drug, "Exact program": event,
                "NCT ID": nct, "Phase 3 Verified": True}

    def test_three_verified_gems_and_only_one_pending_lead(self):
        verified = [
            self.verified("NTLA", "lonvoguran ziclumeran", "NTLA|HAE", "NCT06634420"),
            self.verified("ZBIO", "obexelimab", "ZBIO|IGG4", "NCT05662241"),
            self.verified("PRAX", "ulixacaltamide", "PRAX|ET", "NCT06087276"),
        ]
        potential = [{"Ticker": "AXSM", "Drug": "AXS-12",
                      "Exact program": "AXSM|NARCOLEPSY", "NCT ID": ""}]
        research_universe = verified + potential
        labels = [research_program_label(research_universe[n])
                  for n in range(len(research_universe))]
        self.assertEqual(len(labels), 4)
        self.assertEqual(labels[0], "NTLA · lonvoguran ziclumeran · NCT06634420")
        self.assertEqual(labels[2], "PRAX · ulixacaltamide · NCT06087276")
        self.assertEqual(labels[3], "AXSM · AXS-12 · AXSM|NARCOLEPSY")
        self.assertEqual(len(set(labels)), 4)

    def test_zero_potential_leads_with_multiple_source_cleared(self):
        research_universe = [
            self.verified("NTLA", "lonvo", "NTLA|HAE", "NCT06634420"),
            self.verified("ZBIO", "obexelimab", "ZBIO|IGG4", "NCT05662241"),
        ]
        self.assertEqual(
            [research_program_label(research_universe[n])
             for n in range(len(research_universe))],
            ["NTLA · lonvo · NCT06634420",
             "ZBIO · obexelimab · NCT05662241"],
        )

    def test_only_potential_leads_and_missing_fields(self):
        potential = [{"Ticker": "AXSM", "Drug": "AXS-12",
                      "Exact program": "AXSM|NARCOLEPSY"},
                     {"Ticker": "CAPR", "Drug": "deramiocel",
                      "NCT ID": "NCT03406780"}]
        self.assertEqual([research_program_label(x) for x in potential],
                         ["AXSM · AXS-12 · AXSM|NARCOLEPSY",
                          "CAPR · deramiocel · NCT03406780"])
        self.assertEqual(research_program_label({}), "? · ? · ")

    def test_real_streamlit_selectbox_options_reference_combined_universe(self):
        ui = (ROOT / "gem_potential_ui.py").read_text(encoding="utf-8")
        area = ui[ui.index("    research_universe = source_cleared + potential"):
                  ui.index("            lead = research_universe[choice]")]
        self.assertIn("identifiers = list(range(len(research_universe)))", area)
        self.assertIn("research_program_label(research_universe[n])", area)
        self.assertNotIn("potential[n]", area)


if __name__ == "__main__":
    unittest.main()
