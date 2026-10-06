#!/usr/bin/env python3
"""Build the precision-first FDA 100-on-100 bucket.

This module does NOT replace the forced-direction engine.
It qualifies only strict FDA-V3 APPROVED/CRL calls and abstains on REVIEW/NO_CALL.

Historical rows are retrospective audits, not blind validation.
Prospective accuracy is scored only after a frozen qualified case receives an FDA decision.

Typical runtime: under 5 seconds for the current repository data.
"""

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HIST_IN = DATA / "fda_v3_historical_backtest.csv"
LIVE_IN = DATA / "fda_directional_100pct_live.csv"
PROMOTIONS_IN = DATA / "fda_100_on_100_verified_promotions.csv"
HIST_OUT = DATA / "fda_100_on_100_historical.csv"
LIVE_OUT = DATA / "fda_100_on_100_live.csv"
SUMMARY_OUT = DATA / "fda_100_on_100_summary.json"

MODEL_VERSION = "FDA-100-ON-100-GATE-V1"
VALID_DIRS = {"APPROVED", "CRL"}

def build_historical(df: pd.DataFrame, promotions: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        public_call = str(r.get("public_model_class", "")).strip().upper()
        recon_call = str(r.get("v3_reconstructed_call", "")).strip().upper()
        if public_call in VALID_DIRS:
            call, source = public_call, "PHASE_A_PUBLIC"
        elif recon_call in VALID_DIRS:
            call, source = recon_call, "V3_RECONSTRUCTED"
        else:
            continue
        actual = str(r.get("actual_outcome", "")).strip().upper()
        rows.append({
            "event_key": r.get("event_key", ""),
            "ticker": r.get("ticker", ""),
            "pdufa_date": r.get("pdufa_date", ""),
            "qualified_direction": call,
            "actual_outcome": actual,
            "match_result": "MATCH" if call == actual else "MISS",
            "source_layer": source,
            "status": "RETROSPECTIVE_NOT_BLIND",
        })
    out = pd.DataFrame(rows)
    if promotions is not None and not promotions.empty:
        lookup = df.set_index("event_key", drop=False)
        extra = []
        existing = set(out["event_key"]) if not out.empty else set()
        for _, p in promotions.iterrows():
            event_key = str(p.get("event_key", "")).strip()
            call = str(p.get("qualified_direction", "")).strip().upper()
            if not event_key or call not in VALID_DIRS or event_key in existing or event_key not in lookup.index:
                continue
            r = lookup.loc[event_key]
            actual = str(r.get("actual_outcome", "")).strip().upper()
            extra.append({
                "event_key": event_key,
                "ticker": r.get("ticker", ""),
                "pdufa_date": r.get("pdufa_date", ""),
                "qualified_direction": call,
                "actual_outcome": actual,
                "match_result": "MATCH" if call == actual else "MISS",
                "source_layer": "VERIFIED_PREDECISION_PROMOTION",
                "status": "RETROSPECTIVE_NOT_BLIND",
            })
        if extra:
            out = pd.concat([out, pd.DataFrame(extra)], ignore_index=True)
    return out

def build_live(df: pd.DataFrame) -> pd.DataFrame:
    out = df[
        (df["count_in_coverage"].astype(str).str.upper() == "YES")
        & (df["strict_v3_prediction"].astype(str).str.upper().isin(VALID_DIRS))
    ].copy()
    if out.empty:
        return pd.DataFrame(columns=[
            "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
            "qualified_direction","strict_v3_hard_gate","evidence_completeness_pct",
            "decision_date","actual_fda_decision","match_result","status"
        ])
    out["qualified_direction"] = out["strict_v3_prediction"].astype(str).str.upper()
    out["status"] = "PROSPECTIVE_PENDING"
    decided = out["actual_fda_decision"].astype(str).str.upper().isin(VALID_DIRS)
    out.loc[decided, "status"] = "PROSPECTIVE_DECIDED"
    cols = [
        "event_key","fda_regulatory_case_id","ticker","drug","pdufa_date",
        "qualified_direction","strict_v3_hard_gate","evidence_completeness_pct",
        "decision_date","actual_fda_decision","match_result","status"
    ]
    return out[cols]

def main():
    hist = pd.read_csv(HIST_IN)
    live = pd.read_csv(LIVE_IN)
    promotions = pd.read_csv(PROMOTIONS_IN) if PROMOTIONS_IN.exists() else pd.DataFrame()

    h = build_historical(hist, promotions)
    l = build_live(live)

    h.to_csv(HIST_OUT, index=False)
    l.to_csv(LIVE_OUT, index=False)

    h_matches = int((h["match_result"] == "MATCH").sum()) if len(h) else 0
    decided_mask = l["actual_fda_decision"].astype(str).str.upper().isin(VALID_DIRS) if len(l) else pd.Series(dtype=bool)
    decided = l[decided_mask].copy() if len(l) else l
    p_matches = int((decided["qualified_direction"] == decided["actual_fda_decision"].astype(str).str.upper()).sum()) if len(decided) else 0

    summary = {
        "model_version": MODEL_VERSION,
        "principle": "Precision-first abstaining gate; strict FDA-V3 directional calls only.",
        "historical_qualified": int(len(h)),
        "historical_matches": h_matches,
        "historical_accuracy_pct": round(100*h_matches/len(h), 2) if len(h) else None,
        "historical_total_reviewed": int(len(hist)),
        "historical_coverage_pct": round(100*len(h)/len(hist), 2) if len(hist) else None,
        "historical_validation_status": "RETROSPECTIVE_NOT_BLIND",
        "live_counted_cases": int((live["count_in_coverage"].astype(str).str.upper() == "YES").sum()),
        "live_qualified": int(len(l)),
        "live_coverage_pct": round(100*len(l)/max(1, int((live["count_in_coverage"].astype(str).str.upper() == "YES").sum())), 2),
        "live_decided_scored": int(len(decided)),
        "live_decided_matches": p_matches,
        "prospective_accuracy_pct": round(100*p_matches/len(decided), 2) if len(decided) else None,
        "future_guarantee": False,
        "note": "A historical 100% subset does not guarantee future FDA outcomes. Prospective accuracy is reported only after frozen qualified cases are decided."
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
