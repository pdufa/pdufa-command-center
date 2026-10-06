#!/usr/bin/env python3
"""Join recorded historical directions with strict qualification, without rescoring.

Every broad call keeps its original model version and direction. Actual outcomes
are used only to compute MATCH/MISS after the recorded direction is selected.
Runtime: under 3 seconds for the current cohort.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VALID_DIRECTIONS = {"APPROVED", "CRL"}


def clean(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def indexed(frame, name):
    if "event_key" not in frame:
        raise ValueError(f"{name}: missing event_key")
    keys = frame["event_key"].map(clean)
    if keys.eq("").any() or keys.duplicated().any():
        raise ValueError(f"{name}: blank or duplicate event_key")
    return {clean(row["event_key"]): row for _, row in frame.iterrows()}


def broad_reason(row):
    source = clean(row.get("source_layer"))
    call = clean(row.get("forced_direction"))
    score = clean(row.get("fallback_probability"))
    if source == "FROZEN_MODEL_FORCE":
        return f"Recorded model baseline {score}%; 50% threshold gives {call}. Strict evidence remains incomplete."
    reasons = {
        "FDA_DOMAIN_RISK_OVERRIDE": "Clinical/regulatory/CMC risk rule overrides the baseline direction.",
        "EVENT_RISK_OVERRIDE": "Late-cycle regulatory risk rule overrides the baseline direction.",
        "VERIFIED_REMEDIATION_OVERRIDE": "Verified prior-deficiency remediation rule overrides the baseline direction.",
        "STRICT_V3_RECONSTRUCTION": "Recorded FDA-V3 reconstruction from public evidence.",
        "STRICT_V3_PUBLIC_CALL": "Recorded public-evidence FDA-V3 direction.",
    }
    return f"{reasons.get(source, 'Recorded directional model assessment.')} Final assessed direction: {call}."


def build_decisions(history, broad, qualified, promotions=None, strict_reviews=None):
    hist = indexed(history, "history")
    directions = indexed(broad, "broad directions")
    strict = indexed(qualified, "strict qualified")
    promoted = indexed(promotions, "promotions") if promotions is not None and not promotions.empty else {}
    reviewed = indexed(strict_reviews, "strict reviews") if strict_reviews is not None and not strict_reviews.empty else {}
    if set(hist) != set(directions):
        raise ValueError("Historical and broad event identities do not match")
    if not set(strict).issubset(hist):
        raise ValueError("Strict qualification contains an unknown historical event")

    rows = []
    for key, row in hist.items():
        direction = directions[key]
        broad_call = clean(direction.get("forced_direction")).upper()
        if broad_call not in VALID_DIRECTIONS:
            raise ValueError(f"Missing recorded broad direction for {key}")
        evidence = clean(row.get("v3_evidence_summary"))
        notes = clean(row.get("internal_direction_note")) or clean(row.get("public_evidence_note"))
        sources = clean(row.get("v3_source_urls"))
        if key in strict:
            call = clean(strict[key].get("qualified_direction")).upper()
            if call not in VALID_DIRECTIONS:
                raise ValueError(f"Invalid strict direction for {key}")
            promotion = promoted.get(key, {})
            evidence = clean(promotion.get("predecision_evidence")) or evidence or notes
            sources = clean(promotion.get("source_urls")) or sources
            reason = evidence or "Recorded strict FDA-V3 directional qualification."
            basis, strict_status, strict_direction = "STRICT", "QUALIFIED", call
            strict_reason = "Qualified strict direction from recorded public evidence."
            source = clean(strict[key].get("source_layer"))
        else:
            call = broad_call
            basis, strict_status, strict_direction = "BROAD", "REVIEW_NO_CALL_ANALYZED", "REVIEW"
            strict_reason = evidence or "Critical public FDA evidence remains unresolved."
            reason, source = broad_reason(direction), clean(direction.get("source_layer"))
            evidence = evidence or notes

        if key in reviewed:
            review = reviewed[key]
            strict_reason = clean(review.get("fda_gate_reason"))
            evidence = clean(review.get("evidence_summary")) or clean(review.get("review_note"))
            sources = clean(review.get("source_urls"))
            if key in strict:
                reason = evidence

        # Outcome is joined only after the assessment has been selected.
        actual = clean(row.get("actual_outcome")).upper()
        match = ("MATCH" if call == actual else "MISS") if actual in VALID_DIRECTIONS else "PENDING"
        rows.append({
            "event_key": key,
            "ticker": clean(row.get("ticker")),
            "pdufa_date": clean(row.get("pdufa_date")),
            "assessed_direction": call,
            "assessment_basis": basis,
            "strict_status": strict_status,
            "strict_direction": strict_direction,
            "decision_reason": reason,
            "strict_reason": strict_reason,
            "baseline_model_probability_pct": clean(direction.get("fallback_probability")),
            "source_layer": source,
            "model_version": clean(reviewed.get(key, {}).get("fda_model_version")) if key in strict and key in reviewed else clean(direction.get("model_version")),
            "evidence_summary": evidence,
            "source_urls": sources,
            "actual_outcome": actual,
            "match_result": match,
            "review_status": clean(reviewed.get(key, {}).get("review_status")) or "ANALYZED_DIRECTION_RECORDED",
            "validation_status": "RETROSPECTIVE_DEVELOPMENT_NOT_BLIND",
            "strict_run_id": clean(reviewed.get(key, {}).get("run_id")),
        })
    return pd.DataFrame(rows).sort_values(["pdufa_date", "ticker", "event_key"]).reset_index(drop=True)


def summary_for(decisions):
    result = {"total_assessed": len(decisions), "unresolved_assessments": 0}
    for basis in ["BROAD", "STRICT"]:
        subset = decisions[decisions["assessment_basis"].eq(basis)]
        scored = subset[subset["actual_outcome"].isin(VALID_DIRECTIONS)]
        matches = int(scored["match_result"].eq("MATCH").sum())
        result[basis.lower()] = {
            "assessed": len(subset),
            "approval_calls": int(subset["assessed_direction"].eq("APPROVED").sum()),
            "crl_calls": int(subset["assessed_direction"].eq("CRL").sum()),
            "scored": len(scored),
            "matches": matches,
            "misses": len(scored) - matches,
            "match_pct": round(100 * matches / len(scored), 2) if len(scored) else None,
        }
    result["validation_status"] = "RETROSPECTIVE_DEVELOPMENT_NOT_BLIND"
    result["note"] = "Recorded suggestions and strict qualification are separate. Historical matches are descriptive development results."
    return result


def write_decisions(history=None, qualified=None, promotions=None):
    if history is None:
        history = pd.read_csv(DATA / "fda_v3_historical_backtest.csv", keep_default_na=False)
    if qualified is None:
        qualified = pd.read_csv(DATA / "fda_100_on_100_historical.csv", keep_default_na=False)
    if promotions is None:
        promotions = pd.read_csv(DATA / "fda_100_on_100_verified_promotions.csv", keep_default_na=False)
    broad = pd.read_csv(DATA / "fda_directional_100pct_historical.csv", keep_default_na=False)
    reviews_path = DATA / "strict_historical_126_review.csv"
    reviews = pd.read_csv(reviews_path, keep_default_na=False) if reviews_path.exists() else None
    decisions = build_decisions(history, broad, qualified, promotions, reviews)
    decisions.to_csv(DATA / "historical_assessed_decisions.csv", index=False)
    summary = summary_for(decisions)
    (DATA / "historical_assessed_decisions_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(write_decisions(), indent=2))
