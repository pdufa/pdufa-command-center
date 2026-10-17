"""Reference-image GEM page contract: source data, ranked controls and disclosures."""
import unittest
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_visual_page import _show, _rankings
from gem_reference_dashboard import resolve_dashboard_action, _candidate, _all_company_trials, _hierarchy, _junior_section8_checks

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
