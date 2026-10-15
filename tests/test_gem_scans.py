"""Regression tests for the three source-gated GEMS scans in SCANS."""
from pathlib import Path
from unittest.mock import patch

from gem_scans import STAGES, WEIGHTS, build_gem_scans, all_mandatory_entry_gates_pass

ROOT = Path(__file__).resolve().parents[1]


def sample(ticker="AAA", market=10, second=True, days=40):
    return {
        "Ticker": ticker, "Drug": "Drug " + ticker, "NCT ID": "NCT01234567",
        "Exact event": ticker + "|DRUG_20261130", "Source lane": "SAVED REGULATORY PIPELINE",
        "Entry qualification": "GREEN — GATES ATTESTED",
        "Phase 3 evidence": "VERIFIED SUCCESS — SOURCE LINKED",
        "2nd Financing Completed": (
            "YES — VERIFIED (HISTORICAL)" if second else "NOT VERIFIED"
        ),
        "Verified 2nd financing close date": "2026-09-15" if second else "",
        "PDUFA verification": "VERIFIED — SOURCE LINKED",
        "Days to PDUFA": days, "Evidence score /100": 85,
        "Clinical evidence /30": 30, "Financing evidence /20": 20,
        "Trading setup /20": 20, "PDUFA evidence /15": 15,
        "Market activity /10": market, "As of Pacific": "2026-10-13",
    }


def sec_snapshot(ticker, cash=140_000_000):
    return {
        "ticker": ticker, "cik": "0000000123", "as_of": "2026-10-13",
        "cash_usd": cash, "operating_cash_flow_usd": -30_000_000,
        "operating_cash_flow_months": 3, "runway_months_cash_only": cash / 10_000_000,
        "cash_includes_restricted": False, "review_flags": [],
        "evidence": {
            "companyfacts_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json",
            "cash": {"form": "10-Q", "accession": "0000000123-26-000001",
                     "period_end": "2026-09-30", "filed": "2026-10-10"},
            "operating_cash_flow": {"form": "10-Q", "accession": "0000000123-26-000001",
                                    "period_end": "2026-09-30", "filed": "2026-10-10"},
        },
    }


def run(rows, *, fresh=True, events=None, sec_current=True, runway=True):
    verified_events = {
        r["Exact event"]: {
            "ticker": r["Ticker"], "nct_id": r["NCT ID"],
            "phase3_status": "VERIFIED_SUCCESS",
            "phase3_date": "2026-10-01",
            "trial_evidence_url": "https://issuer.example/verified-readout",
            "conflict_flag": "NONE", "new_dilution_flag": "NO",
        }
        for r in rows
    }
    # Synthetic positive fixtures must contain FULL pre-signal primary
    # evidence, not just an unaudited score string and event identifier.
    if events is not None:
        for key, overrides in events.items():
            if key in verified_events:
                verified_events[key].update(overrides)
    events = verified_events
    financial = ({item["Ticker"]: sec_snapshot(item["Ticker"]) for item in rows}
                 if runway else {})
    origin_ids = {"APPLICATION|" + str(row["Exact event"]) for row in rows}
    origin_tickers = {"APPLICATION|" + str(row["Exact event"]): row["Ticker"] for row in rows}
    with patch("gem_scans.pipeline_origins", return_value=(origin_ids, origin_tickers)), \
            patch("gem_scans.load_snapshots", return_value=financial), patch("gem_scans.build_queue", return_value=(
        rows, {"feed_current": fresh, "as_of": "2026-10-13"},
    )), patch("gem_scans._event_map", return_value=events), patch(
        "gem_scans.sec_recheck_current", return_value=sec_current
    ):
        return build_gem_scans("fake-path")



class GemScanRegressionTests(__import__('unittest').TestCase):
    def test_all_three_stage_scores_are_independent_and_labeled(self):
        rows, status = run([sample(market=10), sample("BBB", market=7)])
        assert len(STAGES) == 3
        assert all(sum(weights.values()) == 100 for weights in WEIGHTS.values())
        assert rows[0]["Phase 3 GEM"] == "#1 (100)"
        assert rows[0]["Post-Financing GEM"] == "#1 (100)"
        assert rows[0]["PDUFA GEM"] == "#1 (100)"
        assert rows[0]["GEM trade entry gate"].startswith("POST-CLOSE ENTRY REVIEW ELIGIBLE")
        assert rows[1]["Phase 3 GEM"] == "#2 (96)"
        assert rows[1]["Post-Financing GEM"] == "#2 (97)"
        assert rows[1]["PDUFA GEM"] == "#2 (96)"
        assert all(status["scan_counts"][stage]["qualified"] == 2 for stage in STAGES)


    def test_only_fully_qualified_all_stage_and_second_closed_programs_enter_shortlist(self):
        best = sample("AAA", market=10)
        one_short = sample("BBB", market=7)
        one_short["Entry qualification"] = "REVIEW — ENTRY BLOCKED"
        before_second = sample("CCC", second=False)
        on_exit = sample("DDD", days=3)
        rows, status = run([best, one_short, before_second, on_exit])
        self.assertEqual(status["strict_entry_gate_shortlist_count"], 1)
        self.assertEqual(sum(all_mandatory_entry_gates_pass(row) for row in rows), 1)
        self.assertEqual(rows[0]["GEM strict shortlist rank"], 1)
        self.assertEqual(rows[0]["GEM ALL ENTRY GATES"], "PASS — MANUAL REVIEW ONLY")
        self.assertTrue(all(row["GEM strict shortlist rank"] is None for row in rows[1:]))
        self.assertTrue(all(row["GEM ALL ENTRY GATES"] == "NOT MET — WATCH / REVIEW"
                            for row in rows[1:]))
        # A high research rank is explicitly insufficient without Stage 1 GREEN.
        self.assertIsNotNone(rows[1]["PDUFA rank"])
        self.assertFalse(all_mandatory_entry_gates_pass(rows[1]))

    def test_strict_shortlist_empty_if_sec_blocked_or_financing_not_closed(self):
        for kwargs in (
            {"sec_current": False},
            {"fresh": False},
        ):
            rows, status = run([sample()], **kwargs)
            self.assertEqual(status["strict_entry_gate_shortlist_count"], 0)
            self.assertIsNone(rows[0]["GEM strict shortlist rank"])
        rows, status = run([sample(second=False)])
        self.assertEqual(status["strict_entry_gate_shortlist_count"], 0)
        rows, status = run([sample(days=3)])
        self.assertEqual(status["strict_entry_gate_shortlist_count"], 0)
        row = sample()
        row["Verified 2nd financing close date"] = ""
        rows, status = run([row])
        self.assertEqual(status["strict_entry_gate_shortlist_count"], 0)

    def test_global_sec_blocked_cannot_produce_post_financing_or_pdufa_entry(self):
        rows, status = run([sample(second=True)], sec_current=False)
        assert status["sec_financing_source_current"] is False
        assert rows[0]["Phase 3 rank"] == 1  # early watch is still allowed
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None
        assert rows[0]["GEM trade entry gate"] == "HOLD — STALE SOURCE EVIDENCE"
        assert "unblocked SEC" in rows[0]["Post-Financing missing"]

    def test_no_cash_runway_does_not_block_phase3_but_blocks_post_finance(self):
        rows, details = run([sample()], runway=False)
        assert rows[0]["Phase 3 rank"] == 1
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None
        assert details["strict_entry_gate_shortlist_count"] == 0
        assert "RUNWAY" in rows[0]["GEM trade entry gate"]

    def test_sub_12_month_cash_runway_is_not_trade_eligible(self):
        with patch("gem_scans.load_snapshots", return_value={"AAA": sec_snapshot("AAA", 100_000_000)}):
            # Use the regular fixture runner with missing runway first to prove the
            # stricter outside-of-scoring control; source unit tests cover 10 months.
            row = sample()
            assessed = __import__("gem_runway_gate").assess_runway(
                "AAA", sec_snapshot("AAA", 100_000_000),
                as_of="2026-10-13", second_close="2026-09-15")
            assert assessed["Cash runway gate"].startswith("HOLD")

    def test_financing_is_only_scored_when_exact_second_closing_verified(self):
        rows, _ = run([sample(second=False)])
        assert rows[0]["Phase 3 rank"] == 1
        assert rows[0]["GEM trade entry gate"] == "WATCH ONLY — SECOND FINANCING NOT VERIFIED CLOSED"
        assert rows[0]["Post-Financing score"] is None
        assert "Second separate" in rows[0]["Post-Financing missing"]


    def test_pdufa_trade_window_runs_from_verified_finance_until_minus_three(self):
        rows, _ = run([sample(days=3), sample("BBB", days=4), sample("CCC", days=91)])
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None
        assert rows[1]["Post-Financing rank"] is not None
        assert rows[1]["PDUFA rank"] is not None
        assert rows[2]["Post-Financing rank"] is not None
        assert rows[2]["PDUFA rank"] is not None

    def test_last_week_survives_old_stage1_red_cutoff_if_primary_source_verified(self):
        row = sample(days=5)
        row["Entry qualification"] = "RED WINDOW — NO NEW ENTRY"
        row["PDUFA evidence /15"] = 0  # older Stage 1 day-7 scoring rule
        rows, _ = run([row])
        assert rows[0]["PDUFA rank"] == 1
        assert rows[0]["PDUFA score"] == 100

    def test_last_week_missing_fda_verification_never_overrides_source_gate(self):
        row = sample(days=5)
        row["Entry qualification"] = "RED WINDOW — NO NEW ENTRY"
        row["PDUFA verification"] = "REVIEW — NOT VERIFIED"
        row["PDUFA evidence /15"] = 0
        rows, _ = run([row])
        assert rows[0]["PDUFA rank"] is None


    def test_stale_and_unrated_feeds_have_no_gem_ranks(self):
        stale, _ = run([sample()], fresh=False)
        assert all(stale[0][stage + " score"] is None for stage in STAGES)
        unrated = sample()
        unrated["Evidence score /100"] = None
        rows, _ = run([unrated])
        assert all(rows[0][stage + " rank"] is None for stage in STAGES)


    def test_conflicting_regulatory_evidence_fail_closed(self):
        row = sample()
        rows, _ = run([row], events={
            row["Exact event"]: {"conflict_flag": "REVIEW", "new_dilution_flag": "NO"}
        })
        assert all(rows[0][stage + " rank"] is None for stage in STAGES)


    def test_dilution_flag_blocks_financing_and_pdufa_but_not_phase3_research(self):
        row = sample()
        rows, _ = run([row], events={
            row["Exact event"]: {"conflict_flag": "NONE", "new_dilution_flag": "UNKNOWN"}
        })
        assert rows[0]["Phase 3 rank"] == 1
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None


    def test_equal_scores_share_rank_without_dropping_candidates(self):
        rows, _ = run([sample(), sample("BBB"), sample("CCC", market=7)])
        assert [r["Phase 3 rank"] for r in rows] == [1, 1, 3]


    def test_track_immediately_after_verified_successful_phase3_without_financing(self):
        row = sample(second=False, days=None)
        row["Trading setup /20"] = 0
        row["Evidence score /100"] = 30
        event = {
            row["Exact event"]: {
                "phase3_status": "VERIFIED_SUCCESS",
                "phase3_date": "2026-10-01",
                "trial_evidence_url": "https://issuer.example/phase3-results",
                "conflict_flag": "NONE",
                "new_dilution_flag": "NO",
                "outcome": "",
            }
        }
        rows, meta = run([row], events=event)
        assert rows[0]["Phase 3 tracking"] == "TRACKING — VERIFIED SUCCESSFUL PHASE 3"
        assert rows[0]["Phase 3 result date (source)"] == "2026-10-01"
        assert rows[0]["Financing watch"].startswith("SECOND FINANCING NOT VERIFIED")
        assert rows[0]["Phase 3 rank"] is None  # Technical entry gates still missing.
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["GEM trade entry gate"] == "WATCH ONLY — SECOND FINANCING NOT VERIFIED CLOSED"
        assert meta["phase3_tracking_count"] == 1
        assert meta["phase3_tracking_before_second_financing"] == 1

    def test_end_of_phase3_without_verified_success_cannot_start_tracking(self):
        row = sample(second=False)
        event = {
            row["Exact event"]: {
                "phase3_status": "RESULTS_REVIEW",
                "phase3_date": "2026-10-01",
                "trial_evidence_url": "https://issuer.example/topline",
                "conflict_flag": "NONE",
            }
        }
        rows, meta = run([row], events=event)
        assert rows[0]["Phase 3 tracking"].startswith("AWAITING VERIFIED")
        assert rows[0]["Phase 3 rank"] is None
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None
        assert meta["phase3_tracking_count"] == 0

    def test_verified_phase3_with_stale_source_stays_on_hold(self):
        row = sample(second=False)
        event = {
            row["Exact event"]: {
                "phase3_status": "VERIFIED_SUCCESS",
                "phase3_date": "2026-10-01",
                "trial_evidence_url": "https://issuer.example/phase3-results",
                "conflict_flag": "NONE",
            }
        }
        rows, meta = run([row], fresh=False, events=event)
        assert rows[0]["Phase 3 tracking"] == "VERIFICATION HOLD — SOURCE STALE"
        assert meta["phase3_tracking_count"] == 0

    def test_phase3_tracking_never_resurrects_resolved_fda_event(self):
        row = sample(second=False)
        event = {
            row["Exact event"]: {
                "phase3_status": "VERIFIED_SUCCESS",
                "phase3_date": "2026-10-01",
                "trial_evidence_url": "https://issuer.example/phase3-results",
                "conflict_flag": "NONE",
                "outcome": "APPROVED",
            }
        }
        rows, meta = run([row], events=event)
        assert rows[0]["Phase 3 tracking"] == "CLOSED — FDA EVENT RESOLVED"
        assert meta["phase3_tracking_count"] == 0

    def test_original_scans_and_protected_controls_are_preserved(self):
        source = (ROOT / "nightly_scan_dashboard.py").read_text(encoding="utf-8")
        assert "render_gem_scans()" in source
        assert "render_extended_source_report()" in source
        assert 'st.markdown("## NIGHTLY SCAN REPORT")' in source
        assert "PDUFA_SCAN_CONTROL_PIN" in source
        assert 'dispatch_action(action, scan, token)' in source
        ui = (ROOT / "gem_scans_ui.py").read_text(encoding="utf-8")
        assert "### GEM — UNIFIED MASTER LIST" in ui
        assert "build_gem_master_list(items)" in ui
        assert "EXPORT GEM MASTER LIST" in ui
        nested = (ROOT / "gem_nested_master_ui.py").read_text(encoding="utf-8")
        assert "FACTOR_FIELDS" in nested
        assert "score_factor_inputs" in nested
        assert 'args=(ticker, "watch")' in nested
        assert 'args=(ticker, "trade")' in nested

