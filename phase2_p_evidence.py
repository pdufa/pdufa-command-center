"""Source-dated Phase 2 primary p-value evidence linked to pre-readout Phase 3 trials.

Informational inputs only: individual p-values do not establish Phase 2 clinical
success, predict Phase 3 success, or calibrate probability of success.
Only exact Phase 2 NCT IDs linked from the Phase 3 trial are eligible.
"""
from datetime import date
import re
import pandas as pd

COLUMNS = (
    "Phase 2 p Evidence",
    "Phase 2 Primary p-values (research only)",
    "Phase 2 p Source",
    "Phase 2 Registry Results Posted",
    "Phase 2 p First Verified",
    "Days Since Phase 2 p Verification",
)

def _day(value):
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (TypeError, ValueError):
        return None

def join_phase2_p(queue, observations, *, as_of):
    """Attach dated, exact-trial linked primary analyses, never score from p alone."""
    result = queue.copy()
    for col in COLUMNS:
        result[col] = "" if col != "Days Since Phase 2 p Verification" else pd.NA
    if result.empty:
        return result
    cutoff = _day(as_of)
    if cutoff is None:
        raise ValueError("Explicit pre-readout cutoff is required")
    if observations is None or observations.empty:
        result["Phase 2 p Evidence"] = "NOT COLLECTED"
        return result
    required = {"nct_id", "ticker", "p_value", "observed_at_utc",
                "results_first_posted", "source_url", "primary_endpoint"}
    if not required.issubset(observations.columns):
        result["Phase 2 p Evidence"] = "NOT COLLECTED"
        return result
    p = observations.fillna("").copy()
    matches = {}
    for _, row in p.iterrows():
        nct = str(row.get("nct_id", "")).strip().upper()
        if not re.fullmatch(r"NCT\d{8}", nct):
            continue
        first_post = _day(row.get("results_first_posted"))
        observed = _day(row.get("observed_at_utc"))
        # Registry posting may predate p-values. First observation is the
        # defensible "known by" date; do not backdate this to first posting.
        if (not first_post or not observed or first_post > cutoff or
                observed > cutoff or first_post > observed):
            continue
        if str(row.get("source_url", "")).strip() != "https://clinicaltrials.gov/study/" + nct:
            continue
        if not str(row.get("primary_endpoint", "")).strip():
            continue
        matches.setdefault(nct, []).append(row)
    for idx, item in result.iterrows():
        phase2_ids = set(re.findall(r"NCT\d{8}", str(item.get("Phase 2 NCT Links", "")).upper()))
        if not phase2_ids:
            result.at[idx, "Phase 2 p Evidence"] = "NO LINKED PHASE 2 NCT"
            continue
        tick = str(item.get("Ticker", "")).strip().upper()
        # Ticker plus an explicitly stored Phase 2 NCT relation are both
        # mandatory. This still needs manual drug/indication equivalence review.
        eligible = [r for nct in sorted(phase2_ids) for r in matches.get(nct, [])
                    if str(r.get("ticker", "")).strip().upper() == tick
                    and str(r.get("p_value", "")).strip()]
        if not eligible:
            result.at[idx, "Phase 2 p Evidence"] = "NO VERIFIED PRIMARY p"
            continue
        eligible.sort(key=lambda x: (str(x.get("observed_at_utc","")),
                                     str(x.get("nct_id","")), str(x.get("primary_endpoint",""))))
        # Limit display while retaining source for a full independent review.
        labels = []
        seen = set()
        for r in eligible:
            label = (str(r["nct_id"]) + ": " +
                     str(r.get("primary_endpoint", "")).strip()[:75] + " p" +
                     str(r.get("p_value_modifier", "=")).strip().replace("LT", "<").replace("GT", ">").replace("EQ", "=") +
                     str(r["p_value"]).strip())
            if label not in seen:
                labels.append(label)
                seen.add(label)
        result.at[idx, "Phase 2 p Evidence"] = "REPORTED — MANUAL CLINICAL REVIEW"
        result.at[idx, "Phase 2 Primary p-values (research only)"] = " | ".join(labels[:8])
        result.at[idx, "Phase 2 p Source"] = str(eligible[0]["source_url"])
        result.at[idx, "Phase 2 Registry Results Posted"] = min(str(r["results_first_posted"])[:10] for r in eligible)
        verified = min(_day(r["observed_at_utc"]) for r in eligible)
        result.at[idx, "Phase 2 p First Verified"] = verified.isoformat()
        result.at[idx, "Days Since Phase 2 p Verification"] = (cutoff - verified).days
    return result
