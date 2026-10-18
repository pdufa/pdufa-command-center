"""Potential GEM watchlist is source-grounded, visible, and research-only."""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_potential_list import build_potential_list


def write(root, name, rows):
    with (root / name).open("w", encoding="utf-8", newline="") as file:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class PotentialGEMTests(unittest.TestCase):
    def fixture(self, root):
        events = [
            {"event_key": "NTLA|HAE", "ticker": "NTLA", "drug": "lonvo-z",
             "pdufa_date": "2027-03-10", "phase3_status": "UNVERIFIED"},
            {"event_key": "AXSM|AXS12", "ticker": "AXSM", "drug": "AXS-12",
             "pdufa_date": "2027-05-01", "phase3_status": "UNVERIFIED"},
            {"event_key": "CAPR|DMD", "ticker": "CAPR", "drug": "deramiocel",
             "pdufa_date": "2026-11-22", "phase3_status": "UNVERIFIED"},
            {"event_key": "CORT|CUSHINGS", "ticker": "CORT", "drug": "relacorilant",
             "pdufa_date": "2026-12-17", "phase3_status": "UNVERIFIED"},
            {"event_key": "IRD|PRESBYOPIA", "ticker": "IRD", "drug": "phentolamine",
             "pdufa_date": "2026-10-17", "phase3_status": "RESULTS_REVIEW",
             "phase3_date": "2025-06-26",
             "trial_evidence_url": "https://www.sec.gov/Archives/readout"},
            {"event_key": "INO|RRP", "ticker": "INO", "drug": "INO-3107",
             "pdufa_date": "2026-10-30", "phase3_status": "PHASE_1_2_NOT_PHASE_3"},
            {"event_key": "FIN|RESOLVED", "ticker": "FIN", "drug": "older",
             "pdufa_date": "2026-12-02", "phase3_status": "UNVERIFIED",
             "outcome": "APPROVED"},
        ]
        clinical = [
            {"event_key": "AXSM|AXS12", "source_recheck_status":
             "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT03881852",
             "saved_phase3_status": "UNVERIFIED"},
            {"event_key": "CAPR|DMD", "source_recheck_status":
             "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT03406780",
             "saved_phase3_status": "UNVERIFIED"},
            {"event_key": "CORT|CUSHINGS", "source_recheck_status":
             "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT04308590",
             "saved_phase3_status": "UNVERIFIED"},
            {"event_key": "INO|RRP", "source_recheck_status":
             "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT04398433",
             "saved_phase3_status": "PHASE_1_2_NOT_PHASE_3"},
        ]
        financing = [
            {"event_key": "NTLA|HAE",
             "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_sec_status": "VERIFIED", "second_sec_status": "VERIFIED"},
            {"event_key": "AXSM|AXS12",
             "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_sec_status": "REVIEW_REQUIRED", "second_sec_status": "REVIEW_REQUIRED"},
            {"event_key": "IRD|PRESBYOPIA",
             "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_sec_status": "VERIFIED", "second_sec_status": "VERIFIED"},
            {"event_key": "FIN|RESOLVED",
             "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_sec_status": "VERIFIED", "second_sec_status": "VERIFIED"},
        ]
        write(root, "pdufa_candidates.csv", events)
        write(root, "gem_phase3_exact_recheck.csv", clinical)
        write(root, "gem_two_close_recheck.csv", financing)

    def test_potential_reason_and_verification_gap_for_each_program(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            pending, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertEqual({x["Ticker"] for x in pending},
                             {"NTLA", "AXSM", "CAPR", "CORT", "IRD"})
            self.assertEqual({x["Ticker"] for x in held}, {"FIN"})
            ntla = next(x for x in pending if x["Ticker"] == "NTLA")
            self.assertIn("both cited SEC documents rechecked", ntla["Why potential"])
            self.assertIn("Phase 3 results", ntla["Still needed"])
            self.assertEqual(ntla["GEM status"], "POTENTIAL — RESEARCH ONLY / NOT QUALIFIED")
            axsm = next(x for x in pending if x["Ticker"] == "AXSM")
            self.assertIn("NCT03881852", axsm["Why potential"])
            self.assertIn("0/2 SEC documents", axsm["Why potential"])
            capr = next(x for x in pending if x["Ticker"] == "CAPR")
            self.assertIn("NCT03406780", capr["Why potential"])
            self.assertIn("two distinct", capr["Still needed"])
            self.assertNotIn("INO", {x["Ticker"] for x in pending + held})
            self.assertIn("NO NEW ENTRY", next(x for x in pending if x["Ticker"] == "IRD")
                          ["Timing / resolution"])
            self.assertIn("APPROVED", next(x for x in held if x["Ticker"] == "FIN")
                          ["Timing / resolution"])

    def test_pdufa_three_day_warning_keeps_candidate_until_actual_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            # IRD has saved PDUFA 2026-10-17.
            before, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertIn("IRD", {x["Ticker"] for x in before})
            self.assertNotIn("IRD", {x["Ticker"] for x in held})
            on_day, held_on_day = build_potential_list(root, as_of=date(2026, 10, 17))
            self.assertIn("IRD", {x["Ticker"] for x in on_day})
            self.assertNotIn("IRD", {x["Ticker"] for x in held_on_day})
            expired, held_expired = build_potential_list(root, as_of=date(2026, 10, 18))
            self.assertNotIn("IRD", {x["Ticker"] for x in expired})
            self.assertIn("PDUFA date expired",
                          next(x for x in held_expired if x["Ticker"] == "IRD")
                          ["Timing / resolution"])

    def test_duplicate_exact_event_does_not_borrow_financing_or_study(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            rows = [{"event_key": "AXSM|AXS12", "source_recheck_status":
                     "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT03881852"}]
            write(root, "gem_phase3_exact_recheck.csv", rows + rows)
            pending, _ = build_potential_list(root, as_of=date(2026, 10, 14))
            axsm = next(x for x in pending if x["Ticker"] == "AXSM")
            self.assertNotIn("NCT03881852", axsm["Why potential"])
            self.assertIn("Historical two-close", axsm["Why potential"])

    def test_same_ticker_two_programs_preserve_distinct_reasons(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            ev = [
                {"event_key": "AXSM|ONE", "ticker": "AXSM", "drug": "program one",
                 "pdufa_date": "2027-01-01", "phase3_status": "UNVERIFIED"},
                {"event_key": "AXSM|TWO", "ticker": "AXSM", "drug": "program two",
                 "pdufa_date": "2027-04-02", "phase3_status": "UNVERIFIED"},
            ]
            write(root, "pdufa_candidates.csv", ev)
            write(root, "gem_phase3_exact_recheck.csv", [
                {"event_key": "AXSM|ONE", "source_recheck_status":
                 "POSTED_RESULTS_DISCOVERY_ONLY", "nct_results_posted": "NCT11112222"}])
            write(root, "gem_two_close_recheck.csv", [
                {"event_key": "AXSM|TWO",
                 "historical_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                 "first_sec_status": "VERIFIED", "second_sec_status": "REVIEW_REQUIRED"}])
            pending, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertFalse(held)
            self.assertEqual(len(pending), 2)
            self.assertNotEqual(pending[0]["Evidence type"], pending[1]["Evidence type"])
            self.assertFalse(any(r["Evidence type"] == "Phase 3 + financing" for r in pending))

    def test_independent_post_phase3_issuer_leads_are_separate_pending_stocks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            write(root, "post_phase3_discoveries.csv", [
                {"ticker": "CLDX", "drug": "barzolvolimab",
                 "indication": "chronic spontaneous urticaria",
                 "nct_id": "NCT06445023", "readout_date": "2026-09-22",
                 "source_url": "https://issuer.example/csuevidence"},
                {"ticker": "CLDX", "drug": "barzolvolimab",
                 "indication": "chronic spontaneous urticaria",
                 "nct_id": "NCT06455202", "readout_date": "2026-09-22",
                 "source_url": "https://issuer.example/csuevidence"},
                {"ticker": "MLTX", "drug": "sonelokimab",
                 "indication": "psoriatic arthritis", "nct_id": "NCT06641076",
                 "readout_date": "2026-08-10",
                 "source_url": "https://issuer.example/izar"},
            ])
            # Independent issuer leads must FIRST exist as exact Pipeline trials.
            write(root, "phase_pipeline.csv", [
                {"ticker": "CLDX", "nct_id": "NCT06445023", "phase": "PHASE3"},
                {"ticker": "CLDX", "nct_id": "NCT06455202", "phase": "PHASE3"},
                {"ticker": "MLTX", "nct_id": "NCT06641076", "phase": "PHASE3"},
            ])
            pending, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertEqual(sum(x["Ticker"] == "CLDX" for x in pending), 2)
            self.assertEqual(sum(x["Ticker"] == "MLTX" for x in pending), 1)
            self.assertTrue(all("not GEM-verified" in x["Why potential"]
                                for x in pending if x["Ticker"] in ("CLDX", "MLTX")))
            self.assertTrue(all("two separate post-readout" in x["Still needed"]
                                for x in pending if x["Ticker"] in ("CLDX", "MLTX")))
            self.assertFalse(any(x["Ticker"] in ("CLDX", "MLTX") for x in held))

    def test_independent_lead_cannot_borrow_financing_from_same_ticker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            write(root, "post_phase3_discoveries.csv", [
                {"ticker": "NTLA", "drug": "different trial",
                 "indication": "other program", "nct_id": "NCT11111111",
                 "readout_date": "2026-08-12",
                 "source_url": "https://issuer.example/other"}
            ])
            write(root, "phase_pipeline.csv", [
                {"ticker": "NTLA", "nct_id": "NCT11111111", "phase": "PHASE3"},
            ])
            pending, _ = build_potential_list(root, as_of=date(2026, 10, 14))
            extra = next(x for x in pending if x["Exact program"] == "TRIAL|NTLA|NCT11111111")
            self.assertEqual(extra["Pipeline ID"], "TRIAL|NCT11111111")
            self.assertEqual(extra["SEC documents rechecked"], 0)
            self.assertEqual(extra["Evidence type"], "Issuer Phase 3 readout (review)")
            self.assertIn("verify two separate", extra["Still needed"])

    def test_pre_oct15_independent_leads_enter_research_without_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            write(root, "post_phase3_discoveries.csv", [
                {"ticker": "ORPH", "drug": "unmapped", "indication": "test",
                 "nct_id": "NCT33333333", "readout_date": "2026-09-22",
                 "source_url": "https://issuer.example/orphan"},
                {"ticker": "WRONG", "drug": "issuer mismatch", "indication": "test",
                 "nct_id": "NCT44444444", "readout_date": "2026-09-22",
                 "source_url": "https://issuer.example/conflict"},
            ])
            write(root, "phase_pipeline.csv", [
                {"ticker": "RIGHT", "nct_id": "NCT44444444", "phase": "PHASE3"},
            ])
            active, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertIn("ORPH", {x["Ticker"] for x in active})
            # A known mismatched issuer for the same trial remains blocked.
            self.assertNotIn("WRONG", {x["Ticker"] for x in active + held})
            orphan = next(x for x in active if x["Ticker"] == "ORPH")
            self.assertEqual(orphan["Pipeline ID"], "TRIAL|NCT33333333|ISSUER|ORPH")
            self.assertEqual(orphan["Pipeline linkage"],
                             "PENDING PIPELINE INTAKE — RESEARCH ONLY")
            self.assertEqual(orphan["SEC documents rechecked"], 0)
            self.assertTrue(all(x.get("Pipeline ID") for x in active + held))

    def test_without_regulatory_candidates_pipeline_trial_lead_still_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root, "phase_pipeline.csv", [
                {"ticker": "NEW", "nct_id": "NCT55555555", "phase": "PHASE3"},
            ])
            write(root, "post_phase3_discoveries.csv", [
                {"ticker": "NEW", "drug": "trial-only", "indication": "test",
                 "nct_id": "NCT55555555", "readout_date": "2026-09-22",
                 "source_url": "https://issuer.example/new"},
            ])
            active, held = build_potential_list(root, as_of=date(2026, 10, 14))
            self.assertEqual([r["Pipeline ID"] for r in active], ["TRIAL|NCT55555555"])
            self.assertEqual(held, [])

    def test_rendered_potential_is_an_ordered_list_with_reason_and_pending(self):
        from gem_potential_ui import numbered_potential_markdown
        lines = numbered_potential_markdown([
            {"Ticker": "NTLA", "Drug": "lonvo-z",
             "Why potential": "Two source-linked financing transactions",
             "Still needed": "Exact Phase 3 readout"},
            {"Ticker": "AXSM", "Drug": "AXS-12",
             "Why potential": "Clinical registry result observed",
             "Still needed": "Second financing audit"},
        ])
        self.assertIn("1. **NTLA · lonvo-z**", lines)
        self.assertIn("2. **AXSM · AXS-12**", lines)
        self.assertIn("**Why potential:** Two source-linked financing", lines)
        self.assertIn("**Pending:** Second financing audit", lines)

    def test_overview_has_visible_new_section_under_gem_one(self):
        root = Path(__file__).resolve().parents[1]
        overview = (root / "unified_clinical_trading.py").read_text(encoding="utf-8")
        potential_ui = (root / "gem_potential_ui.py").read_text(encoding="utf-8")
        first = overview.index('st.markdown("### 3 — GEM")')
        render = overview.index('render_gem_potential(root=root, compact=True', first)
        next_panel = overview.index('with st.expander("PDUFA TIMELINE"', first)
        self.assertLess(first, render)
        self.assertLess(render, next_panel)
        self.assertIn('### POTENTIAL GEMs — PENDING RESEARCH', potential_ui)
        self.assertIn('st.markdown(numbered_potential_markdown(potential))', potential_ui)
        self.assertIn('**Why potential:**', potential_ui)
        self.assertIn('**Pending:**', potential_ui)
        self.assertIn("EXPORT POTENTIAL GEMs + REASONS", potential_ui)


if __name__ == "__main__":
    unittest.main()
