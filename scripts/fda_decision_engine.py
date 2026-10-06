#!/usr/bin/env python3
"""FDA-like decision engine for the PDUFA Command Center.

Purpose
-------
Keep regulatory prediction separate from trading setup. This engine consumes
only regulatory/clinical evidence fields and persistent FDA-review overrides.
It never uses market cap, price, momentum, short interest, IV, financing,
ownership, or other trading variables.

The engine is intentionally conservative. Missing critical FDA-review
disciplines produce REVIEW rather than a forced APPROVED/CRL call.

Usage
-----
python scripts/fda_decision_engine.py
python scripts/fda_decision_engine.py --freeze
python scripts/fda_decision_engine.py --event-key 'TICKER|EVENT'

Typical runtime: under 5 seconds for the current saved candidate feed.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CANDIDATES = DATA / "pdufa_candidates.csv"
REVIEWS = DATA / "fda_review_engine.csv"
FREEZES = DATA / "fda_prediction_freezes.csv"
BACKFILL = DATA / "fda_review_backfill_queue.csv"
CONFIG = DATA / "fda_engine_config.json"

REVIEW_COLUMNS = [
    "event_key","ticker","drug","pdufa_date",
    "fda_regulatory_case_id","fda_count_in_match",
    "fda_application_identity",
    "fda_clinical_score","fda_statistics_score","fda_meaningfulness_score",
    "fda_safety_score","fda_clinical_pharmacology_score","fda_nonclinical_score",
    "fda_cmc_score","fda_inspection_status","fda_regulatory_score",
    "fda_labeling_score","fda_benefit_risk_score",
    "fda_evidence_freshness","fda_hard_gate","fda_probability",
    "fda_prediction","fda_confidence","fda_gate_reason",
    "fda_model_version","fda_prediction_frozen_at","fda_last_evaluated_at",
    "decision_date","actual_fda_decision","fda_match_result","fda_source_note"
]

FREEZE_COLUMNS = [
    "freeze_id","event_key","ticker","drug","pdufa_date","fda_regulatory_case_id","evidence_cutoff",
    "fda_probability","fda_prediction","fda_confidence","fda_hard_gate",
    "fda_gate_reason","frozen_at","model_version","decision_date",
    "actual_fda_decision","match_result"
]

BACKFILL_COLUMNS = [
    "event_key","ticker","drug","pdufa_date","priority","days_to_pdufa",
    "missing_components","backfill_status","source_targets","decision_date",
    "actual_fda_decision","notes"
]

SCORE_FIELDS = {
    "clinical": "fda_clinical_score",
    "statistics": "fda_statistics_score",
    "clinical_meaningfulness": "fda_meaningfulness_score",
    "safety": "fda_safety_score",
    "clinical_pharmacology": "fda_clinical_pharmacology_score",
    "nonclinical": "fda_nonclinical_score",
    "cmc": "fda_cmc_score",
    "regulatory": "fda_regulatory_score",
    "labeling": "fda_labeling_score",
    "benefit_risk": "fda_benefit_risk_score",
}

TRADING_FIELDS_PROHIBITED = {
    "market_cap","market_cap_bucket","price_last","return_30d_pct","avg_volume_20d",
    "short_interest","short_ratio","shares_float","institutional_ownership_pct",
    "iv_30d","trade_score","financing_status","financing_close_date",
    "financing_proceeds","new_dilution_flag","cash","cash_runway_months"
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan","none","<na>"} else text


def score(value):
    try:
        if value is None or pd.isna(value) or clean(value) == "":
            return None
        x = float(value)
        if 0 <= x <= 1:
            x *= 100.0
        return max(0.0, min(100.0, x))
    except Exception:
        return None


def normalize_outcome(value):
    value = clean(value).upper()
    if "APPROV" in value:
        return "APPROVED"
    if "CRL" in value or "COMPLETE RESPONSE" in value or "REJECT" in value or "DECLIN" in value:
        return "CRL"
    return ""


def load_config():
    with CONFIG.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path, columns=None):
    if path.exists():
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        frame = pd.DataFrame(columns=columns or [])
    if columns:
        for col in columns:
            if col not in frame:
                frame[col] = ""
        frame = frame[columns]
    return frame


def seed_review(candidate, prior):
    row = {c: clean(prior.get(c)) for c in REVIEW_COLUMNS}
    row["event_key"] = clean(candidate.get("event_key"))
    row["ticker"] = clean(candidate.get("ticker"))
    row["drug"] = clean(candidate.get("drug"))
    row["pdufa_date"] = clean(candidate.get("pdufa_date"))
    if clean(row.get("fda_regulatory_case_id")) == "":
        row["fda_regulatory_case_id"] = clean(candidate.get("event_key"))
    if clean(row.get("fda_count_in_match")) == "":
        row["fda_count_in_match"] = "YES"
    row["decision_date"] = clean(candidate.get("decision_date"))
    row["actual_fda_decision"] = normalize_outcome(candidate.get("outcome"))

    # Seed only from pre-existing regulatory/clinical score fields.
    # New FDA disciplines remain UNKNOWN until evidence is deliberately backfilled.
    seed_map = {
        "fda_clinical_score": "science_score",
        "fda_safety_score": "safety_score",
        "fda_cmc_score": "cmc_score",
        "fda_regulatory_score": "regulatory_score",
    }
    for dst, src in seed_map.items():
        if clean(row.get(dst)) == "":
            v = score(candidate.get(src))
            row[dst] = "" if v is None else f"{v:.1f}"

    if clean(row.get("fda_application_identity")) == "":
        pstatus = clean(candidate.get("pdufa_confirmation")).upper()
        purl = clean(candidate.get("pdufa_evidence_url"))
        if purl and ("VERIFIED" in pstatus or "CONFIRMED" in pstatus):
            row["fda_application_identity"] = "PASS"
        elif purl:
            row["fda_application_identity"] = "REVIEW"
        else:
            row["fda_application_identity"] = "UNKNOWN"

    if clean(row.get("fda_inspection_status")) == "":
        row["fda_inspection_status"] = "UNKNOWN"
    if clean(row.get("fda_evidence_freshness")) == "":
        row["fda_evidence_freshness"] = "UNKNOWN"

    return row


def evaluate(row, cfg):
    reasons = []
    fail_reasons = []
    unknown_reasons = []
    pass_min = float(cfg["hard_gates"]["critical_score_pass_min"])
    fail_max = float(cfg["hard_gates"]["critical_score_fail_max"])

    identity = clean(row.get("fda_application_identity")).upper()
    if identity == "FAIL":
        fail_reasons.append("application/review-cycle identity failed")
    elif identity != "PASS":
        unknown_reasons.append("application/review-cycle identity not verified")

    inspection = clean(row.get("fda_inspection_status")).upper()
    if inspection == "FAIL":
        fail_reasons.append("manufacturing/facility inspection gate failed")
    elif inspection != "PASS":
        unknown_reasons.append("inspection status unknown")

    values = {name: score(row.get(col)) for name, col in SCORE_FIELDS.items()}

    for critical in ["safety","cmc","regulatory"]:
        v = values[critical]
        if v is None:
            unknown_reasons.append(f"{critical} score missing")
        elif v <= fail_max:
            fail_reasons.append(f"{critical} hard gate failed ({v:.0f})")
        elif v < pass_min:
            unknown_reasons.append(f"{critical} hard gate not strong enough ({v:.0f})")

    for required in ["clinical","statistics","clinical_meaningfulness","benefit_risk"]:
        if values[required] is None:
            unknown_reasons.append(f"{required} score missing")

    freshness = clean(row.get("fda_evidence_freshness")).upper()
    if freshness == "FAIL":
        fail_reasons.append("evidence freshness/cutoff failed")
    elif freshness not in {"PASS","FROZEN"}:
        unknown_reasons.append("decision-safe evidence freshness not verified")

    if fail_reasons:
        hard_gate = "FAIL"
    elif unknown_reasons:
        hard_gate = "REVIEW"
    else:
        hard_gate = "PASS"

    probability = None
    if hard_gate == "PASS":
        weighted = 0.0
        used_weight = 0.0
        for name, weight in cfg["weights"].items():
            v = values.get(name)
            if v is None:
                continue
            w = float(weight)
            weighted += v * w
            used_weight += w
        if used_weight > 0:
            probability = weighted / used_weight

    approved_min = float(cfg["directional_thresholds"]["approved_min_probability"])
    crl_max = float(cfg["directional_thresholds"]["crl_max_probability"])

    if hard_gate == "FAIL":
        prediction = "CRL"
        confidence = "HARD-GATE FAIL"
    elif hard_gate != "PASS" or probability is None:
        prediction = "REVIEW"
        confidence = "INSUFFICIENT FDA EVIDENCE"
    elif probability >= approved_min:
        prediction = "APPROVED"
        confidence = "HIGH"
    elif probability <= crl_max:
        prediction = "CRL"
        confidence = "HIGH"
    else:
        prediction = "REVIEW"
        confidence = "ABSTAIN FOR ACCURACY"

    reasons = fail_reasons + unknown_reasons
    if not reasons:
        reasons = ["all required FDA-like review gates passed"]

    row["fda_hard_gate"] = hard_gate
    row["fda_probability"] = "" if probability is None else f"{probability:.1f}"
    row["fda_prediction"] = prediction
    row["fda_confidence"] = confidence
    row["fda_gate_reason"] = " | ".join(dict.fromkeys(reasons))
    row["fda_model_version"] = clean(cfg.get("model_version")) or "FDA-V3.0"
    row["fda_last_evaluated_at"] = utc_now()

    actual = normalize_outcome(row.get("actual_fda_decision"))
    decision_date = clean(row.get("decision_date"))
    if actual and decision_date:
        if prediction in {"APPROVED","CRL"}:
            row["fda_match_result"] = "MATCH" if prediction == actual else "MISS"
        else:
            row["fda_match_result"] = "NO CALL"
    else:
        row["fda_match_result"] = "PENDING"

    return row


def freeze_rows(review, candidates, cfg):
    freezes = load_csv(FREEZES, FREEZE_COLUMNS)
    existing = set(freezes["event_key"].astype(str) + "|" + freezes["model_version"].astype(str))
    new_rows = []
    cand_by_key = {clean(r["event_key"]): r for _, r in candidates.iterrows()}

    for _, r in review.iterrows():
        key = clean(r.get("event_key"))
        model = clean(r.get("fda_model_version"))
        if clean(r.get("fda_prediction")) not in {"APPROVED","CRL"}:
            continue
        if clean(r.get("fda_hard_gate")) != "PASS":
            continue
        if clean(r.get("decision_date")):
            continue
        sig = key + "|" + model
        if sig in existing:
            continue

        c = cand_by_key.get(key, {})
        frozen_at = utc_now()
        freeze_id = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_") + "_" + model.replace(".", "_")
        new_rows.append({
            "freeze_id": freeze_id,
            "event_key": key,
            "ticker": clean(r.get("ticker")),
            "drug": clean(r.get("drug")),
            "pdufa_date": clean(r.get("pdufa_date")),
            "fda_regulatory_case_id": clean(r.get("fda_regulatory_case_id")),
            "evidence_cutoff": clean(c.get("evidence_cutoff")),
            "fda_probability": clean(r.get("fda_probability")),
            "fda_prediction": clean(r.get("fda_prediction")),
            "fda_confidence": clean(r.get("fda_confidence")),
            "fda_hard_gate": clean(r.get("fda_hard_gate")),
            "fda_gate_reason": clean(r.get("fda_gate_reason")),
            "frozen_at": frozen_at,
            "model_version": model,
            "decision_date": "",
            "actual_fda_decision": "",
            "match_result": "PENDING",
        })

    if new_rows:
        freezes = pd.concat([freezes, pd.DataFrame(new_rows)], ignore_index=True)
        freezes = freezes[FREEZE_COLUMNS]
        freezes.to_csv(FREEZES, index=False)

        frozen_map = {x["event_key"]: x["frozen_at"] for x in new_rows}
        for i in review.index:
            key = clean(review.at[i, "event_key"])
            if key in frozen_map:
                review.at[i, "fda_prediction_frozen_at"] = frozen_map[key]

    return review, len(new_rows)


def write_backfill_queue(review):
    today = pd.Timestamp(datetime.now(timezone.utc).date())
    checks = [
        ("application_identity","fda_application_identity",lambda v: clean(v).upper() != "PASS"),
        ("clinical","fda_clinical_score",lambda v: score(v) is None),
        ("statistics","fda_statistics_score",lambda v: score(v) is None),
        ("clinical_meaningfulness","fda_meaningfulness_score",lambda v: score(v) is None),
        ("safety","fda_safety_score",lambda v: score(v) is None),
        ("clinical_pharmacology","fda_clinical_pharmacology_score",lambda v: score(v) is None),
        ("nonclinical_toxicology","fda_nonclinical_score",lambda v: score(v) is None),
        ("cmc_product_quality","fda_cmc_score",lambda v: score(v) is None),
        ("manufacturing_inspection","fda_inspection_status",lambda v: clean(v).upper() != "PASS"),
        ("regulatory_history","fda_regulatory_score",lambda v: score(v) is None),
        ("labeling","fda_labeling_score",lambda v: score(v) is None),
        ("benefit_risk","fda_benefit_risk_score",lambda v: score(v) is None),
        ("evidence_freshness","fda_evidence_freshness",lambda v: clean(v).upper() not in {"PASS","FROZEN"}),
    ]
    rows = []
    for _, r in review.iterrows():
        pdate = pd.to_datetime(r.get("pdufa_date"), errors="coerce")
        days = None if pd.isna(pdate) else int((pd.Timestamp(pdate).normalize() - today).days)
        if days is None:
            priority = "P4 DATE UNKNOWN"
        elif days < 0:
            priority = "P0 PAST / CLOSURE"
        elif days <= 30:
            priority = "P1 0-30 DAYS"
        elif days <= 60:
            priority = "P2 31-60 DAYS"
        elif days <= 90:
            priority = "P3 61-90 DAYS"
        else:
            priority = "P4 >90 DAYS"

        missing = [name for name, col, test in checks if test(r.get(col))]
        closed = bool(clean(r.get("decision_date")) and normalize_outcome(r.get("actual_fda_decision")))
        rows.append({
            "event_key": clean(r.get("event_key")),
            "ticker": clean(r.get("ticker")),
            "drug": clean(r.get("drug")),
            "pdufa_date": clean(r.get("pdufa_date")),
            "priority": priority,
            "days_to_pdufa": "" if days is None else str(days),
            "missing_components": " | ".join(missing),
            "backfill_status": "CLOSED_DECIDED" if closed else ("NEEDS_BACKFILL" if missing else "READY_FOR_ENGINE"),
            "source_targets": "FDA/Drugs@FDA review documents | FDA action/CRL source | ClinicalTrials.gov | issuer/SEC application evidence",
            "decision_date": clean(r.get("decision_date")),
            "actual_fda_decision": normalize_outcome(r.get("actual_fda_decision")),
            "notes": (
                "No further prospective pursuit; retained for calibration/audit."
                if closed else
                "Backfill only decision-safe evidence that predates the actual FDA action."
            ),
        })
    pd.DataFrame(rows, columns=BACKFILL_COLUMNS).to_csv(BACKFILL, index=False)


def reconcile_freezes(review):
    if not FREEZES.exists():
        return
    freezes = load_csv(FREEZES, FREEZE_COLUMNS)
    review_by_key = {clean(r["event_key"]): r for _, r in review.iterrows()}
    changed = False
    for i, fr in freezes.iterrows():
        r = review_by_key.get(clean(fr["event_key"]))
        if r is None:
            continue
        actual = normalize_outcome(r.get("actual_fda_decision"))
        decision_date = clean(r.get("decision_date"))
        if not actual or not decision_date:
            continue
        pred = clean(fr.get("fda_prediction")).upper()
        result = "MATCH" if pred == actual else "MISS"
        if clean(fr.get("decision_date")) != decision_date:
            freezes.at[i, "decision_date"] = decision_date
            changed = True
        if clean(fr.get("actual_fda_decision")) != actual:
            freezes.at[i, "actual_fda_decision"] = actual
            changed = True
        if clean(fr.get("match_result")) != result:
            freezes.at[i, "match_result"] = result
            changed = True
    if changed:
        freezes.to_csv(FREEZES, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-key", action="append", default=[])
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    candidates = load_csv(CANDIDATES)
    prior = load_csv(REVIEWS, REVIEW_COLUMNS)
    prior_by_key = {clean(r["event_key"]): r for _, r in prior.iterrows()}

    rows = []
    wanted = set(args.event_key)
    for _, candidate in candidates.iterrows():
        key = clean(candidate.get("event_key"))
        if wanted and key not in wanted:
            # Preserve untouched rows for partial runs.
            if key in prior_by_key:
                rows.append({c: clean(prior_by_key[key].get(c)) for c in REVIEW_COLUMNS})
            continue
        seeded = seed_review(candidate, prior_by_key.get(key, {}))
        rows.append(evaluate(seeded, cfg))

    review = pd.DataFrame(rows, columns=REVIEW_COLUMNS)
    if args.freeze:
        review, frozen = freeze_rows(review, candidates, cfg)
    else:
        frozen = 0

    review.to_csv(REVIEWS, index=False)
    reconcile_freezes(review)
    write_backfill_queue(review)

    calls = review["fda_prediction"].value_counts().to_dict() if not review.empty else {}
    print(json.dumps({
        "rows": int(len(review)),
        "calls": calls,
        "new_freezes": int(frozen),
        "model_version": cfg.get("model_version"),
        "trading_fields_used": [],
        "prohibited_trading_fields": sorted(TRADING_FIELDS_PROHIBITED),
    }, indent=2))


if __name__ == "__main__":
    main()
