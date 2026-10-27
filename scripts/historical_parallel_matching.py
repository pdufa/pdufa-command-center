"""Conservative historical-parallel retrieval for PDUFA review.

No probabilistic claims or invented similarity percentages. Input records must be
independently sourced and validated upstream. Standard library only.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Mapping, Sequence

FIELDS = ("indication", "population", "line_of_therapy", "mechanism",
          "modality", "endpoint_family", "regulatory_pathway")
DECISIONS = {"approved", "crl", "withdrawn"}
DEVELOPMENT = {"terminated", "discontinued", "no_application"}


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def find_parallels(
    current: Mapping[str, Any],
    historical: Sequence[Mapping[str, Any]],
    *,
    as_of: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Return evidence-grounded matches; no FDA probability is calculated.

    Required historical fields: program_id, evidence_as_of, source_urls.
    Decision examples are counted once per FDA application, not once per NCT.
    Historical evidence later than the requested cutoff is excluded.
    """
    cutoff = _as_date(as_of)
    if cutoff is None:
        raise ValueError("as_of date required")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    matches = []
    for h in historical:
        if not h.get("program_id") or h.get("program_id") == current.get("program_id"):
            continue
        sources = h.get("source_urls") or []
        evidence_date = _as_date(h.get("evidence_as_of"))
        if not evidence_date or evidence_date > cutoff or not sources:
            continue
        # Do not use historical outcome as a matching feature.
        equal = [f for f in FIELDS if current.get(f) and h.get(f)
                 and str(current[f]).casefold().strip() == str(h[f]).casefold().strip()]
        compared = [f for f in FIELDS if current.get(f) and h.get(f)]
        if not equal:
            continue
        outcome = str(h.get("fda_outcome") or "").lower()
        decision_date = _as_date(h.get("fda_decision_date"))
        # No outcome can be used until it was known at the cutoff.
        if not decision_date or decision_date > cutoff:
            outcome = ""
        kind = ("fda_decision" if outcome in DECISIONS and h.get("application_id")
                else "development")
        matches.append({
            "program_id": str(h["program_id"]),
            "application_id": h.get("application_id"),
            "matched_dimensions": equal,
            "compared_dimensions": compared,
            "match_status": "unscored",
            "evidence_as_of": evidence_date.isoformat(),
            "source_urls": list(sources),
            "group": kind,
            "fda_outcome": outcome if kind == "fda_decision" else None,
            "fda_decision_date": decision_date.isoformat() if outcome and decision_date else None,
        })
    matches.sort(key=lambda m: (-len(m["matched_dimensions"]),
                                -len(m["compared_dimensions"]), m["program_id"]))
    unique_decisions = set()
    result = []
    for m in matches:
        key = m["application_id"] if m["group"] == "fda_decision" else None
        if key is not None:
            if key in unique_decisions:
                continue
            unique_decisions.add(key)
        result.append(m)
        if len(result) >= limit:
            break
    return {
        "as_of": cutoff.isoformat(),
        "status": "verified_matches_available" if result else "no_verified_matches",
        "verified_match_count": len(result),
        "match_count_is_limited": len(result) == limit,
        "historical_parallels_collapsed": True,
        "prediction_probability": None,
        "prediction_status": "not_calibrated",
        "matches": result,
    }
