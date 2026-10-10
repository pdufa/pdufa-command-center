"""A pre-readout input is not clinical efficacy or a calibrated PoS."""
import unittest
from datetime import date
import pandas as pd
from pre_readout_readiness import audit_inputs

CUTOFF = date(2026, 10, 10)


def sample_queue():
    return pd.DataFrame([{
        "NCT ID": "NCT12345678",
        "Program Identity": "VERIFIED",
        "Phase 2 NCT Links": "NCT87654321",
        "Pre-Readout Evidence Points": pd.NA,
    }])


def design():
    return pd.DataFrame([{
        "NCT ID": "NCT12345678",
        "Coverage": "PROTOCOL PARTIAL",
        "Primary Endpoints": "Change in symptoms at week 24",
        "Allocation": "RANDOMIZED",
        "Masking": "NONE",
        "Enrollment": "440",
    }])


def evidence(**fields):
    row = {
        "nct_id": "NCT12345678",
        "assessment_cutoff_date": "2026-10-10",
        "issuer_readout_status": "VERIFIED_UNRELEASED",
        "issuer_readout_checked_at": "2026-10-10",
        "issuer_readout_source": "https://issuer.example.com/investors",
        "actual_topline_release_date": "",
        "phase2_efficacy_points": "20",
        "phase2_efficacy_source": "https://issuer.example.com/phase2",
        "phase2_efficacy_source_date": "2026-09-01",
    }
    row.update(fields)
    return pd.DataFrame([row])


class PreReadoutReadinessTests(unittest.TestCase):
    def row(self, table, label):
        return table.loc[table["Pre-readout input"].eq(label)].iloc[0]

    def test_blank_evidence_cannot_be_represented_as_clinical_probability(self):
        table = audit_inputs(sample_queue(), design(), pd.DataFrame(), CUTOFF)
        self.assertEqual(int(self.row(table, "Prospective protocol design records")["Present"]), 1)
        self.assertEqual(int(self.row(table, "Earlier Phase 2 trial IDs linked")["Present"]), 1)
        self.assertEqual(int(self.row(table, "Phase 2 efficacy analysis source-dated")["Present"]), 0)
        self.assertEqual(int(self.row(table, "Clinical safety assessment source-dated")["Present"]), 0)
        self.assertEqual(int(self.row(table, "Independently calibrated Phase 3 probability")["Present"]), 0)
        self.assertEqual(int(self.row(table, "Independently calibrated Phase 3 probability")["Missing"]), 1)

    def test_analyst_input_requires_original_dated_source(self):
        good = audit_inputs(sample_queue(), design(), evidence(), CUTOFF)
        self.assertEqual(int(self.row(good, "Phase 2 efficacy analysis source-dated")["Present"]), 1)
        self.assertEqual(int(self.row(good, "Issuer topline absence checked today (analyst entry)")["Present"]), 1)

        late = audit_inputs(sample_queue(), design(), evidence(phase2_efficacy_source_date="2026-10-11"), CUTOFF)
        self.assertEqual(int(self.row(late, "Phase 2 efficacy analysis source-dated")["Present"]), 0)

        stale = audit_inputs(sample_queue(), design(), evidence(issuer_readout_checked_at="2026-10-09"), CUTOFF)
        self.assertEqual(int(self.row(stale, "Issuer topline absence checked today (analyst entry)")["Present"]), 0)

    def test_post_readout_issuer_check_is_not_pre_readout_evidence(self):
        table = audit_inputs(sample_queue(), design(), evidence(actual_topline_release_date="2026-10-09"), CUTOFF)
        self.assertEqual(int(self.row(table, "Issuer topline absence checked today (analyst entry)")["Present"]), 0)

    def test_absent_candidates_show_zeros_without_divide_by_zero(self):
        table = audit_inputs(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), CUTOFF)
        self.assertTrue(table["Present"].eq(0).all())
        self.assertTrue(table["Missing"].eq(0).all())

    def test_enrollment_presence_is_numeric_and_masking_none_is_described(self):
        table = audit_inputs(sample_queue(), design(), pd.DataFrame(), CUTOFF)
        self.assertEqual(int(self.row(table, "Trial enrollment recorded")["Present"]), 1)
        self.assertEqual(int(self.row(table, "Blinding/masking described")["Present"]), 1)
        bad = design()
        bad.loc[0, "Enrollment"] = "unreported"
        bad_table = audit_inputs(sample_queue(), bad, pd.DataFrame(), CUTOFF)
        self.assertEqual(int(self.row(bad_table, "Trial enrollment recorded")["Present"]), 0)


if __name__ == "__main__":
    unittest.main()
