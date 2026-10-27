"""Reference-image GEM page contract: source data, ranked controls and disclosures."""
import unittest
import tempfile
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gem_visual_page import _show, _rankings
from gem_stage_dossier import scan_diagnostics
from gem_reference_dashboard import resolve_dashboard_action, _candidate, _all_company_trials, _hierarchy, _junior_section8_checks, _gem_section9_entry_checks, _junior_section9_exit_checks, _junior_section10_history, _gem_section10_exit_checks, _gem_history_timeline

ROOT = Path(__file__).resolve().parents[1]


class GemVisualPageTests(unittest.TestCase):
    def test_missing_data_is_never_represented_as_an_actual_score(self):
        self.assertEqual(_show(None), "NOT AVAILABLE")
        self.assertEqual(_show("nan"), "NOT AVAILABLE")
        self.assertEqual(_show("  "), "NOT AVAILABLE")
        self.assertEqual(_show("2026-10-15"), "2026-10-15")

    @patch("gem_visual_page.assess_gem_trade")
    @patch("gem_visual_page.exact_event", return_value={"company": "Test"})
    @patch("gem_visual_page.load_market_rows", return_value={})
    def test_junior_research_does_not_gain_gem_trade_scores(
        self, market, event, assess
    ):
        assess.return_value = {"base": {"status": "NO SOURCE"}, "bars": [],
                               "recommendation": "WAIT"}
        candidates = [{"Ticker": "TEST", "Exact program": "TEST|TRIAL1",
                       "Drug": "Research only"}]
        rows = _rankings("GEM JR", candidates, "data", date(2026, 10, 15))
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0][4]["entry"])
        self.assertIsNone(rows[0][4]["exit_risk"])
        self.assertIsNone(rows[0][4]["quality"])

    def test_w_t_actions_resolve_from_exact_program_not_client_ticker(self):
        payload = {"candidates": [{"id": "APPLICATION|TEST|A", "ticker": "TEST"}]}
        for action in ("watch", "trade"):
            result = resolve_dashboard_action({
                "nonce": "click-1", "action": action,
                "id": "APPLICATION|TEST|A", "ticker": "WRONG",
            }, payload)
            self.assertEqual(result, {"action": action, "ticker": "TEST"})
        self.assertIsNone(resolve_dashboard_action({
            "nonce": "click-2", "action": "trade", "id": "UNKNOWN",
        }, payload))

    def test_ambiguous_or_expired_component_targets_fail_closed(self):
        same = {"id": "APPLICATION|TEST|A", "ticker": "TEST"}
        event = {"nonce": "click-1", "action": "watch", "id": same["id"]}
        self.assertIsNone(resolve_dashboard_action(event, {"candidates": [same, same]}))
        self.assertIsNone(resolve_dashboard_action(event, {"candidates": []}))
        self.assertIsNone(resolve_dashboard_action({"action": "watch"}, {"candidates": [same]}))

    def test_only_existing_research_navigation_and_policies_are_accepted(self):
        payload = {"candidates": []}
        for value in ("SCANS", "WT", "GEM JR"):
            self.assertEqual(resolve_dashboard_action({"nonce": "x", "action": "navigate", "tab": value}, payload),
                             {"action": "navigate", "tab": value})
        for event in ({"action": "order", "ticker": "TEST"},
                      {"action": "navigate", "tab": "BROKER"},
                      {"action": "policy", "policy": "automatic"}):
            self.assertIsNone(resolve_dashboard_action({"nonce": "x", **event}, payload))

    def test_section4_lists_saved_company_trials_with_stage_specific_exact_nct_flags(self):
        import csv
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            registry = [
                {"ticker": "ABCD", "nct_id": "NCT00000001", "phase": "Phase 1",
                 "drug": "Alpha", "indication": "Disease 1", "source_url": "https://clinicaltrials.gov/study/NCT00000001"},
                {"ticker": "ABCD", "nct_id": "NCT00000002", "phase": "Phase 2",
                 "drug": "Beta", "indication": "Disease 2"},
                {"ticker": "ABCD", "nct_id": "NCT00000003", "phase": "Phase 3",
                 "drug": "Gamma", "indication": "Disease 3"},
                {"ticker": "OTHER", "nct_id": "NCT00000002", "phase": "Phase 3",
                 "drug": "Unrelated", "indication": "Other disease"},
            ]
            with (Path(root) / "all_phase_trials.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=registry[0].keys())
                writer.writeheader()
                for row in registry:
                    writer.writerow(row)
            gem = [{"Ticker": "ABCD", "NCT ID": "NCT00000003",
                    "Exact program": "ABCD|DRUG3"}]
            junior = [{"Ticker": "ABCD", "NCT ID": "NCT00000002",
                       "Exact program": "ABCD|DRUG2"}]
            by_ticker, coverage = _all_company_trials(root, gem=gem, junior=junior)
            abcd = {trial["nct"]: trial for trial in by_ticker["ABCD"]}
            self.assertEqual(len(abcd), 3)
            self.assertEqual(abcd["NCT00000001"]["phase"], "Phase 1")
            self.assertEqual(abcd["NCT00000001"]["stage_labels"], [])
            self.assertEqual(abcd["NCT00000002"]["phase"], "Phase 2")
            self.assertEqual(abcd["NCT00000002"]["stage_labels"], ["GEM JR"])
            self.assertEqual(abcd["NCT00000003"]["stage_labels"], ["GEM"])
            self.assertEqual(by_ticker["OTHER"][0]["stage_labels"], [])
            self.assertEqual(abcd["NCT00000003"]["url"],
                             "https://clinicaltrials.gov/study/NCT00000003")
            self.assertNotIn("PARTIAL", coverage)

    def test_section4_absent_full_registry_does_not_claim_complete_inventory(self):
        with tempfile.TemporaryDirectory() as root:
            gem = [{"Ticker": "ABCD", "NCT ID": "NCT00000004 | NCT00000005",
                    "Exact program": "ABCD|DRUG4"}]
            by_ticker, coverage = _all_company_trials(root, gem=gem, junior=[])
            self.assertIn("PARTIAL", coverage)
            self.assertEqual({t["nct"] for t in by_ticker["ABCD"]},
                             {"NCT00000004", "NCT00000005"})
            self.assertTrue(all(t["stage_labels"] == ["GEM"]
                                for t in by_ticker["ABCD"]))
            self.assertTrue(all(t["phase"] == "Not verified in saved sources"
                                for t in by_ticker["ABCD"]))

    def test_section5_trial_tree_includes_all_saved_phases_and_exact_gem_labels(self):
        record = {"Ticker": "TEST", "NCT ID": "NCT00000003",
                  "Drug": "Drug Three", "Indication": "Condition 3",
                  "Phase 3 status": "PRIMARY_MET_VERIFIED",
                  "Phase 3 date": "2026-09-12",
                  "Phase 3 source": "https://www.sec.gov/exactphase3"}
        trials = [
            {"nct": "NCT00000001", "drug": "Drug One", "indication": "Condition 1",
             "phase": "Phase 1", "stage_labels": [], "selected_source": ""},
            {"nct": "NCT00000002", "drug": "Drug Two", "indication": "Condition 2",
             "phase": "Phase 2", "stage_labels": ["GEM JR"], "selected_source": ""},
            {"nct": "NCT00000003", "drug": "Drug Three", "indication": "Condition 3",
             "phase": "Phase 3", "stage_labels": ["GEM"],
             "selected_source": "https://www.sec.gov/verified-results"},
            {"nct": "NCT00000004", "drug": "Drug Four", "indication": "Condition 4",
             "phase": "Phase 4", "stage_labels": [], "selected_source": ""},
        ]
        registry = [
            {"ticker": "TEST", "nct_id": "NCT00000003", "phase": "Phase 3",
             "status": "COMPLETED"},
            {"ticker": "OTHER", "nct_id": "NCT00000002", "phase": "Phase 3",
             "status": "COMPLETED"},
        ]
        pvalues = [
            {"ticker": "TEST", "nct_id": "NCT00000003",
             "primary_endpoint": "Exact trial endpoint", "p_value": "0.001"},
            {"ticker": "OTHER", "nct_id": "NCT00000002",
             "primary_endpoint": "Wrong issuer endpoint", "p_value": "0.0001"},
        ]
        for stage in ("GEM JR", "GEM"):
            nested = _hierarchy(record, {}, "Test Bio", registry, pvalues, trials)
            all_trials = {t["nct"]: t for g in nested for t in g["trials"]}
            self.assertEqual(len(all_trials), 4)
            self.assertEqual([all_trials[f"NCT0000000{i}"]["phase"]
                              for i in range(1, 5)],
                             ["Phase 1", "Phase 2", "Phase 3", "Phase 4"])
            self.assertEqual(all_trials["NCT00000002"]["stage_labels"], ["GEM JR"])
            self.assertEqual(all_trials["NCT00000003"]["stage_labels"], ["GEM"])
            self.assertEqual(all_trials["NCT00000002"]["endpoint"],
                             "Not available in saved sources")
            self.assertEqual(all_trials["NCT00000002"]["p_value"],
                             "Not available in saved sources")
            self.assertEqual(all_trials["NCT00000003"]["endpoint"],
                             "Exact trial endpoint")
            self.assertEqual(all_trials["NCT00000003"]["p_value"], "0.001")
            self.assertEqual(all_trials["NCT00000003"]["result_type"], "pass")
            self.assertEqual(all_trials["NCT00000003"]["evidence_url"],
                             "https://www.sec.gov/verified-results")
            self.assertEqual(all_trials["NCT00000003"]["url"],
                             "https://clinicaltrials.gov/study/NCT00000003")

    def test_section5_multi_trial_program_never_assigns_individual_endpoint_success(self):
        record = {"Ticker": "TEST", "NCT ID": "NCT00000006 | NCT00000007",
                  "Drug": "Drug Group", "Indication": "Disease",
                  "Phase 3 status": "PRIMARY_MET_VERIFIED"}
        nested = _hierarchy(record, {"reported_p_values": "0.01"}, "Test Bio",
                            [], [], [])
        all_trials = {t["nct"]: t for g in nested for t in g["trials"]}
        self.assertEqual(set(all_trials), {"NCT00000006", "NCT00000007"})
        for item in all_trials.values():
            self.assertEqual(item["phase"], "Phase not verified")
            self.assertEqual(item["result_type"], "unknown")
            self.assertEqual(item["p_value"], "Not available in saved sources")
            self.assertEqual(item["url"],
                             f"https://clinicaltrials.gov/study/{item['nct']}")

    def test_section8_junior_readiness_is_ordered_and_never_claims_two_financing_pass(self):
        record = {
            "Ticker": "TEST", "Pipeline ID": "APPLICATION|TEST|DRUGA",
            "NCT ID": "NCT00000001", "Phase 3 status": "PRIMARY_MET_VERIFIED",
            "Phase 3 date": "2026-08-01",
            "Clinical source": "https://www.sec.gov/trial",
            "SEC documents rechecked": 2,
            "Financing SEC source": "https://www.sec.gov/second",
            "Still needed": "Confirm both distinct closings after the readout",
        }
        event = {
            "market_cap": "800000000", "new_dilution_flag": "NO",
            "pdufa_confirmation": "REPORTED_ONLY",
            "pdufa_date": "2027-02-16",
        }
        profile = {"fresh": True, "dollar_volume": 2500000}
        runway = {"Cash runway (months)": None,
                  "Cash runway reason": "Missing source"}
        sources = [
            {"label": "Financing #1", "url": "https://www.sec.gov/first"},
            {"label": "Financing #2", "url": "https://www.sec.gov/second"},
            {"label": "PDUFA target", "url": ""},
        ]
        checks = _junior_section8_checks(record, event, profile,
                                          runway, sources, {})
        self.assertEqual(len(checks), 11)
        self.assertEqual([x["priority"] for x in checks], list(range(1, 12)))
        self.assertTrue(checks[0]["status"])  # Pipeline + valid exact NCT
        self.assertTrue(checks[1]["status"])  # Source-linked dated Phase 3 label
        self.assertIsNone(checks[3]["status"])  # Saved SEC link does not qualify
        self.assertIsNone(checks[4]["status"])  # 2 checked docs != 2 verified closes
        self.assertIsNone(checks[5]["status"])  # Missing cash source
        self.assertIsNone(checks[6]["status"])  # Saved market cap needs independent check
        self.assertIsNone(checks[7]["status"])  # No flag != risk-free
        self.assertIsNone(checks[9]["status"])  # Reported PDUFA != verified
        self.assertTrue(all(x["points"] == "—" for x in checks))

    def test_section8_junior_flags_explicit_risks_without_faking_success(self):
        record = {
            "Ticker": "TEST", "Pipeline ID": "TRIAL|NCT00000001",
            "NCT ID": "NCT00000001",
        }
        event = {
            "market_cap": "250000000", "new_dilution_flag": "YES",
            "pdufa_confirmation": "REPORTED_ONLY",
        }
        checks = _junior_section8_checks(record, event, {"fresh": False},
                                          {}, [], {})
        self.assertEqual(checks[6]["status"], False)  # Outside saved cap range
        self.assertEqual(checks[7]["status"], False)  # Explicit dilution alert
        self.assertIsNone(checks[1]["status"])  # Missing Phase 3 verification
        self.assertIsNone(checks[5]["status"])  # Missing cash assessment
        self.assertIsNone(checks[9]["status"])  # No FDA date verification

    def test_section9_gem_entry_gates_do_not_equate_saved_benchmarks_with_trade_clearance(self):
        record = {
            "Ticker": "TEST", "NCT ID": "NCT00000001",
            "Phase 3 status": "PRIMARY_MET_VERIFIED",
            "Phase 3 date": "2026-04-01",
            "Phase 3 source": "https://clinicaltrials.gov/study/NCT00000001",
            "First close": "2026-05-01",
            "Second close": "2026-06-01",
            "First SEC source": "https://www.sec.gov/first",
            "Second SEC source": "https://www.sec.gov/second",
            "Second financing verified": True,
            "Source review as of": "2026-10-15",
            "PDUFA verified": True,
            "PDUFA saved": "2027-03-20",
        }
        event = {"market_cap": "550000000"}
        profile = {
            "fresh": True, "date": date(2026, 10, 16),
            "close": 15.0, "sma20": 13.0, "sma50": 12.0,
            "dollar_volume": 3000000,
        }
        runway = {"Cash runway (months)": 16,
                  "Cash runway source": "https://www.sec.gov/cash",
                  "Cash runway as of": "2026-09-30"}
        checks = _gem_section9_entry_checks(
            record, event, profile, runway,
            date(2026, 10, 17), source_current=True
        )
        self.assertEqual(len(checks), 10)
        self.assertEqual([c["priority"] for c in checks], list(range(1, 11)))
        self.assertTrue(all(c["status"] is True for c in checks[:6]))
        self.assertIsNone(checks[6]["status"])  # in range != current verified
        self.assertIsNone(checks[7]["status"])  # no negative flag != safe
        self.assertIsNone(checks[8]["status"])  # trend != buy approval
        self.assertIsNone(checks[9]["status"])  # position plan still required
        self.assertTrue(all(c["points"] == "—" for c in checks))

        unreviewed = dict(record, **{"Second financing verified": False})
        saved_only = _gem_section9_entry_checks(
            unreviewed, event, profile, runway,
            date(2026, 10, 17), source_current=True
        )
        self.assertIsNone(saved_only[1]["status"])
        self.assertIsNone(saved_only[2]["status"])

        stale = _gem_section9_entry_checks(
            record, event, profile, runway,
            date(2026, 10, 17), source_current=False
        )
        self.assertIs(stale[0]["status"], True)  # saved clinical source remains
        self.assertIs(stale[3]["status"], False)  # stale SEC source blocks entry
        old = dict(record, **{"Source review as of": "2026-09-01"})
        stale = _gem_section9_entry_checks(
            old, event, profile, runway,
            date(2026, 10, 17), source_current=True
        )
        # Optional funding review age cannot override a current global SEC
        # source check. Missing current SEC coverage above still holds entry.
        self.assertIs(stale[3]["status"], True)

    def test_section9_gem_missing_second_financing_never_passes(self):
        record = {
            "Ticker": "TEST", "NCT ID": "NCT00000001",
            "Phase 3 status": "PRIMARY_MET_VERIFIED",
            "Phase 3 date": "2026-04-01",
            "Phase 3 source": "https://clinicaltrials.gov/study/NCT00000001",
            "First close": "2026-05-01",
            "Second close": "2026-03-01",  # before Phase 3, disallowed
            "First SEC source": "https://www.sec.gov/first",
            "Second SEC source": "https://www.sec.gov/second",
            "PDUFA saved": "2026-10-19",  # two days: no new entry
        }
        checks = _gem_section9_entry_checks(
            record, {}, {"fresh": False}, {},
            date(2026, 10, 17), source_current=None
        )
        self.assertIs(checks[0]["status"], True)
        self.assertIsNone(checks[1]["status"])
        self.assertIsNone(checks[2]["status"])
        self.assertIs(checks[3]["status"], False)
        self.assertIs(checks[4]["status"], False)
        self.assertIsNone(checks[5]["status"])

    def test_section9_future_financings_and_stale_cash_do_not_pass(self):
        record = {
            "Ticker": "TEST", "NCT ID": "NCT00000001",
            "Phase 3 status": "PRIMARY_MET_VERIFIED",
            "Phase 3 date": "2026-04-01",
            "Phase 3 source": "https://clinicaltrials.gov/study/NCT00000001",
            "First close": "2026-11-01",
            "Second close": "2026-12-01",
            "First SEC source": "https://www.sec.gov/first",
            "Second SEC source": "https://www.sec.gov/second",
        }
        runway = {
            "Cash runway (months)": 24,
            "Cash runway source": "https://www.sec.gov/cash",
            "Cash runway as of": "2025-06-01",
        }
        checks = _gem_section9_entry_checks(record, {}, {}, runway,
                                            date(2026, 10, 17), source_current=True)
        self.assertIsNone(checks[1]["status"])
        self.assertIsNone(checks[2]["status"])
        self.assertIsNone(checks[5]["status"])

    def test_section9_junior_exit_flags_specific_adverse_evidence_only(self):
        record = {
            "Ticker": "TEST", "NCT ID": "NCT00000001",
            "Phase 3 status": "PRIMARY_FAILED_VERIFIED",
            "PDUFA date (saved)": "2026-10-19",
            "Source review date": "2026-10-01",
        }
        event = {
            "outcome": "CRL", "new_dilution_flag": "YES",
            "conflict_flag": "ACTIVE",
            "pdufa_evidence_url": "https://www.fda.gov/result",
        }
        profile = {
            "fresh": True, "date": date(2026, 10, 16),
            "close": 6.0, "sma50": 8.0,
            "base": {"support": 7.0},
        }
        runway = {
            "Cash runway (months)": 3.5,
            "Cash runway source": "https://www.sec.gov/cash",
            "Cash runway as of": "2026-09-30",
        }
        checks = _junior_section9_exit_checks(
            record, event, profile, runway, date(2026, 10, 17)
        )
        self.assertEqual(len(checks), 9)
        self.assertEqual([c["priority"] for c in checks], list(range(1, 10)))
        self.assertTrue(all(c["status"] is False for c in checks[:8]))
        self.assertIsNone(checks[8]["status"])
        self.assertEqual(checks[0]["url"], "https://www.fda.gov/result")
        no_data = _junior_section9_exit_checks(
            {"Ticker": "TEST"}, {}, {"fresh": False, "base": {}}, {},
            date(2026, 10, 17)
        )
        self.assertTrue(all(c["status"] is None for c in no_data))
        self.assertTrue(all(c["points"] == "—" for c in no_data))

    def test_section10_junior_promotion_requires_exact_observed_gem_identity(self):
        history = {
            "stages": {
                "GEM_JR": {
                    "entries": {
                        "TRIAL|NCT00000001": {
                            "pipeline_id": "TRIAL|NCT00000001",
                            "ticker": "AAA", "drug": "Drug A",
                            "nct_id": "NCT00000001", "status": "LEFT",
                            "periods": [{
                                "found": "2026-10-10", "left": "2026-10-16",
                                "reason": "PROMOTED_TO_GEM",
                            }],
                        },
                        "TRIAL|NCT00000002": {
                            "pipeline_id": "TRIAL|NCT00000002",
                            "ticker": "BBB", "drug": "Drug B",
                            "nct_id": "NCT00000002", "status": "ACTIVE",
                            "periods": [
                                {"found": "2026-10-10", "left": "2026-10-12",
                                 "reason": "NO_LONGER_IN_VERIFIED_STAGE_SNAPSHOT"},
                                {"found": "2026-10-15", "left": None, "reason": ""},
                            ],
                        },
                    },
                },
                "GEM": {
                    "entries": {
                        "TRIAL|NCT00000001": {
                            "ticker": "AAA", "first_found": "2026-10-16",
                            "status": "ACTIVE",
                        },
                    },
                },
            },
        }
        rows = _junior_section10_history(history)
        promoted = [r for r in rows if r["ticker"] == "AAA"]
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["movement"], "PROMOTED TO GEM")
        self.assertEqual(promoted[0]["found"], "2026-10-10")
        self.assertEqual(promoted[0]["left"], "2026-10-16")
        self.assertEqual(promoted[0]["duration_days"], 6)
        self.assertEqual(promoted[0]["current_stage"], "GEM")
        self.assertEqual(len([r for r in rows if r["ticker"] == "BBB"]), 2)

        history["stages"]["GEM"]["entries"]["TRIAL|NCT00000001"]["ticker"] = "OTHER"
        rows = _junior_section10_history(history)
        self.assertEqual(next(r for r in rows if r["ticker"] == "AAA")["movement"],
                         "PROMOTION NEEDS REVIEW")
        self.assertNotIn("GEM", next(r for r in rows if r["ticker"] == "AAA")["current_stage"])

    def test_section10_gem_exit_risk_warns_without_automatically_selling(self):
        today = date(2026, 10, 17)
        bars = [{
            "date": today - timedelta(days=21 - i),
            "close": 80.0 if i >= 19 else 100.0,
        } for i in range(21)]
        profile = {
            "fresh": True, "date": today - timedelta(days=1),
            "close": 80.0, "sma50": 95.0, "rsi": 75.0,
            "macd": {"bullish": False}, "base": {"support": 90.0},
            "bars": bars,
        }
        record = {
            "PDUFA saved": "2026-10-20", "Source review as of": "2026-10-16",
            "Second SEC source": "https://www.sec.gov/filing",
        }
        event = {"outcome": "CRL", "conflict_flag": "ACTIVE",
                 "new_dilution_flag": "YES",
                 "pdufa_evidence_url": "https://www.fda.gov/decision"}
        runway = {
            "Cash runway (months)": 4.5,
            "Cash runway source": "https://www.sec.gov/cash",
            "Cash runway as of": "2026-09-30",
        }
        checks = _gem_section10_exit_checks(record, event, profile, runway,
                                            today, source_current=False)
        self.assertEqual(len(checks), 12)
        self.assertEqual([c["priority"] for c in checks], list(range(1, 13)))
        self.assertIs(checks[0]["triggered"], True)
        self.assertIs(checks[1]["triggered"], True)
        self.assertIs(checks[2]["triggered"], True)
        self.assertIs(checks[3]["triggered"], True)
        self.assertIs(checks[4]["triggered"], True)
        self.assertIs(checks[5]["triggered"], True)
        self.assertIs(checks[6]["triggered"], True)
        self.assertIs(checks[7]["triggered"], True)
        self.assertIs(checks[8]["triggered"], True)
        self.assertIs(checks[9]["triggered"], True)
        self.assertIsNone(checks[10]["triggered"])  # no fake OHLC / VWAP
        self.assertIs(checks[11]["triggered"], True)  # SEC source review stale

    def test_section10_missing_price_history_does_not_assert_support_or_sma20(self):
        today = date(2026, 10, 17)
        checks = _gem_section10_exit_checks(
            {"Ticker": "TEST"}, {}, {"fresh": False, "bars": []}, {},
            today, source_current=None
        )
        self.assertIsNone(checks[5]["triggered"])
        self.assertIsNone(checks[6]["triggered"])
        self.assertIsNone(checks[7]["triggered"])
        self.assertIsNone(checks[8]["triggered"])
        self.assertIsNone(checks[9]["triggered"])
        self.assertIsNone(checks[10]["triggered"])
        self.assertIs(checks[11]["triggered"], True)
        self.assertTrue(all("url" in c and "next_step" in c for c in checks))

    def test_shared_section10_11_contract_and_separate_gem_policy(self):
        source = (ROOT / "gem_reference_frontend" / "dashboard.js").read_text(
            encoding="utf-8"
        )
        styles = (ROOT / "gem_reference_frontend" / "dashboard.css").read_text(
            encoding="utf-8"
        )
        self.assertIn('"10 · Candidate History — GEM JR → GEM"', source)
        self.assertIn('"10 · Candidate History — GEM"', source)
        self.assertIn('"11 · Alerts / Watchlist"', source)
        common_order = "$" + "{historyCard()}" + "$" + "{alertsCard(r)}" + "$" + "{scansCard()}"
        self.assertEqual(source.count(common_order), 2)
        self.assertIn('class="grid footer gem-footer">' + common_order, source)
        self.assertIn('class="grid footer">' + common_order, source)
        self.assertIn('class="gem-only-controls"', source)
        self.assertIn("PDUFA Exit Policy · GEM only", source)
        self.assertNotIn('gem-footer">' + "$" + "{policyCard()}", source)
        self.assertNotIn("PDUFA policy is configured separately in Section 11", source)
        self.assertIn('if(ev.target.id==="alert-scope")', source)
        self.assertIn('data-tab="WT"', source)
        self.assertIn(".gem-only-controls", styles)
        self.assertIn(".stage-timeline", styles)
        self.assertIn(".shared-alerts", styles)

    def test_gem_candidate_history_retains_exact_scan_observed_periods(self):
        state = {
            "stages": {
                "GEM": {
                    "entries": {
                        "TRIAL|NCT00000002": {
                            "ticker": "TEST", "drug": "Drug 2",
                            "nct_id": "NCT00000002", "status": "ACTIVE",
                            "periods": [
                                {"found": "2026-10-01", "left": "2026-10-03",
                                 "reason": "NO_LONGER_IN_VERIFIED_STAGE_SNAPSHOT"},
                                {"found": "2026-10-10", "left": None, "reason": ""},
                            ],
                        },
                        "TRIAL|NCT00000003": {
                            "ticker": "OTHER", "drug": "Drug 3",
                            "nct_id": "NCT00000003", "status": "LEFT",
                            "periods": [
                                {"found": "2026-10-02", "left": "2026-10-09",
                                 "reason": "PDUFA_EXPIRED"},
                            ],
                        },
                    }
                },
            },
        }
        rows = _gem_history_timeline(state)
        self.assertEqual(len(rows), 3)
        by_trial = [r for r in rows if r["id"] == "TRIAL|NCT00000002"]
        self.assertEqual(
            {r["movement"] for r in by_trial},
            {"LEFT GEM", "RE-ENTERED GEM"}
        )
        self.assertTrue(all(r["ticker"] == "TEST" for r in by_trial))
        self.assertEqual(
            next(r for r in by_trial if r["movement"] == "RE-ENTERED GEM")["found"],
            "2026-10-10"
        )
        self.assertEqual(
            next(r for r in rows if r["id"] == "TRIAL|NCT00000003")["reason"],
            "PDUFA_EXPIRED"
        )
        self.assertEqual(_gem_history_timeline({"stages": {}}), [])

    def test_section12_reports_partial_source_coverage_and_scoped_collector_completion(self):
        import json
        now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            target = Path(root)
            (target / "nightly_scan_report.json").write_text(json.dumps({
                "status": "PARTIAL",
                "updated_at_utc": "2026-10-17T09:00:00+00:00",
                "latest_run_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/123",
                "latest_run_conclusion": None,
                "scope": "CLINICAL_PIPELINE_AND_GEM_JR_COLLECTORS_ONLY",
                "verification": {"all_source_coverage": "NOT_VERIFIED",
                                 "artifact_integrity": "PASS"},
                "missing_required_source_families": ["SEC verification", "FDA dates"],
                "scans": [{
                    "scan": "2", "label": "PIPELINE trial inventory",
                    "collector_status": "COMPLETE", "status": "PARTIAL",
                    "errors_count": 0, "issues": [],
                    "collected_at_utc": "2026-10-17T09:01:00+00:00",
                    "metrics": {"companies_checked": 717},
                }],
            }), encoding="utf-8")
            (target / "overnight_scan_status.json").write_text(json.dumps({
                "status": "PARTIAL", "complete": False,
                "finished_at": "2026-10-11T14:00:00+00:00",
                "missing_required_source_families": ["SEC financing"],
                "source_checks": {
                    "clinical_pipeline": {
                        "status": "COMPLETE",
                        "finished_at": "2026-10-11T14:00:00+00:00",
                        "source_scope": "Company registry recheck",
                        "errors": [], "exit_code": 0,
                    },
                },
            }), encoding="utf-8")
            (target / "gem_scan_block_report.json").write_text(json.dumps({
                "status": "PARTIAL",
                "generated_at_utc": "2026-10-17T09:20:00+00:00",
                "run_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/123",
                "source_verification": "NOT VERIFIED — NOT TRADE READY",
                "blocking_or_review_flags": ["SEC_FINANCING_COVERAGE_BLOCKED_OR_STALE"],
                "acceptance_checks": {
                    "phase3_collector_current": True,
                    "sec_financing_source_current": False,
                },
                "sec_source_health": {
                    "status": "PARTIAL_STALE_OR_BLOCKED",
                    "blocked_records": 38, "last_check_age_days": 12,
                },
                "cash_runway": {"missing_or_stale": 346, "source_backed_pass": 10},
            }), encoding="utf-8")
            rows = scan_diagnostics(root, now=now)
            self.assertEqual(len(rows), 3)
            night, clinical, gem = rows
            self.assertEqual(night["status"], "PARTIAL")
            self.assertEqual(night["freshness"], "CURRENT")
            self.assertEqual(night["coverage"], "NOT_VERIFIED")
            self.assertEqual(night["type"], "review")
            self.assertEqual(night["run_url"],
                             "https://github.com/pdufa/pdufa-command-center/actions/runs/123")
            self.assertEqual(night["details"][0]["status"], "COMPLETE")
            self.assertEqual(night["details"][0]["type"], "review")
            self.assertIn("SEC verification", night["issues"])
            self.assertTrue(any("conclusion" in x for x in night["issues"]))
            self.assertEqual(clinical["freshness"], "STALE")
            self.assertEqual(clinical["type"], "hold")
            self.assertEqual(clinical["details"][0]["type"], "review")
            self.assertEqual(gem["coverage"], "NOT VERIFIED — NOT TRADE READY")
            self.assertEqual(gem["type"], "review")
            self.assertTrue(any("sec financing source current" in x
                                for x in gem["issues"]))
            self.assertTrue(any("SEC financing source" == x["label"] and
                                x["type"] == "hold" for x in gem["details"]))
            self.assertEqual(gem["run_url"],
                             "https://github.com/pdufa/pdufa-command-center/actions/runs/123")

    def test_section12_missing_or_corrupt_reports_are_not_successful(self):
        import json
        now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            reports = scan_diagnostics(root, now=now)
            self.assertEqual(len(reports), 3)
            for r in reports:
                self.assertEqual(r["status"], "UNAVAILABLE")
                self.assertEqual(r["type"], "unknown")
                self.assertEqual(r["freshness"], "UNKNOWN")
                self.assertTrue(r["issues"])
                self.assertEqual(r["run_url"], "")
            (Path(root) / "nightly_scan_report.json").write_text("{broken", encoding="utf-8")
            updated = scan_diagnostics(root, now=now)
            self.assertEqual(updated[0]["status"], "UNAVAILABLE")
            self.assertIn("invalid", updated[0]["issues"][0])

            # A collector-complete snapshot with unverified broader sources
            # must never be displayed as a fully verified scan.
            (Path(root) / "nightly_scan_report.json").write_text(json.dumps({
                "status": "COMPLETE",
                "updated_at_utc": "2026-10-17T11:00:00+00:00",
                "latest_run_url": "https://evil.example.com/actions/runs/123",
                "latest_run_conclusion": "success",
                "verification": {"all_source_coverage": "NOT_VERIFIED",
                                 "artifact_integrity": "PASS"},
                "scans": [],
            }), encoding="utf-8")
            updated = scan_diagnostics(root, now=now)
            self.assertEqual(updated[0]["status"], "COMPLETE")
            self.assertEqual(updated[0]["type"], "review")
            self.assertEqual(updated[0]["run_url"], "")

    def test_section12_source_error_cannot_look_like_a_clean_collector(self):
        import json
        now = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "nightly_scan_report.json").write_text(json.dumps({
                "status": "PARTIAL",
                "updated_at_utc": "2026-10-17T10:00:00+00:00",
                "verification": {"all_source_coverage": "NOT_VERIFIED"},
                "scans": [{
                    "scan": "4", "label": "Phase 3",
                    "collector_status": "COMPLETE", "status": "PARTIAL",
                    "errors_count": 1, "issues": ["source timeout"],
                }],
            }), encoding="utf-8")
            r = scan_diagnostics(root, now=now)[0]
            self.assertEqual(r["details"][0]["status"], "REVIEW — RECORDED ERRORS")
            self.assertEqual(r["details"][0]["type"], "review")
            self.assertIn("source timeout", r["details"][0]["errors"])

    @patch("gem_reference_dashboard.assess_runway", return_value={
        "Cash runway (months)": None, "Cash runway reason": "No audited assessment",
    })
    def test_profile_does_not_invent_financing_terms_or_inherit_sibling_clinical_results(self, runway):
        record = {"Ticker": "TEST", "Pipeline ID": "APPLICATION|TEST|A",
                  "Exact program": "TEST|A", "Drug": "Drug A", "Indication": "Condition A",
                  "NCT ID": "NCT00000001", "Phase 3 status": "PRIMARY_MET_VERIFIED",
                  "Phase 3 date": "2025-01-01", "First close": "2025-02-01",
                  "Second close": "2025-04-01", "First SEC source": "https://www.sec.gov/first",
                  "Second SEC source": "https://www.sec.gov/second"}
        event = {"company": "Test Bio", "reported_p_values": "0.002"}
        profile = {"base": {}, "bars": [], "date": None}
        score = {"entry": None, "exit_risk": None}
        registry = [{"ticker": "TEST", "nct_id": "NCT00000002", "phase": "Phase 3",
                     "drug": "Drug B", "indication": "Condition B", "status": "COMPLETED"}]
        result = _candidate("GEM", (record, event, None, profile, score), "data",
                            date(2026, 10, 15), {}, {}, {}, registry, [])
        self.assertIsNone(result["entry"])
        self.assertEqual(result["financings"][0]["amount"], "—")
        self.assertEqual(result["financings"][1]["warrants"], "—")
        children = {t["nct"]: t for group in result["hierarchy"] for t in group["trials"]}
        self.assertEqual(children["NCT00000001"]["p_value"], "0.002")
        self.assertEqual(children["NCT00000002"]["p_value"], "Not available in saved sources")
        self.assertEqual(children["NCT00000002"]["result"], "COMPLETED")
        self.assertEqual(children["NCT00000002"]["result_type"], "unknown")


if __name__ == "__main__":
    unittest.main()
