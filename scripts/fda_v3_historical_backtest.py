#!/usr/bin/env python3
"""Decision-safe FDA-V3 historical benchmark and backfill queue.

This does NOT claim a full FDA-V3 backtest until every historical row has
decision-safe FDA-review inputs. It reports:
1) legacy baseline accuracy,
2) directional accuracy/coverage where a preserved public pre-decision call exists,
3) an explicit queue for rows still needing FDA-V3 historical evidence backfill,
4) diagnostic miss classes that are never fed back into pre-decision predictions.

Typical runtime: under 3 seconds for the current 146-row cohort.
"""

import json
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HISTORY = DATA / "prediction_engine_history.csv"
OUT = DATA / "fda_v3_historical_backtest.csv"
QUEUE = DATA / "fda_v3_historical_backfill_queue.csv"
SUMMARY = DATA / "fda_v3_historical_summary.json"

def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none","<na>"} else s

def normalize(v):
    s = clean(v).upper()
    if "APPROV" in s:
        return "APPROVED"
    if "CRL" in s or "COMPLETE RESPONSE" in s or "REJECT" in s or "DECLIN" in s:
        return "CRL"
    if s == "REVIEW":
        return "REVIEW"
    return ""

def diagnostic_miss_class(row):
    if str(row.get("correct")).lower() != "false":
        return ""
    text = " ".join([
        clean(row.get("public_evidence_note")),
        clean(row.get("internal_direction_note")),
    ]).lower()
    if re.search(r"manufactur|inspection|cmc|cgmp|facility|nonclinical deficiency", text):
        return "CMC_INSPECTION"
    if re.search(r"efficacy|statistic|endpoint|substantial evidence|generalizability|replication|confirmatory|dose lacked", text):
        return "EFFICACY_STATISTICS"
    if re.search(r"safety|benefit-risk|toxicity|tolerability", text):
        return "SAFETY_BENEFIT_RISK"
    if re.search(r"resubmission|remediation|prior crl", text):
        return "RESUBMISSION_REMEDIATION"
    return "OTHER_UNCLEAR"

def main():
    h = pd.read_csv(HISTORY, keep_default_na=False)
    h["actual_norm"] = h["actual_outcome"].apply(normalize)
    h["public_call"] = h["public_model_class"].apply(normalize)
    h["legacy_correct_bool"] = h["correct"].astype(str).str.lower().map({"true": True, "false": False})

    h["v3_phase_a_status"] = h["public_call"].apply(
        lambda x: "DIRECTIONAL_CALL" if x in {"APPROVED","CRL"} else ("REVIEW_NO_CALL" if x == "REVIEW" else "NEEDS_V3_BACKFILL")
    )
    h["v3_phase_a_match"] = h.apply(
        lambda r: "MATCH" if r["public_call"] in {"APPROVED","CRL"} and r["public_call"] == r["actual_norm"]
        else ("MISS" if r["public_call"] in {"APPROVED","CRL"} else "NO_CALL"),
        axis=1
    )
    h["diagnostic_miss_class"] = h.apply(diagnostic_miss_class, axis=1)
    h["historical_v3_backfill_needed"] = ~h["public_call"].isin(["APPROVED","CRL"])

    # Prioritize old misses and independent holdouts first because they are most useful
    # for calibrating FDA-V3 without contaminating prospective logic.
    def priority(r):
        if r["public_call"] in {"APPROVED","CRL"}:
            return "COMPLETE_PHASE_A"
        if clean(r.get("independence_status")) == "EXTERNAL_HOLDOUT":
            return "P1_EXTERNAL_HOLDOUT"
        if str(r.get("correct")).lower() == "false":
            return "P2_LEGACY_MISS"
        if clean(r.get("validation_period")).startswith("2024_"):
            return "P3_2024_VALIDATION"
        if clean(r.get("validation_period")).startswith("2023_"):
            return "P4_2023_TUNING"
        return "P5_REMAINING_HISTORY"

    h["v3_backfill_priority"] = h.apply(priority, axis=1)

    cols = [
        "event_key","ticker","pdufa_date","actual_outcome","model_class","p_approval",
        "correct","validation_period","independence_status","public_model_class",
        "public_approval_probability","v3_phase_a_status","v3_phase_a_match",
        "historical_v3_backfill_needed","v3_backfill_priority","diagnostic_miss_class",
        "public_evidence_note","internal_direction_note"
    ]
    h[cols].to_csv(OUT, index=False)

    queue = h[h["historical_v3_backfill_needed"]].copy()
    qcols = [
        "event_key","ticker","pdufa_date","actual_outcome","validation_period",
        "independence_status","v3_backfill_priority","diagnostic_miss_class",
        "public_evidence_note","internal_direction_note"
    ]
    queue[qcols].to_csv(QUEUE, index=False)

    scored = h[h["legacy_correct_bool"].notna()]
    legacy_correct = int(scored["legacy_correct_bool"].sum())
    directional = h[h["public_call"].isin(["APPROVED","CRL"])]
    dir_correct = int((directional["public_call"] == directional["actual_norm"]).sum())
    ext = h[h["independence_status"].eq("EXTERNAL_HOLDOUT")]
    ext_dir = ext[ext["public_call"].isin(["APPROVED","CRL"])]
    ext_correct = int((ext_dir["public_call"] == ext_dir["actual_norm"]).sum())

    miss_counts = h.loc[h["legacy_correct_bool"].eq(False), "diagnostic_miss_class"].value_counts().to_dict()
    summary = {
        "cohort_rows": int(len(h)),
        "legacy_scored_rows": int(len(scored)),
        "legacy_correct": legacy_correct,
        "legacy_accuracy_pct": round(100 * legacy_correct / len(scored), 2) if len(scored) else None,
        "phase_a_public_directional_calls": int(len(directional)),
        "phase_a_public_directional_correct": dir_correct,
        "phase_a_public_directional_match_pct": round(100 * dir_correct / len(directional), 2) if len(directional) else None,
        "phase_a_public_directional_coverage_pct": round(100 * len(directional) / len(h), 2) if len(h) else None,
        "phase_a_review_no_call": int((h["public_call"] == "REVIEW").sum()),
        "historical_v3_backfill_remaining": int(h["historical_v3_backfill_needed"].sum()),
        "external_holdout_rows": int(len(ext)),
        "external_holdout_directional_calls": int(len(ext_dir)),
        "external_holdout_directional_correct": ext_correct,
        "external_holdout_directional_match_pct": round(100 * ext_correct / len(ext_dir), 2) if len(ext_dir) else None,
        "external_holdout_directional_coverage_pct": round(100 * len(ext_dir) / len(ext), 2) if len(ext) else None,
        "legacy_miss_diagnostic_counts": miss_counts,
        "warning": "Phase A is a preserved decision-safe public-call benchmark, not the full FDA-V3 backtest. Full V3 accuracy remains pending historical FDA-discipline backfill."
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
