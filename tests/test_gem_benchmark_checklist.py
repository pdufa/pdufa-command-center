"""GEM umbrella and checkbox filters must never become new entry gates."""
from __future__ import annotations

import unittest
from pathlib import Path

from gem_benchmark_checklist import (
    ADVISORIES, BENCHMARKS, UMBRELLA,
    build_checklist, build_checklist_map, filter_programs, program_key,
)

ROOT = Path(__file__).resolve().parents[1]


def row(ticker, phase3=False, financed=False, eligible=False):
    return {
        "Ticker": ticker, "Drug": ticker + " program",
        "Exact Program / Event": ticker + "|EXACT_DRUG",
        "Phase 3 Verified": ("PASS — VERIFIED RESULTS RELEASE" if phase3 else
                             "PENDING — VERIFIED READOUT MISSING"),
        "Second Financing Closed": ("PASS — TWO POST-READOUT CLOSES" if financed else
                                    "PENDING — SECOND CLOSE UNVERIFIED"),
        "_eligible": eligible,
        "GEM Score /100": 80 if eligible else None,
        "GEM Rank": 1 if eligible else None,
    }


def item(ticker):
    return {"Exact event": ticker + "|EXACT_DRUG",
            "Phase 3 evidence": "REGISTRY RESULTS POSTED — REVIEW",
            "Market activity /10": 0,
            "Trading setup /20": 0,
            "GEM financing dilution flag": "UNKNOWN",
            "GEM clinical conflict flag": "UNKNOWN",
            "Cash runway (months)": None}


class UmbrellaCheckboxTests(unittest.TestCase):
    def test_only_two_positive_entry_benchmarks(self):
        self.assertEqual(len(BENCHMARKS), 2)
        self.assertEqual(len(UMBRELLA), 2)
        self.assertGreater(len(ADVISORIES), 8)
        master = row("AAA", phase3=True, financed=True, eligible=True)
        states = build_checklist(master, item("AAA"), feed_current=False,
                                 sec_current=False)
        self.assertTrue(states["phase3_verified"]["checked"])
        self.assertTrue(states["financing_verified"]["checked"])
        self.assertFalse(states["sec_fresh"]["checked"])
        self.assertFalse(states["clinical_fresh"]["checked"])
        self.assertEqual(master["GEM Rank"], 1)

    def test_registry_posting_is_umbrella_lead_not_verified_phase3(self):
        master = row("AAA")
        states = build_checklist(master, item("AAA"),
                                 clinical_audit={"source_recheck_status":
                                                 "POSTED_RESULTS_DISCOVERY_ONLY"})
        self.assertTrue(states["phase3_data"]["observed"])
        self.assertFalse(states["phase3_data"]["checked"])
        self.assertFalse(states["phase3_verified"]["checked"])
        self.assertFalse(master["_eligible"])

    def test_stale_historical_financing_is_lead_not_confirmed_gate(self):
        master = row("BBB")
        states = build_checklist(master, item("BBB"), finance_audit={
            "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "recheck_status": "SEC_TRANSACTION_EVIDENCE_INCOMPLETE",
        })
        self.assertFalse(states["financing_verified"]["checked"])
        self.assertTrue(states["financing_lead"]["observed"])
        self.assertFalse(master["_eligible"])

    def test_optional_filter_never_changes_rank_or_eligibility(self):
        a = row("AAA", phase3=True, financed=True, eligible=True)
        b = row("BBB")
        source = [item("AAA"), item("BBB")]
        a["GEM Rank"] = 1
        states = build_checklist_map([a, b], source, feed_current=False)
        filtered = filter_programs([a, b], states, ["sec_fresh"])
        self.assertEqual(filtered, [])
        self.assertEqual(a["GEM Rank"], 1)
        self.assertTrue(a["_eligible"])
        self.assertEqual(len(filter_programs([a, b], states)), 2)

    def test_source_observed_filter_includes_unverified_but_not_as_verified(self):
        a, b = row("AAA"), row("BBB")
        source = [item("AAA"), {"Exact event": "BBB|EXACT_DRUG"}]
        states = build_checklist_map([a, b], source)
        found = filter_programs([a, b], states, ["phase3_data"])
        self.assertEqual([r["Ticker"] for r in found], ["AAA"])
        self.assertEqual(filter_programs([a, b], states, ["phase3_verified"]), [])

    def test_unlinked_or_duplicated_exact_event_cannot_borrow_source(self):
        a, b = row("AAA"), row("BBB")
        duplicate = [item("AAA"), item("AAA")]
        states = build_checklist_map([a, b], duplicate)
        self.assertFalse(states[program_key(a)]["phase3_data"]["observed"])
        self.assertFalse(states[program_key(b)]["phase3_data"]["observed"])

    def test_phase3_registry_umbrella_handles_unique_ticker_nct_without_event(self):
        unlinked = row("TRIAL")
        unlinked["Exact Program / Event"] = ""
        unlinked["NCT ID"] = "NCT01234567"
        source = {"Ticker": "TRIAL", "Exact event": "", "NCT ID": "NCT01234567",
                  "Phase 3 evidence": "REGISTRY RESULTS POSTED — REVIEW"}
        states = build_checklist_map([unlinked], [source])
        matching = filter_programs([unlinked], states, ["phase3_data"])
        self.assertEqual(matching, [unlinked])
        self.assertEqual(filter_programs([unlinked], states, ["phase3_verified"]), [])
        self.assertFalse(unlinked["_eligible"])

    def test_ambiguous_same_ticker_nct_never_borrows_issuer_clinical_evidence(self):
        unlinked = row("TRIAL")
        unlinked["Exact Program / Event"] = ""
        unlinked["NCT ID"] = "NCT01234567"
        source = {"Ticker": "TRIAL", "Exact event": "", "NCT ID": "NCT01234567",
                  "Phase 3 evidence": "REGISTRY RESULTS POSTED — REVIEW"}
        states = build_checklist_map([unlinked], [source, source])
        self.assertEqual(filter_programs([unlinked], states, ["phase3_data"]), [])
        self.assertEqual(filter_programs([unlinked], states), [unlinked])

    def test_checkbox_ui_is_visible_in_both_gem_surfaces(self):
        nested = (ROOT / "gem_nested_master_ui.py").read_text(encoding="utf-8")
        scan = (ROOT / "gem_scans_ui.py").read_text(encoding="utf-8")
        ui = (ROOT / "gem_checklist_ui.py").read_text(encoding="utf-8")
        self.assertIn("stock_checkboxes(", nested)
        self.assertIn("checklist_filters(", nested)
        self.assertIn("checklist_filters(", scan)
        self.assertIn("render_checkbox_table(", scan)
        self.assertIn("st.checkbox(", ui)
        self.assertIn("disabled=True", ui)
        self.assertIn("FILTER the", ui)


if __name__ == "__main__":
    unittest.main()
