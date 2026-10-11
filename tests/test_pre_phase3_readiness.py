"""Auditable PRE PHASE 3 completion gates, not post-P3 entry rules."""
import unittest

from pre_phase3_readiness import check_pre_phase3_readiness, SOURCES


def inputs():
    checks = [{"Source": name, "Health": "RECENT",
               "Last checked UTC": "2026-10-10T19:00:00Z"} for name in SOURCES]
    checks.append({"Source": "SEC financing recheck", "Health": "BLOCKED / PARTIAL"})
    manifest = {"source_checks": checks}
    trials = [{"Trial phase":"Phase 3", "Phase 2 PRIMARY evidence count":1,
               "Pre-readout research score /100":82.0,
               "Score status":"100-POINT RESEARCH SCORE — UNCALIBRATED",
               "ENTRY READY":"NO — NOT VERIFIED"}]
    protocol = {"active_registry_unposted_phase3_trials": 1,
                "protocol_records_stored": 1,
                "uncollected_trials": 0, "errors":{},
                "status":"COMPLETE"}
    phase2 = {"linked_unique_phase2_nct":1, "phase2_nct_queried_this_run":1,
              "unattempted_linked_nct":0, "errors":{}, "status":"COMPLETE"}
    return manifest, trials, protocol, phase2


class ReadinessTests(unittest.TestCase):
    def test_clinical_ready_is_not_post_phase3_entry_ready(self):
        result = check_pre_phase3_readiness(*inputs())
        self.assertEqual(result["status"], "READY FOR FINAL BROWSER ACCEPTANCE")
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["live_scored_pilots"], 1)
        self.assertNotIn("SEC financing recheck feed", [x["Requirement"] for x in result["checks"]])
        self.assertNotIn("ENTRY READY", result["status"])

    def test_unreviewed_clinical_scores_block_completion(self):
        manifest,trials,protocol,phase2 = inputs()
        trials[0]["Pre-readout research score /100"] = None
        result = check_pre_phase3_readiness(manifest,trials,protocol,phase2)
        self.assertEqual(result["status"], "BLOCKED — NOT COMPLETE")
        self.assertIn("Live source-reviewed pre-readout scoring pilot",result["blocked"])

    def test_scope_warnings_missing_protocol_and_futureless_feeds_are_not_done(self):
        manifest,trials,protocol,phase2 = inputs()
        manifest["source_checks"][0]["Health"] = "RECENT WITH WARNINGS"
        protocol["uncollected_trials"] = 1
        phase2["unattempted_linked_nct"] = 1
        result = check_pre_phase3_readiness(manifest,trials,protocol,phase2)
        self.assertIn("Clinical trial pipeline feed", result["blocked"])
        self.assertIn("Active Phase 3 protocol coverage", result["blocked"])
        self.assertIn("Exact-linked Phase 2 collector coverage", result["blocked"])

    def test_empty_manifest_never_defaults_to_complete(self):
        result = check_pre_phase3_readiness({}, [])
        self.assertGreater(len(result["blocked"]), 0)
        self.assertTrue(all(c["Status"] in ("PASS", "BLOCKED") for c in result["checks"]))

    def test_no_linked_primary_p_observation_not_reclassified_as_failed_phase2(self):
        manifest,trials,protocol,phase2=inputs()
        trials[0]["Phase 2 PRIMARY evidence count"]=0
        result=check_pre_phase3_readiness(manifest,trials,protocol,phase2)
        self.assertIn("Phase 2 p provenance in dashboard",result["blocked"])
        self.assertNotIn("failed trial",result["status"].lower())


if __name__ == "__main__":
    unittest.main()
