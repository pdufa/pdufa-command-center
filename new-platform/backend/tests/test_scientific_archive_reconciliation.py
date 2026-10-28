"""Offline science cohort -> exact archived source reconciliation tests."""
import unittest

from app.scientific_archive_reconciliation import reconcile_sources


def program(pid, source, cohorts):
    return {"program_id": pid, "source_key": source, "cohorts": cohorts}


def archive(nct, *, sha="a", results=True, pvalue="REPORTED", phases=None):
    return {
        "nct_id": nct,
        "phases": phases if phases is not None else ["PHASE3"],
        "has_posted_results": results,
        "p_value_status": pvalue,
        "source_sha256": sha * 64,
    }


class ScientificArchiveReconciliationTest(unittest.TestCase):
    def test_application_only_wt_yields_manual_queue_not_invented_nct(self):
        rows = [
            program("PDUFA-000071", "APPLICATION|DBVT|2020-08-03|viaskin-peanut", ["WT"]),
            program("PDUFA-000076", "APPLICATION|ESPR|2020-02-21|bempedoic-acid", ["WT"]),
        ]
        audit = reconcile_sources(rows, [])
        self.assertEqual(audit["identity_audit"]["unlinked_programs"], 2)
        self.assertEqual(audit["exact_identity_source_matched_programs"], 0)
        self.assertIsNone(audit["proposed_plan"])
        self.assertFalse(audit["import_executed"])
        self.assertFalse(audit["independent_scientific_review_complete"])
        self.assertIsNone(audit["fda_approval_probability"])

    def test_only_exact_archived_nct_is_proposed_and_missing_stays_missing(self):
        programs = [
            program("PDUFA-000101", "TRIAL|NCT02142738", ["GEM_JR", "GEM"]),
            program("PDUFA-000102", "TRIAL|NCT04280705", ["WT"]),
            program("PDUFA-000103", "APPLICATION|EXAMPLE|Drug", ["WT"]),
        ]
        result = reconcile_sources(programs, [archive("NCT02142738")])
        self.assertEqual(result["exact_identity_source_matched_programs"], 1)
        self.assertEqual(len(result["exact_identity_source_missing_programs"]), 1)
        self.assertEqual(result["exact_identity_source_missing_programs"][0]["nct_id"],
                         "NCT04280705")
        self.assertEqual(result["proposed_plan"]["unique_trials"], 1)
        self.assertEqual(result["proposed_plan"]["trials"][0]["cohorts"], ["GEM", "GEM_JR"])
        self.assertEqual(result["proposed_plan"]["planned_batches"][0]["nct_ids"],
                         ["NCT02142738"])
        self.assertFalse(result["proposed_plan"]["import_executed"])

    def test_same_exact_nct_multiple_programs_dedupes_trial_import(self):
        programs = [
            program("PDUFA-000101", "TRIAL|NCT02142738", ["GEM_JR"]),
            program("PDUFA-000102", "TRIAL|NCT02142738", ["GEM", "WT"]),
        ]
        r = reconcile_sources(programs, [archive("NCT02142738")])
        self.assertEqual(r["exact_identity_source_matched_programs"], 2)
        self.assertEqual(r["proposed_plan"]["unique_trials"], 1)
        self.assertEqual(r["proposed_plan"]["trials"][0]["cohorts"], ["WT", "GEM", "GEM_JR"])

    def test_contradictory_digest_rejected_before_plan_is_issued(self):
        programs = [program("PDUFA-000101", "TRIAL|NCT02142738", ["GEM"])]
        with self.assertRaises(ValueError):
            reconcile_sources(programs, [archive("NCT02142738"),
                                         archive("NCT02142738", sha="b")])
        with self.assertRaises(ValueError):
            reconcile_sources(programs, [archive("NCT02142738", sha="bad")])

    def test_malformed_archive_and_inferred_application_link_fail_closed(self):
        p = program("PDUFA-000071", "APPLICATION|EXAMPLE|drug", ["WT"])
        with self.assertRaises(ValueError):
            reconcile_sources([{**p, "nct_id": "NCT02142738"}], [])
        with self.assertRaises(ValueError):
            reconcile_sources([], [{"nct_id": "NCTinvalid"}])
        with self.assertRaises(ValueError):
            reconcile_sources([], [42])
        with self.assertRaises(ValueError):
            reconcile_sources([], ["NCT02142738"])


if __name__ == "__main__":
    unittest.main()
