"""Safety and quantification tests for the merged SCANS control center."""
import json
import unittest
from unittest.mock import patch, Mock

from unified_scans_command_center import (
    numbers, tally_source, reasons, workflow_request, dispatch_section,
    collect_cards, recent_active,
)


class ScoreSemanticsTests(unittest.TestCase):
    def test_100_only_with_real_nonzero_denominator(self):
        self.assertEqual(numbers(45, 45), 100.0)
        self.assertEqual(numbers(740, 762), 97.1)
        self.assertIsNone(numbers(None, 1))
        self.assertIsNone(numbers(0, None))
        self.assertIsNone(numbers(0, 0))
        self.assertIsNone(numbers(8, 7))

    def test_verified_not_applicable_and_unavailable_are_separate(self):
        sec = tally_source({"findings_due": 762, "findings_verified": 740,
                            "findings_not_applicable": 0,
                            "required_findings_unresolved": 22})
        self.assertEqual(sec["score"], 97.1)
        self.assertEqual(sec["outstanding"], 22)
        financial = tally_source({"findings_due": 89, "findings_verified": 78,
                                  "findings_not_applicable": 10,
                                  "required_findings_unresolved": 1})
        self.assertEqual(financial["score"], 98.9)
        self.assertEqual(financial["not_applicable"], 10)
        self.assertEqual(financial["outstanding"], 1)
        market = tally_source({"findings_due": 180, "findings_verified": 87,
                               "optional_findings_unavailable": 93})
        self.assertEqual(market["score"], 48.3)
        self.assertEqual(market["outstanding"], 93)
        why = " ".join(reasons("MARKET", market))
        self.assertIn("93", why)
        self.assertIn("supplemental", why)

    def test_missing_gem_baseline_is_not_fake_100_percent(self):
        clinical = {"scans": [
            {"scan": "2", "collector_status": "COMPLETE",
             "metrics": {"tracked_trials_checked": 9751, "tracked_trials_total": 9751}},
            {"scan": "4", "collector_status": "COMPLETE",
             "metrics": {"studies_checked": 3989, "matched_posted_results": 99}}]}
        sources = {"status": "PARTIAL", "sources": []}
        gem = {"observed_phase3_rows": 2487, "two_benchmark_candidate_count": 6,
               "strict_entry_gate_shortlist_count": 0}
        result = {item["name"]: item for item in collect_cards(clinical, sources, gem)}
        self.assertEqual(result["PIPELINE"]["score"], 100)
        self.assertTrue(any("PARTIAL" in x for x in result["PIPELINE"]["reasons"]))
        self.assertIsNone(result["GEM JR"]["score"])
        self.assertIsNone(result["GEM"]["score"])
        self.assertIn("6", str(result["GEM"]["details"]["Potential two-benchmark candidates"]))

    def test_standalone_result_does_not_silently_rewrite_source_aggregate(self):
        older = {"updated_at_utc": "2026-10-17T09:20:00Z", "sources": [{
            "source": "SEC", "findings_due": 100, "findings_verified": 90,
            "required_findings_unresolved": 10}]}
        item = {"schema_version": 1, "source": "SEC", "run_id": 11,
                "published_at_utc": "2026-10-17T12:00:00Z",
                "findings_due": 120, "findings_verified": 115,
                "required_findings_unresolved": 5}
        sec = next(x for x in collect_cards({}, older, {}, standalone={"SEC": item})
                   if x["name"] == "SEC")
        self.assertEqual(sec["checked"], 115)
        self.assertEqual(sec["source_run_id"], 11)
        self.assertIn("Standalone", sec["details"]["Evidence scope"])
        self.assertEqual(older["sources"][0]["findings_verified"], 90)


class DispatchRoutingTests(unittest.TestCase):
    def test_each_section_maps_to_a_real_specific_workflow(self):
        self.assertEqual(workflow_request("PIPELINE", "FULL"),
                         ("pdufa-nightly-clinical.yml", {"scan": "PIPELINE", "scan_mode": "FULL"}))
        self.assertEqual(workflow_request("GEM JR", "DELTA"),
                         ("pdufa-nightly-clinical.yml", {"scan": "GEM_JR", "scan_mode": "DELTA"}))
        self.assertEqual(workflow_request("GEM", "FULL"),
                         ("gem-research-quality.yml", {"action": "RESCAN_ALL"}))
        for source in ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"):
            workflow, args = workflow_request(source, "DELTA")
            self.assertEqual(workflow, "pdufa-individual-source-scan.yml")
            self.assertEqual(args["source"], source)
        self.assertEqual(workflow_request("SCAN HEALTH", "DELTA"),
                         ("pdufa-adhoc-error-check.yml", {}))
        self.assertEqual(workflow_request("SCAN ALL", "FULL"),
                         ("pdufa-overnight-sequential.yml", {
                             "scan_mode": "FULL", "gem_action": "RESCAN_ALL"}))
        with self.assertRaises(ValueError):
            workflow_request("GEM; evil", "FULL")
        with self.assertRaises(ValueError):
            workflow_request("GEM", "NO")

    def test_real_post_sent_only_on_explicit_dispatch(self):
        response = Mock()
        response.status = 204
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("unified_scans_command_center.urllib.request.urlopen",
                   return_value=response) as open_call:
            dispatch_section("SEC", "DELTA", "synthetic-token")
        request = open_call.call_args.args[0]
        self.assertTrue(request.full_url.endswith(
            "/actions/workflows/pdufa-individual-source-scan.yml/dispatches"))
        self.assertEqual(json.loads(request.data), {
            "ref": "main", "inputs": {"source": "SEC", "scan_mode": "DELTA"}})
        self.assertEqual(request.get_method(), "POST")

    def test_duplicate_guard_avoids_queued_matching_stage(self):
        runs = [{"status": "queued", "path": ".github/workflows/pdufa-individual-source-scan.yml",
                 "display_title": "SEC — individual PDUFA source scan"}]
        self.assertIsNotNone(recent_active(runs, "SEC"))
        self.assertIsNone(recent_active(runs, "FDA"))


if __name__ == "__main__":
    unittest.main()
