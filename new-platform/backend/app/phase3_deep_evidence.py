"""Research-only, point-in-time evidence integrity and analog matching.

Never treats later FDA outcomes or later source publications as predictors.
Similarity is descriptive, not a calibrated approval probability.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

FEATURES = ("indication", "line_of_therapy", "modality", "mechanism",
            "endpoint", "comparator", "trial_design", "population")
WEIGHTS = {"indication": 4, "line_of_therapy": 3, "modality": 2,
           "mechanism": 2, "endpoint": 3, "comparator": 2,
           "trial_design": 2, "population": 2}

def _date(value):
    return date.fromisoformat(value)

def validate_snapshot(row: dict, *, cutoff: str) -> dict:
    """Fail closed on incomplete identity or point-in-time provenance."""
    if not row.get("exactKey") or not row.get("sourceUrl", "").startswith("https://"):
        return {"eligible": False, "reason": "IDENTITY_OR_SOURCE_MISSING"}
    try:
        observed = _date(row["observedAt"])
        published = _date(row["publishedAt"])
        cutoff_date = _date(cutoff)
    except (KeyError, TypeError, ValueError):
        return {"eligible": False, "reason": "INVALID_DATES"}
    if published > observed or observed > cutoff_date:
        return {"eligible": False, "reason": "FUTURE_INFORMATION"}
    if row.get("reviewStatus") != "VERIFIED":
        return {"eligible": False, "reason": "UNVERIFIED"}
    return {"eligible": True, "reason": None}

def find_historical_analogs(target: dict, history: list[dict], *,
                            prediction_as_of: str, limit: int = 10) -> dict:
    if not target.get("exactKey") or limit < 1:
        raise ValueError("Exact target identity and positive limit required")
    candidates = []
    for row in history:
        if row.get("exactKey") == target["exactKey"]:
            continue
        audit = validate_snapshot(row, cutoff=prediction_as_of)
        if not audit["eligible"]:
            continue
        common = [key for key in FEATURES if target.get(key) and row.get(key)]
        if not common:
            continue
        denominator = sum(WEIGHTS[k] for k in common)
        matched = sum(WEIGHTS[k] for k in common if target[k] == row[k])
        candidates.append({
            "exactKey": row["exactKey"], "similarity": round(matched / denominator, 4),
            "comparableFeatures": len(common), "matchedFeatures":
                [k for k in common if target[k] == row[k]],
            "sourceUrl": row["sourceUrl"], "observedAt": row["observedAt"],
            "outcome": None,  # Do not leak future labels into feature matching.
        })
    candidates.sort(key=lambda r: (-r["similarity"], -r["comparableFeatures"], r["exactKey"]))
    return {"targetExactKey": target["exactKey"], "predictionAsOf": prediction_as_of,
            "analogs": candidates[:limit], "approvalProbability": None,
            "tradeAuthorized": False, "researchOnly": True}

def contradiction_flags(evidence: list[dict]) -> list[dict]:
    """Flag differing verified numeric values for the same endpoint and population."""
    groups = {}
    for row in evidence:
        if row.get("reviewStatus") != "VERIFIED":
            continue
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            continue
        key = (row.get("exactKey"), row.get("endpoint"), row.get("population"),
               row.get("unit"), row.get("analysisCutoff"))
        if None in key or "" in key:
            continue
        groups.setdefault(key, []).append(row)
    flags = []
    for key, rows in groups.items():
        if len({float(r["value"]) for r in rows}) > 1:
            flags.append({"exactKey": key[0], "endpoint": key[1],
                          "population": key[2], "status": "REVIEW_REQUIRED",
                          "sourceUrls": sorted({r.get("sourceUrl", "") for r in rows})})
    return flags
