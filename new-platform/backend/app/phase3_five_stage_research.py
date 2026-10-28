"""Five-stage Phase 3 deep research pipeline (no trade decisions).

1 evidence extraction/identity; 2 historical cohort; 3 efficacy/safety;
4 regulatory precedents; 5 backtest eligibility. All outputs are audit-only.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from urllib.parse import urlparse

REQUIRED_CLINICAL = ("primary_endpoint", "effect_size", "statistical_significance",
                     "safety", "trial_design", "population", "analysis_cutoff")
FDA_OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE"}

def _source_ok(item, cutoff):
    if not isinstance(item, dict):
        return False
    url = str(item.get("source_url") or "")
    p = urlparse(url)
    if p.scheme != "https" or not p.netloc or item.get("review_status") != "VERIFIED":
        return False
    try:
        return date.fromisoformat(item["published_at"]) <= date.fromisoformat(cutoff)
    except (KeyError, TypeError, ValueError):
        return False

def clinical_evidence_audit(exact_key, evidence, cutoff):
    """1: independently auditable field-level coverage, not a clinical score."""
    if not exact_key or not isinstance(evidence, dict):
        raise ValueError("Exact identity and evidence map required")
    items = {}
    for field in REQUIRED_CLINICAL:
        row = evidence.get(field)
        items[field] = "VERIFIED" if _source_ok(row, cutoff) else "PENDING_REVIEW"
    count = sum(v == "VERIFIED" for v in items.values())
    return {"exactKey": exact_key, "verified": count, "required": len(items),
            "coveragePercent": round(100*count/len(items), 1), "fields": items,
            "clinicalPass": None}

def historical_cohort_audit(rows, cutoff):
    """2: require complete denominators and pre-decision snapshots."""
    seen, accepted, excluded = set(), [], []
    for row in rows:
        key = (row.get("application_id"), row.get("review_cycle"))
        try:
            valid_dates = (date.fromisoformat(row["features_as_of"]) <
                           date.fromisoformat(row["decision_date"]) <
                           date.fromisoformat(cutoff))
        except (KeyError, TypeError, ValueError):
            valid_dates = False
        valid = (all(key) and key not in seen and valid_dates and
                 row.get("outcome") in FDA_OUTCOMES and
                 row.get("ascertainment_source") == "COMPLETE_APPLICATION_COHORT" and
                 row.get("cohort_complete_verified") is True and
                 _source_ok(row, cutoff))
        seen.add(key)
        (accepted if valid else excluded).append(key)
    return {"eligible": len(accepted), "excluded": len(excluded),
            "eligibleKeys": accepted, "probability": None,
            "completeCohortOnly": True}

def efficacy_safety_audit(exact_key, observations, cutoff):
    """3: quality checks for arm-level counts and reported statistical evidence."""
    issues, valid = [], []
    for i, row in enumerate(observations):
        if row.get("exact_key") != exact_key or not _source_ok(row, cutoff):
            issues.append({"index": i, "issue": "IDENTITY_OR_PROVENANCE"})
            continue
        n, events = row.get("denominator"), row.get("events")
        if (not isinstance(n, int) or isinstance(n, bool) or n <= 0 or
            not isinstance(events, int) or isinstance(events, bool) or
            not 0 <= events <= n):
            issues.append({"index": i, "issue": "INVALID_ARM_COUNTS"})
            continue
        valid.append({"endpoint": row.get("endpoint"), "arm": row.get("arm"),
                      "events": events, "denominator": n,
                      "ratePercent": round(100*events/n, 2),
                      "sourceUrl": row["source_url"]})
    return {"exactKey": exact_key, "validatedObservations": valid,
            "issues": issues, "causalInference": None,
            "statisticalSignificance": None}

def regulatory_precedent_audit(target, precedents, cutoff):
    """4: compare only public historical decisions known at the target cutoff."""
    from .phase3_deep_evidence import find_historical_analogs
    valid = []
    for row in precedents:
        try:
            known = date.fromisoformat(row["decision_date"]) < date.fromisoformat(cutoff)
        except (KeyError, TypeError, ValueError):
            known = False
        if known and row.get("outcome") in FDA_OUTCOMES and _source_ok(row, cutoff):
            valid.append({**row, "exactKey": row.get("exactKey") or row.get("application_id"),
                          "sourceUrl": row["source_url"],
                          "publishedAt": row["published_at"],
                          "observedAt": row["published_at"],
                          "reviewStatus": "VERIFIED"})
    analogs = find_historical_analogs(target, valid, prediction_as_of=cutoff)
    return {"knownPrecedents": len(valid), "analogs": analogs["analogs"],
            "regulatoryProbability": None, "researchOnly": True}

def validation_readiness(cohort_audit, folds):
    """5: require eligible cohort AND scored independent temporal test folds."""
    tested = sum(f.test_count for f in folds)
    brier = [f.brier_score for f in folds if f.brier_score is not None]
    ready = cohort_audit["eligible"] > 0 and tested > 0 and bool(brier)
    return {"status": "EVALUATION_AVAILABLE_NOT_CALIBRATED" if ready else
            "INSUFFICIENT_VALIDATION", "eligibleHistoricalRows": cohort_audit["eligible"],
            "outOfTimePredictions": tested, "foldsWithBrier": len(brier),
            "predictionConfidencePercent": None, "approvalProbability": None,
            "tradeAuthorized": False}
