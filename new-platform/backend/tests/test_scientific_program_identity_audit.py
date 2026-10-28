"""Scientific exact-trial program identity preflight regression tests."""
import unittest
from app.scientific_program_identity_audit import audit_exact_programs


def row(program, source, cohorts):
    return {"program_id": program, "source_key": source, "cohorts": cohorts}


class ProgramIdentityAuditTest(unittest.TestCase):
    def test_requires_actual_exact_nct_for_scientific_dossier(self):
        result = audit_exact_programs([
            row("PDUFA-000071", "APPLICATION|EXAMPLE|2020-08-03|drug", ["WT"]),
            row("PDUFA-000076", "RESULT|EXAMPLE|2020-02-21|drug", ["WT", "GEM"]),
            row("PDUFA-010001", "TRIAL|NCT02142738", ["GEM_JR", "GEM"]),
        ])
        self.assertEqual(result["programs_checked"], 3)
        self.assertEqual(result["exact_trial_identity_links"], 1)
        self.assertEqual(result["unlinked_programs"], 2)
        self.assertEqual(result["cohort_coverage"]["WT"],
                         {"programs": 2, "linked": 0, "unlinked": 2})
        self.assertEqual(result["cohort_coverage"]["GEM"],
                         {"programs": 2, "linked": 1, "unlinked": 1})
        self.assertEqual(result["linked"][0]["nct_id"], "NCT02142738")
        self.assertEqual(result["manual_crosswalk_queue"][0]["nct_id"], None)
        self.assertFalse(result["automated_mapping_performed"])
        self.assertFalse(result["scientific_scores_assigned"])
        self.assertFalse(result["cohort_preset_modified"])
        self.assertIsNone(result["fda_approval_probability"])

    def test_same_program_multiple_cohorts_dedupes_without_changing_identity(self):
        a = row("PDUFA-000101", "TRIAL|NCT04280705", ["GEM_JR"])
        b = row("PDUFA-000101", "TRIAL|NCT04280705", ["GEM", "WT"])
        result = audit_exact_programs([a, b])
        self.assertEqual(result["programs_checked"], 1)
        self.assertEqual(result["linked"][0]["cohorts"], ["WT", "GEM", "GEM_JR"])

    def test_unverified_application_mapping_is_never_accepted(self):
        application = row("PDUFA-000071", "APPLICATION|EXAMPLE|drug", ["WT"])
        application["nct_id"] = "NCT02636699"
        with self.assertRaises(ValueError):
            audit_exact_programs([application])

    def test_trial_with_conflicting_nct_or_program_source_fails_closed(self):
        a = row("PDUFA-000101", "TRIAL|NCT04280705", ["WT"])
        with self.assertRaises(ValueError):
            audit_exact_programs([a, {**a, "nct_id": "NCT02142738"}])
        with self.assertRaises(ValueError):
            audit_exact_programs([a, {**a, "source_key": "TRIAL|NCT02142738"}])

    def test_malformed_member_and_source_identity_rejected(self):
        valid = row("PDUFA-000101", "TRIAL|NCT04280705", ["WT"])
        failures = [
            {"program_id": "ticker-only"},
            {"source_key": ""},
            {"cohorts": []},
            {"cohorts": ["WT", "WT"]},
            {"cohorts": ["PIPELINE"]},
            {"nct_id": "NCT1"},
            {"nct_id": "NCT02142738"},
        ]
        for override in failures:
            with self.subTest(override=override), self.assertRaises(ValueError):
                audit_exact_programs([{**valid, **override}])

    def test_blank_audit_does_not_imply_scientific_readiness(self):
        result = audit_exact_programs([])
        self.assertEqual(result["programs_checked"], 0)
        self.assertEqual(result["exact_trial_identity_links"], 0)
        self.assertFalse(result["scientific_scores_assigned"])

    def test_nontrial_source_key_never_creates_automatic_link(self):
        r = audit_exact_programs([
            row("PDUFA-000071", "APPLICATION|DBVT|2020-08-03|viaskin-peanut", ["WT"]),
            row("PDUFA-000076", "APPLICATION|ESPR|2020-02-21|bempedoic-acid", ["WT"]),
        ])
        self.assertEqual(r["cohort_coverage"]["WT"]["unlinked"], 2)
        self.assertEqual(r["cohort_coverage"]["WT"]["linked"], 0)
        self.assertEqual([x["source_type"] for x in r["manual_crosswalk_queue"]],
                         ["APPLICATION", "APPLICATION"])


if __name__ == "__main__":
    unittest.main()
