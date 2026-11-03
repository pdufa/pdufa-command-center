"""Offline tests for fail-closed official clinical-study source reconciliation."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))
from verify_tools_pool_nct_additions import verify_recent_nct_additions


class ToolsPoolNctAdditionTests(unittest.TestCase):
    def setUp(self):
        self.base = {"NCT01234567"}
        self.added = {"NCT07295847", "NCT07911553"}
        self.live = self.base | self.added
        self.rows = [
            {"id": "TRIAL|NCT01234567", "stage": "Phase 3"},
            {"id": "TRIAL|NCT07295847", "stage": "Phase 1 / 2"},
            {"id": "TRIAL|NCT07911553", "stage": "Phase 3"},
        ]
        self.phases = {"NCT07295847": ["PHASE1", "PHASE2"],
                       "NCT07911553": ["PHASE3"]}

    def official(self, nct):
        return {"protocolSection": {
            "identificationModule": {"nctId": nct},
            "designModule": {"studyType": "INTERVENTIONAL",
                             "phases": self.phases[nct]},
        }}

    def test_genuine_new_ncts_may_join_only_with_official_phase_match(self):
        result = verify_recent_nct_additions(
            self.live, self.base, self.rows, self.official)
        self.assertEqual([r["nctId"] for r in result],
                         ["NCT07295847", "NCT07911553"])
        self.assertTrue(all(r["clinicalTrialsGovUrl"].startswith(
            "https://clinicaltrials.gov/study/NCT") for r in result))

    def test_unchanged_baseline_uses_no_vendor_call(self):
        def no_call(_):
            self.fail("Unneeded official source request")
        result = verify_recent_nct_additions(self.base, self.base,
                                             self.rows, no_call)
        self.assertEqual(result, [])

    def test_missing_baseline_never_automatically_removed(self):
        with self.assertRaisesRegex(ValueError, "MISSING_BASELINE"):
            verify_recent_nct_additions(self.added, self.base,
                                        self.rows, self.official)

    def test_phase_mismatch_is_not_silently_reconciled(self):
        self.rows[2]["stage"] = "Phase 1"
        with self.assertRaisesRegex(ValueError, "PHASE_MISMATCH"):
            verify_recent_nct_additions(self.live, self.base,
                                        self.rows, self.official)

    def test_wrong_issuer_registry_id_and_missing_design_fail(self):
        def wrong(nct):
            v = self.official(nct)
            v["protocolSection"]["identificationModule"]["nctId"] = "NCT00000000"
            return v
        with self.assertRaisesRegex(ValueError, "IDENTITY_OR_DESIGN"):
            verify_recent_nct_additions(self.live, self.base, self.rows, wrong)
        def no_design(nct):
            v = self.official(nct)
            v["protocolSection"]["designModule"]["studyType"] = "OBSERVATIONAL"
            return v
        with self.assertRaisesRegex(ValueError, "IDENTITY_OR_DESIGN"):
            verify_recent_nct_additions(self.live, self.base, self.rows, no_design)

    def test_mass_delta_is_bounded_even_if_http_source_would_respond(self):
        added = {"NCT" + str(i).zfill(8) for i in range(1, 30)}
        rows = self.rows + [{"id": "TRIAL|" + i, "stage": "Phase 1"} for i in added]
        with self.assertRaisesRegex(ValueError, "MASS_ADD_LIMIT"):
            verify_recent_nct_additions(self.base | added,
                                        self.base, rows, self.official)

    def test_duplicate_new_live_identity_refuses_promotion(self):
        rows = self.rows + [dict(self.rows[1])]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_UNVERIFIED"):
            verify_recent_nct_additions(self.live, self.base, rows, self.official)


if __name__ == "__main__":
    unittest.main()
