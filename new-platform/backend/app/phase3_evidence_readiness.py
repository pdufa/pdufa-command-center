"""Phase-3-onward evidence readiness, independent of scientific scores and FS/FA.

Pure read-only assessment: no prediction probabilities, trade signals, or scan writes.
An item is complete only with a source URL, source date, and verified status.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

PHASE3_FIELDS = (
    ("trial_identity", "Trial identity and registration", "phase3"),
    ("trial_design", "Protocol, comparator and randomization", "phase3"),
    ("primary_endpoint", "Primary endpoint result", "phase3"),
    ("effect_size", "Effect size and confidence interval", "phase3"),
    ("statistical_significance", "Statistical analysis", "phase3"),
    ("safety", "Safety and discontinuations", "phase3"),
    ("secondary_endpoints", "Secondary outcomes", "phase3"),
    ("subgroups", "Population and subgroup evidence", "phase3"),
    ("historical_analogs", "Comparable historical trials", "phase3"),
    ("designations", "Applicable FDA designations", "phase3"),
    ("financial_runway", "Cash and runway", "phase3"),
    ("valuation", "Current equity valuation", "phase3"),
    ("commercial_market", "Commercial market assessment", "phase3"),
    ("nda_submission", "NDA/BLA submission evidence", "filing"),
    ("filing_acceptance", "FDA filing acceptance", "filing"),
    ("pdufa_date", "Verified FDA action date", "filing"),
    ("manufacturing", "Manufacturing and inspection evidence", "review"),
    ("regulatory_updates", "Regulatory review developments", "review"),
    ("historical_validation", "Out-of-sample prediction validation", "model"),
)

def evidence_readiness(*, exact_key: str, phase: str, evidence: dict,
                       as_of: str | None = None) -> dict:
    """Return auditable coverage; pending later-stage fields do not penalize Phase 3.

    evidence[field] = {status: VERIFIED|PENDING|CONFLICT|STALE,
                       source_url: https URL, source_date: YYYY-MM-DD}
    Historical validation is reported separately, never counted as a clinical input.
    """
    if not exact_key or not exact_key.strip():
        raise ValueError("Exact trial identity required")
    if phase not in {"phase3", "filing", "review"}:
        raise ValueError("phase must be phase3, filing, or review")
    today = date.fromisoformat(as_of) if as_of else date.today()
    order = {"phase3": 0, "filing": 1, "review": 2}
    items = []
    for key, label, first_phase in PHASE3_FIELDS:
        record = evidence.get(key, {})
        record = record if isinstance(record, dict) else {}
        applicable = first_phase == "model" or order.get(first_phase, 99) <= order[phase]
        source = str(record.get("source_url") or "")
        parsed = urlparse(source)
        try:
            source_date = date.fromisoformat(str(record.get("source_date") or ""))
            date_valid = source_date <= today
        except ValueError:
            date_valid = False
        verified = (record.get("status") == "VERIFIED" and
                    parsed.scheme == "https" and bool(parsed.netloc) and date_valid)
        status = ("NOT_YET_APPLICABLE" if not applicable else
                  "VERIFIED" if verified else
                  "CONFLICT" if record.get("status") == "CONFLICT" else
                  "STALE" if record.get("status") == "STALE" else "PENDING")
        items.append({"key": key, "label": label, "firstPhase": first_phase,
                      "status": status, "sourceUrl": source if verified else None,
                      "sourceDate": str(source_date) if verified else None})
    clinical = [x for x in items if x["firstPhase"] != "model" and
                x["status"] != "NOT_YET_APPLICABLE"]
    verified_count = sum(x["status"] == "VERIFIED" for x in clinical)
    total = len(clinical)
    model = next(x for x in items if x["key"] == "historical_validation")
    blockers = [x["key"] for x in clinical if x["status"] != "VERIFIED"]
    return {
        "schemaVersion": "phase3-evidence-readiness-v1",
        "exactKey": exact_key, "phase": phase, "asOf": today.isoformat(),
        "dataReadinessPercent": round(100 * verified_count / total, 1) if total else None,
        "verifiedCount": verified_count, "applicableCount": total,
        "pendingRequirements": blockers, "items": items,
        "scientificScore": None,
        "predictionConfidencePercent": None,
        "historicalModelValidationStatus": model["status"],
        "predictionReady": False,
        "tradeAuthorized": False,
        "displayRole": "research_status_only",
    }
