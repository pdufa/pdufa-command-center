#!/usr/bin/env python3
"""Track PDUFA extensions as review-cycle state transitions.

An FDA extension is NOT a final outcome. This ledger preserves the prior target
date, records the revised target date/reason, and keeps the review cycle open
until FDA issues APPROVED or CRL.

Typical runtime: under 3 seconds for the current saved feed.
"""

from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CANDIDATES = DATA / "pdufa_candidates.csv"
REVIEWS = DATA / "fda_review_engine.csv"
SIGNALS = DATA / "fda_regulatory_signal_monitor.csv"
DIRECTIONAL = DATA / "fda_directional_100pct_live.csv"
OUT = DATA / "fda_pdufa_extension_ledger.csv"

COLUMNS = [
    "ledger_id","event_key","fda_regulatory_case_id","count_in_coverage",
    "ticker","drug","extension_sequence","prior_pdufa_date","current_pdufa_date",
    "extension_status","extension_reason","extension_detected_at",
    "strict_v3_prediction","forced_direction","directional_model_version",
    "decision_date","actual_fda_decision","source_note","last_updated_at",
]

def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none","<na>"} else s

def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def load(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def case_id(row):
    return clean(row.get("fda_regulatory_case_id")) or clean(row.get("event_key"))

def choose_representatives(review):
    if review.empty:
        return review
    x = review.copy()
    x["_case"] = x.apply(case_id, axis=1)
    x["_count_rank"] = x.get("fda_count_in_match", "").astype(str).str.upper().eq("YES").astype(int)
    x = x.sort_values(["_case","_count_rank"], ascending=[True,False])
    return x.drop_duplicates("_case", keep="first").drop(columns=["_case","_count_rank"])

def main():
    cand = load(CANDIDATES)
    review = choose_representatives(load(REVIEWS))
    signals = load(SIGNALS)
    directional = load(DIRECTIONAL)
    ledger = load(OUT)

    for col in COLUMNS:
        if col not in ledger:
            ledger[col] = ""
    ledger = ledger[COLUMNS] if not ledger.empty else pd.DataFrame(columns=COLUMNS)

    cand_by_event = {clean(r.get("event_key")): r for _, r in cand.iterrows()} if not cand.empty else {}
    sig_by_event = {clean(r.get("event_key")): r for _, r in signals.iterrows()} if not signals.empty else {}
    dir_by_event = {clean(r.get("event_key")): r for _, r in directional.iterrows()} if not directional.empty else {}

    now = now_utc()
    new_rows = []

    for _, r in review.iterrows():
        event = clean(r.get("event_key"))
        case = case_id(r)
        c = cand_by_event.get(event, {})
        sg = sig_by_event.get(event, {})
        dr = dir_by_event.get(event, {})

        current_date = clean(c.get("pdufa_date")) or clean(r.get("pdufa_date"))
        decision_date = clean(r.get("decision_date")) or clean(c.get("decision_date"))
        actual = clean(r.get("actual_fda_decision")) or clean(c.get("outcome"))
        count_flag = clean(r.get("fda_count_in_match")) or "YES"
        extension_known = clean(sg.get("review_extension_status")).upper() == "YES"
        extension_reason = clean(sg.get("extension_reason")) or "NONE"
        source_note = clean(sg.get("source_note")) or clean(r.get("fda_source_note"))

        prior = ledger[ledger["fda_regulatory_case_id"].astype(str).eq(case)].copy()
        if not prior.empty:
            prior["_seq"] = pd.to_numeric(prior["extension_sequence"], errors="coerce").fillna(0)
            prior = prior.sort_values(["_seq","last_updated_at"])
            latest = prior.iloc[-1]
            latest_date = clean(latest.get("current_pdufa_date"))
            seq = int(float(latest.get("_seq", 0)))
        else:
            latest = None
            latest_date = ""
            seq = -1

        if latest is None:
            seq = 1 if extension_known else 0
            status = "RESOLVED" if (decision_date and actual) else (
                "EXTENDED_PENDING" if extension_known else "OPEN_PENDING"
            )
            new_rows.append({
                "ledger_id": f"{case}|{seq}|{current_date or 'NO_DATE'}",
                "event_key": event,
                "fda_regulatory_case_id": case,
                "count_in_coverage": count_flag,
                "ticker": clean(r.get("ticker")),
                "drug": clean(r.get("drug")),
                "extension_sequence": str(seq),
                "prior_pdufa_date": "",
                "current_pdufa_date": current_date,
                "extension_status": status,
                "extension_reason": extension_reason if extension_known else "NONE",
                "extension_detected_at": now if extension_known else "",
                "strict_v3_prediction": clean(r.get("fda_prediction")) or "REVIEW",
                "forced_direction": clean(dr.get("forced_direction")),
                "directional_model_version": clean(dr.get("model_version")),
                "decision_date": decision_date,
                "actual_fda_decision": actual,
                "source_note": source_note,
                "last_updated_at": now,
            })
            continue

        # Date changed without a final FDA action: treat as a new extension
        # snapshot, preserving the old target date in the previous row.
        if current_date and latest_date and current_date != latest_date and not (decision_date and actual):
            seq += 1
            new_rows.append({
                "ledger_id": f"{case}|{seq}|{current_date}",
                "event_key": event,
                "fda_regulatory_case_id": case,
                "count_in_coverage": count_flag,
                "ticker": clean(r.get("ticker")),
                "drug": clean(r.get("drug")),
                "extension_sequence": str(seq),
                "prior_pdufa_date": latest_date,
                "current_pdufa_date": current_date,
                "extension_status": "EXTENDED_PENDING",
                "extension_reason": extension_reason if extension_reason != "NONE" else "UNKNOWN",
                "extension_detected_at": now,
                "strict_v3_prediction": clean(r.get("fda_prediction")) or "REVIEW",
                "forced_direction": clean(dr.get("forced_direction")),
                "directional_model_version": clean(dr.get("model_version")),
                "decision_date": "",
                "actual_fda_decision": "",
                "source_note": source_note,
                "last_updated_at": now,
            })
        else:
            # Refresh latest cycle metadata in place.
            idx = prior.index[-1]
            ledger.at[idx, "strict_v3_prediction"] = clean(r.get("fda_prediction")) or "REVIEW"
            ledger.at[idx, "forced_direction"] = clean(dr.get("forced_direction"))
            ledger.at[idx, "directional_model_version"] = clean(dr.get("model_version"))
            ledger.at[idx, "source_note"] = source_note
            ledger.at[idx, "last_updated_at"] = now
            if extension_known and clean(ledger.at[idx, "extension_reason"]) in {"","NONE","UNKNOWN"}:
                ledger.at[idx, "extension_reason"] = extension_reason
            if decision_date and actual:
                ledger.at[idx, "extension_status"] = "RESOLVED"
                ledger.at[idx, "decision_date"] = decision_date
                ledger.at[idx, "actual_fda_decision"] = actual

    if new_rows:
        ledger = pd.concat([ledger, pd.DataFrame(new_rows)], ignore_index=True)

    if not ledger.empty:
        ledger = ledger.drop_duplicates("ledger_id", keep="last")
        ledger["_seq"] = pd.to_numeric(ledger["extension_sequence"], errors="coerce").fillna(0)
        ledger = ledger.sort_values(["fda_regulatory_case_id","_seq","last_updated_at"]).drop(columns=["_seq"])
    ledger.to_csv(OUT, index=False)

    print({
        "rows": len(ledger),
        "extended_pending": int((ledger["extension_status"] == "EXTENDED_PENDING").sum()) if not ledger.empty else 0,
        "resolved": int((ledger["extension_status"] == "RESOLVED").sum()) if not ledger.empty else 0,
    })

if __name__ == "__main__":
    main()
