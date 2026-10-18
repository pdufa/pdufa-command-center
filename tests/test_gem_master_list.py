"""One GEM stock list, preserving every exact program and the two event gates."""
from pathlib import Path
import unittest
from gem_master_list import MASTER_COLUMNS, build_gem_master_list, gem_stage, gem_status

ROOT = Path(__file__).resolve().parents[1]


def row(ticker, *, phase3=False, closed=False, eligible=False,
        days=None, verified_date=False, score=None, rank=None):
    return {
        "Ticker": ticker, "Drug": "Drug " + ticker,
        "Indication": "Rare disease", "Exact event": ticker + "|DRUG_NCT",
        "Benchmark 1 — Phase 3 released": (
            "PASS — VERIFIED RESULTS RELEASE" if phase3 else "PENDING — VERIFIED READOUT MISSING"),
        "Benchmark 2 — Financing #2 closed": (
            "PASS — TWO POST-READOUT CLOSES" if closed else "PENDING — SECOND CLOSE UNVERIFIED"),
        "Two-benchmark eligible": eligible,
        "Two-benchmark rank": rank,
        "Two-benchmark priority /100": score,
        "Days to PDUFA": days,
        "PDUFA verification": (
            "VERIFIED — SOURCE LINKED" if verified_date else "REVIEW"),
        "Hedge-fund source links": "https://sec.gov/hedge",
        "Phase 3 source": "https://issuer.example/readout",
    }


class GemMasterListTests(unittest.TestCase):
    def test_all_programs_in_one_ranked_list_without_loss(self):
        items = [
            row("A", phase3=True, days=120),
            row("B", phase3=True, closed=True, eligible=True,
                verified_date=True, days=75, score=89, rank=2),
            row("C"),
            row("D", phase3=True, closed=True, eligible=True,
                days=110, verified_date=True, score=95, rank=1),
        ]
        result = build_gem_master_list(items)
        self.assertEqual([r["Ticker"] for r in result], ["D", "B", "A", "C"])
        self.assertEqual([r["GEM Stage"] for r in result],
                         ["Post-Financing", "PDUFA", "Phase 3",
                          "Research / Unverified"])
        self.assertEqual(result[0]["GEM Rank"], 1)
        self.assertEqual(result[1]["GEM Score /100"], 89)
        self.assertEqual(result[2]["GEM Rank"], None)
        self.assertEqual(result[2]["GEM Score /100"], None)
        self.assertEqual(result[2]["Phase 3 Source"], "https://issuer.example/readout")
        self.assertEqual(len(result), len(items))
        self.assertEqual(set(MASTER_COLUMNS), set(result[0]) - {"_eligible"})

    def test_pdufa_stage_does_not_promote_unverified_stock(self):
        item = row("PENDING", days=30, verified_date=True, phase3=True)
        item["Two-benchmark rank"] = 17
        item["Two-benchmark priority /100"] = 99
        result = build_gem_master_list([item])[0]
        self.assertEqual(result["GEM Stage"], "PDUFA")
        self.assertEqual(result["GEM Status"], "PHASE 3 VERIFIED — REVIEW FINANCING RISK (OPTIONAL)")
        self.assertFalse(result["_eligible"])
        self.assertIsNone(result["GEM Rank"])
        self.assertIsNone(result["GEM Score /100"])

    def test_exit_warning_does_not_delete_a_verifiable_program(self):
        record = row("EXIT", phase3=True, closed=True, eligible=True,
                     verified_date=True, days=2, score=85, rank=3)
        r = build_gem_master_list([record])[0]
        self.assertEqual(r["GEM Status"], "EXIT / FDA DECISION WARNING")
        self.assertTrue(r["_eligible"])
        self.assertEqual(r["GEM Rank"], 3)

    def test_unverified_pdufa_dates_do_not_get_false_pdufa_stage(self):
        record = row("NEW", phase3=True, closed=True, eligible=True,
                     days=50, verified_date=False, rank=1, score=70)
        self.assertEqual(gem_stage(record), "Post-Financing")
        self.assertEqual(gem_status(record), "PHASE 3 QUALIFIED — RANKED; MANUAL REVIEW")

    def test_ui_has_single_stock_table_and_full_export(self):
        code = (ROOT / "gem_scans_ui.py").read_text(encoding="utf-8")
        self.assertIn("### GEM — UNIFIED MASTER LIST", code)
        self.assertIn("EXPORT GEM MASTER LIST", code)
        self.assertIn("build_gem_master_list(items)", code)
        self.assertIn("st.dataframe(master_table, use_container_width=True", code)
        self.assertIn("master_table.to_csv(index=False)", code)
        self.assertNotIn("st.tabs(list(STAGES))", code)
        self.assertNotIn("_gems_table", code)
        self.assertNotIn("EXPORT RANKED TWO-BENCHMARK CANDIDATES", code)
        self.assertNotIn("EARLY GEM WATCH — VERIFIED PHASE 3", code)
        self.assertNotIn("EXPORT OPTIONAL CONSERVATIVE RESEARCH SUBSET", code)


if __name__ == "__main__":
    unittest.main()
