"""Research GEM candidates must be visible without bypassing the two gates."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from gem_benchmark_checklist import (
    build_checklist_map, research_candidate_rows, program_key,
)
from gem_research_preview import research_preview

ROOT = Path(__file__).resolve().parents[1]


def master(ticker, nct=""):
    return {
        "Ticker": ticker, "Drug": ticker + " trial",
        "Exact Program / Event": ticker + "|EXACT_EVENT",
        "NCT ID": nct,
        "Phase 3 Verified": "PENDING — VERIFIED READOUT MISSING",
        "Second Financing Closed": "PENDING — SECOND CLOSE UNVERIFIED",
        "GEM Score /100": None, "_eligible": False,
    }


def csv_write(root, filename, values):
    with (root / filename).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=values[0])
        writer.writeheader()
        writer.writerows(values)


class GEMVisibleCandidates(unittest.TestCase):
    def test_four_example_programs_in_research_but_not_verified(self):
        tickers = ("NTLA", "AXSM", "CAPR", "CORT")
        rows = [master(t, "NCT01234567" if t in ("CAPR", "CORT", "AXSM") else "")
                for t in tickers]
        clinical = [{
            "event_key": t + "|EXACT_EVENT",
            "source_recheck_status": "POSTED_RESULTS_DISCOVERY_ONLY",
            "saved_phase3_status": "UNVERIFIED",
        } for t in ("AXSM", "CAPR", "CORT")]
        finance = [{
            "event_key": t + "|EXACT_EVENT",
            "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "first_sec_status": "VERIFIED" if t == "NTLA" else "REVIEW_REQUIRED",
            "second_sec_status": "VERIFIED" if t == "NTLA" else "REVIEW_REQUIRED",
        } for t in ("NTLA", "AXSM")]
        checks = build_checklist_map(rows, financing_rechecks=finance,
                                     clinical_rechecks=clinical)
        leads = research_candidate_rows(rows, checks, clinical_rechecks=clinical,
                                        financing_rechecks=finance)
        self.assertEqual({r["Ticker"] for r in leads}, set(tickers))
        self.assertEqual({r["Ticker"] for r in leads
                          if r["GEM research group"] == "Both research leads"}, {"AXSM"})
        self.assertEqual(next(x for x in leads if x["Ticker"] == "NTLA")
                         ["Fresh SEC transactions verified"], 2)
        for r in leads:
            self.assertEqual(r["Status"], "RESEARCH ONLY — NOT GEM ELIGIBLE")
            self.assertFalse(r["Phase 3 benchmark verified"])
            self.assertFalse(r["Second financing benchmark verified"])

    def test_known_phase1_2_study_excluded_from_phase3_candidate_umbrella(self):
        one = master("INO", "NCT04398433")
        c = [{"event_key": "INO|EXACT_EVENT",
              "source_recheck_status": "POSTED_RESULTS_DISCOVERY_ONLY",
              "saved_phase3_status": "PHASE_1_2_NOT_PHASE_3"}]
        checks = build_checklist_map([one], clinical_rechecks=c)
        self.assertFalse(checks[program_key(one)]["phase3_data"]["observed"])
        self.assertEqual(research_candidate_rows([one], checks, clinical_rechecks=c), [])

    def test_no_new_funding_inherited_from_similar_ticker(self):
        rows = [master("AXSM"), {**master("AXSM"), "Exact Program / Event": "AXSM|OTHER"}]
        financial = [{"event_key": "AXSM|EXACT_EVENT",
                      "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING"}]
        checks = build_checklist_map(rows, financing_rechecks=financial)
        leads = research_candidate_rows(rows, checks, financing_rechecks=financial)
        self.assertEqual([r["Exact Program / Event"] for r in leads], ["AXSM|EXACT_EVENT"])

    def test_preview_independent_of_entry_eligible_filter(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            csv_write(root, "pdufa_candidates.csv", [
                {"event_key": t+"|EXACT_EVENT", "ticker": t}
                for t in ("NTLA", "AXSM", "CAPR", "CORT")
            ])
            csv_write(root, "gem_phase3_exact_recheck.csv", [
                {"event_key": t+"|EXACT_EVENT",
                 "source_recheck_status": "POSTED_RESULTS_DISCOVERY_ONLY",
                 "saved_phase3_status": "UNVERIFIED"}
                for t in ("AXSM", "CAPR", "CORT")
            ])
            csv_write(root, "gem_two_close_recheck.csv", [
                {"event_key": t+"|EXACT_EVENT",
                 "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                 "first_sec_status": "VERIFIED",
                 "second_sec_status": "VERIFIED"}
                for t in ("NTLA", "AXSM")
            ])
            groups = research_preview(root)
            self.assertEqual(groups["Both source leads"], ["AXSM"])
            self.assertEqual(groups["Financing source lead"], ["NTLA"])
            self.assertEqual(groups["Phase 3 source lead"], ["CAPR", "CORT"])

    def test_default_ui_research_lead_views_remain_separate(self):
        nested = (ROOT / "gem_nested_master_ui.py").read_text(encoding="utf-8")
        scan = (ROOT / "gem_scans_ui.py").read_text(encoding="utf-8")
        overview = (ROOT / "unified_clinical_trading.py").read_text(encoding="utf-8")
        self.assertIn('"Research candidates (source leads)", "All candidates"', nested)
        self.assertIn('"Research candidates (source leads)", "All GEM programs"', scan)
        self.assertIn('render_research_candidates(', nested)
        self.assertIn('render_research_candidates(', scan)
        self.assertIn('render_gem_potential(root=root, compact=True', overview)
        self.assertIn('Entry-eligible only', nested)
        self.assertIn('Entry-eligible only', scan)


if __name__ == "__main__":
    unittest.main()
