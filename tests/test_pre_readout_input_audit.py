"""Input-audit controls: source dates, exact identity joins and no outcome leakage."""
import unittest
from datetime import date
import pandas as pd
from pre_readout_input_audit import audit_inputs, INPUTS

DAY = date(2026, 10, 10)
NCT = "NCT12345678"


def candidate(**kw):
    row = {
        "NCT ID": NCT, "Ticker": "BIO", "Drug": "BIO-A",
        "Indication": "Condition X", "Program Identity": "VERIFIED",
        "Source": "https://clinicaltrials.gov/study/" + NCT,
        "Phase 2 NCT Links": "NCT87654321",
    }
    row.update(kw)
    return pd.DataFrame([row])


def protocol(**kw):
    row = {
        "nct_id": NCT, "source_url": "https://clinicaltrials.gov/study/" + NCT,
        "checked_at": "2026-10-10T08:00:00Z", "source_updated": "2026-10-01",
        "primary_endpoint": "Clinical score improvement",
        "primary_timeframe": "Week 24", "allocation": "RANDOMIZED",
        "masking": "NONE", "comparator": "Placebo",
        "enrollment": "400",
    }
    row.update(kw)
    return pd.DataFrame([row])


def manual(**kw):
    row = {
        "nct_id": NCT, "ticker": "BIO", "drug": "BIO-A",
        "indication": "Condition X", "assessment_cutoff_date": "2026-10-10",
        "issuer_readout_status": "VERIFIED_UNRELEASED",
        "issuer_readout_checked_at": "2026-10-10",
        "issuer_readout_source": "https://example.org/issuer-history",
        "actual_topline_release_date": "",
    }
    for name, limit in (("phase2_efficacy", 25), ("safety", 15),
                        ("phase3_design", 30), ("regulatory_alignment", 15)):
        row[name + "_points"] = str(limit)
        row[name + "_source"] = "https://example.org/" + name
        row[name + "_source_date"] = "2026-09-30"
    row.update(kw)
    return pd.DataFrame([row])


class InputAuditTests(unittest.TestCase):
    def test_automatic_protocol_and_phase2_link_are_not_clinical_evidence(self):
        details, coverage = audit_inputs(
            candidate(), protocol(), as_of=DAY,
        )
        row = details.iloc[0]
        self.assertEqual(len(INPUTS), 12)
        self.assertEqual(row["Available Inputs"], 7)
        self.assertEqual(row["Input Coverage %"], 58.3)
        self.assertEqual(coverage["Verified Phase 2 efficacy source"], 0)
        self.assertEqual(coverage["Documented FDA alignment"], 0)
        self.assertEqual(row["Issuer Check"], "NOT VERIFIED")
        self.assertIn("Verified Phase 2 efficacy source", row["Missing Inputs"])
        self.assertNotIn("success probability", " ".join(details.columns).lower())

    def test_manual_sources_fill_all_domains_only_with_matching_identity(self):
        a, _ = audit_inputs(candidate(), protocol(), manual(), as_of=DAY)
        self.assertEqual(a.iloc[0]["Available Inputs"], 12)
        self.assertEqual(a.iloc[0]["Input Coverage %"], 100.0)
        self.assertEqual(a.iloc[0]["Issuer Check"], "CHECKED — ANALYST DOCUMENTED")
        wrong, _ = audit_inputs(candidate(), protocol(), manual(ticker="OTHER"), as_of=DAY)
        self.assertEqual(wrong.iloc[0]["Available Inputs"], 7)

    def test_pre_readout_cutoff_rejects_future_protocol_revisions(self):
        r, _ = audit_inputs(candidate(), protocol(source_updated="2026-10-11"), as_of=DAY)
        self.assertEqual(r.iloc[0]["Available Inputs"], 2)
        old, _ = audit_inputs(candidate(), protocol(checked_at="2026-10-11"), as_of=DAY)
        self.assertEqual(old.iloc[0]["Available Inputs"], 2)

    def test_late_phase2_efficacy_and_issuer_release_block_inputs(self):
        later, _ = audit_inputs(
            candidate(), protocol(),
            manual(phase2_efficacy_source_date="2026-10-11",
                   actual_topline_release_date="2026-10-09"),
            as_of=DAY,
        )
        self.assertEqual(later.iloc[0]["Available Inputs"], 10)
        self.assertEqual(later.iloc[0]["Issuer Check"], "NOT VERIFIED")

    def test_zero_assessed_points_mean_negative_assessment_not_missing_source(self):
        r, _ = audit_inputs(candidate(), protocol(),
                            manual(phase2_efficacy_points="0"), as_of=DAY)
        self.assertEqual(r.iloc[0]["Available Inputs"], 12)

    def test_future_historical_cutoff_cannot_use_current_protocol_or_manual_sources(self):
        d, _ = audit_inputs(
            candidate(), protocol(), manual(), as_of=date(2026, 10, 1),
        )
        self.assertEqual(d.iloc[0]["Available Inputs"], 2)
        self.assertIn("Issuer's unreleased topline checked", d.iloc[0]["Missing Inputs"])

    def test_empty_sources_make_missing_explicit(self):
        d, counts = audit_inputs(candidate(), None, None, as_of=DAY)
        self.assertEqual(len(d), 1)
        self.assertEqual(d.iloc[0]["Available Inputs"], 2)
        self.assertEqual(sum(counts.values()), 2)

    def test_hindsight_future_release_date_cannot_count_as_pre_readout_issuer_check(self):
        r, _ = audit_inputs(
            candidate(), protocol(),
            manual(actual_topline_release_date="2026-10-11"), as_of=DAY,
        )
        self.assertEqual(r.iloc[0]["Issuer Check"], "NOT VERIFIED")
        self.assertEqual(r.iloc[0]["Available Inputs"], 11)
        stale, _ = audit_inputs(
            candidate(), protocol(),
            manual(issuer_readout_checked_at="2026-10-09"), as_of=DAY,
        )
        self.assertEqual(stale.iloc[0]["Issuer Check"], "NOT VERIFIED")



if __name__ == "__main__":
    unittest.main()
