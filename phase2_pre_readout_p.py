"""Attach published earlier Phase 2 primary-p evidence to pre-readout queue.

Never scores the p-value or infers efficacy / Phase 3 probability. Exact NCT,
ticker and publication timestamp gates prevent cross-program contamination.
"""
import re
from datetime import date
import pandas as pd

COLUMNS = ["Phase 2 Primary p Recorded", "Phase 2 Primary p Values",
           "Phase 2 Primary p Sources", "Phase 2 p Published By"]


def attach_phase2_p(queue, evidence, as_of):
    out = queue.copy()
    for name in COLUMNS:
        out[name] = ""
    if out.empty or evidence is None or evidence.empty:
        return out
    cutoff = date.fromisoformat(str(as_of)[:10])
    needed = {"phase3_nct_id", "phase2_nct_id", "ticker", "result_first_posted", "p_value", "source_url"}
    if not needed.issubset(evidence.columns):
        return out
    grouped = {}
    for _, e in evidence.iterrows():
        p3 = str(e.get("phase3_nct_id", "")).strip()
        p2 = str(e.get("phase2_nct_id", "")).strip()
        ticker = str(e.get("ticker", "")).strip().upper()
        posted = str(e.get("result_first_posted", "")).strip()[:10]
        url = str(e.get("source_url", "")).strip()
        pval = str(e.get("p_value", "")).strip()
        try:
            in_time = date.fromisoformat(posted) < cutoff
        except ValueError:
            in_time = False
        if not (re.fullmatch(r"NCT\d{8}", p3) and re.fullmatch(r"NCT\d{8}", p2)
                and p2 != p3 and in_time and url == "https://clinicaltrials.gov/study/" + p2
                and pval and pval.lower() not in {"nan", "none"}):
            continue
        grouped.setdefault((p3, ticker), []).append((pval, url, posted))
    for idx, row in out.iterrows():
        key = (str(row.get("NCT ID", "")).strip(), str(row.get("Ticker", "")).strip().upper())
        entries = grouped.get(key, [])
        if not entries:
            continue
        out.at[idx, "Phase 2 Primary p Recorded"] = "YES — NOT ADJUDICATED"
        out.at[idx, "Phase 2 Primary p Values"] = " | ".join(sorted({r[0] for r in entries}))
        out.at[idx, "Phase 2 Primary p Sources"] = " | ".join(sorted({r[1] for r in entries}))
        out.at[idx, "Phase 2 p Published By"] = max(r[2] for r in entries)
    return out
