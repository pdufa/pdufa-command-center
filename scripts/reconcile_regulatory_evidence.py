"""Read-only evidence reconciliation for retrospective FDA decision research.

Preserves source provenance and prevents post-decision leakage into predictions.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from datetime import date


def reconcile_evidence(records: Sequence[Mapping], decision_date: str | None = None) -> dict:
    """Compare reported measures without silently choosing a preferred value.

    Dates are ISO 8601 calendar dates. Missing dates are excluded from the
    pre-decision evidence set (fail closed). A missing decision date also\n    excludes every record. Different populations remain
    separate; discrepancies are flagged, not automatically resolved.
    """
    try:
        cutoff = date.fromisoformat(decision_date) if isinstance(decision_date, str) and decision_date else None
    except ValueError:
        cutoff = None
    normalized = []
    for item in records:
        source = str(item.get("source") or "").strip()
        metric = str(item.get("metric") or "").strip()
        population = str(item.get("population") or "").strip()
        available = item.get("available_date")
        parsed = None
        if isinstance(available, str) and available:
            try:
                parsed = date.fromisoformat(available)
            except ValueError:
                pass
        eligible = bool(source and metric and population and parsed and cutoff and parsed < cutoff)
        normalized.append({
            "source": source, "source_url": item.get("source_url"),
            "metric": metric, "population": population,
            "value": item.get("value"), "available_date": available,
            "pre_decision_eligible": eligible,
            "exclusion_reason": None if eligible else "missing_provenance_or_not_pre_decision",
        })
    groups: dict[tuple[str, str], list[dict]] = {}
    for record in normalized:
        groups.setdefault((record["metric"], record["population"]), []).append(record)
    discrepancies = []
    for (metric, population), entries in groups.items():
        values = {str(e["value"]) for e in entries if e["value"] is not None}
        if len(values) > 1:
            discrepancies.append({"metric": metric, "population": population,
                                  "values": sorted(values), "sources": sorted(
                                      {e["source"] for e in entries})})
    return {
        "records": normalized, "discrepancies": discrepancies,
        "has_discrepancy": bool(discrepancies),
        "pre_decision_records": [r for r in normalized if r["pre_decision_eligible"]],
        "trading_ready": False,
    }
