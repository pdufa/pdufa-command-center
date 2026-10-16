"""Reference-image GEM page contract: source data, ranked controls and disclosures."""
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_visual_page import _show, _rankings
from gem_reference_dashboard import resolve_dashboard_action, _candidate

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
        self.assertEqual(children["NCT00000002"]["p_value"], "—")
        self.assertEqual(children["NCT00000002"]["result"], "COMPLETED")
        self.assertEqual(children["NCT00000002"]["result_type"], "unknown")


if __name__ == "__main__":
    unittest.main()
