"""Combine source-reviewed Phase 2 results with Phase 3 PRE-READOUT research.

The observed Phase 2 primary p-value is a mandatory *evidence gate*, not
a 25/25 award and not a probability. Full clinical sub-scores are only emitted
when the pre-readout 100-point research assessment already passed its cutoff,
source-date, trial-identity and issuer-unreleased checks.
"""
import pandas as pd

PHASE2_MAX = 25
PHASE3_MAX = 75

def combine_phase2_phase3(candidates, evidence):
    out = candidates.copy()
    out["Phase 2 Clinical Score /25"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    out["Phase 3 Pre-Readout Score /75"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    out["Combined Pre-Readout Score /100"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    out["Combined Score Status"] = "NOT SCORED — NEEDS PHASE 2 PRIMARY p AND CLINICAL REVIEW"
    if out.empty or evidence is None or evidence.empty or "nct_id" not in evidence:
        return out
    if evidence["nct_id"].astype(str).duplicated().any():
        out["Combined Score Status"] = "REVIEW — DUPLICATE NCT EVIDENCE"
        return out
    source = evidence.set_index("nct_id")
    for idx, item in out.iterrows():
        # This status is set exclusively by the pre-release, complete-source
        # assessor, not by an individual p-value or registry design metadata.
        valid = str(item.get("Assessment Status", "")) == "100-POINT RESEARCH SCORE — UNCALIBRATED"
        total = pd.to_numeric(item.get("Pre-Readout Evidence Points"), errors="coerce")
        if not valid or pd.isna(total):
            continue
        if item.get("Phase 2 p Evidence") != "REPORTED — MANUAL CLINICAL REVIEW":
            out.at[idx, "Combined Score Status"] = "REVIEW — PHASE 2 PRIMARY p NOT VERIFIED BEFORE CUTOFF"
            continue
        nct = str(item.get("NCT ID", ""))
        if nct not in source.index:
            continue
        e = source.loc[nct]
        try:
            p2 = float(e.get("phase2_efficacy_points", ""))
        except (ValueError, TypeError):
            continue
        if not 0 <= p2 <= PHASE2_MAX or not 0 <= total - p2 <= PHASE3_MAX:
            continue
        out.at[idx, "Phase 2 Clinical Score /25"] = p2
        out.at[idx, "Phase 3 Pre-Readout Score /75"] = total - p2
        out.at[idx, "Combined Pre-Readout Score /100"] = total
        out.at[idx, "Combined Score Status"] = "COMBINED RESEARCH SCORE — NOT A PROBABILITY"
    return out
