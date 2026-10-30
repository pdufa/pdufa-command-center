"""Evidence availability is not analysis completion or probability of FDA approval."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

FIELD_STATES = {"VERIFIED", "AVAILABLE_UNVERIFIED", "INCOMPLETE", "MISSING"}
REQUIRED_FIELDS = (
    ("Phase 3 efficacy", "Primary endpoint result", True),
    ("Phase 3 efficacy", "Prespecified endpoint definition", True),
    ("Safety", "Adverse event tables", True),
    ("Statistics", "Analysis population and SAP", True),
    ("FDA history", "Application and regulatory status", True),
    ("Manufacturing / CMC", "Manufacturing inspection evidence", True),
    ("Historical comparisons", "Relevant historical decisions", False),
    ("Special designations", "FDA designation documentation", False),
)


def assess_data_availability(
    evidence_fields: Iterable[Mapping],
    required_fields=REQUIRED_FIELDS,
) -> dict:
    """Count only VERIFIED fields as available. Missing required data blocks readiness."""
    supplied = {}
    for item in evidence_fields:
        key = (str(item.get("category", "")), str(item.get("field", "")))
        if key in supplied:
            raise ValueError("Duplicate evidence field")
        status = str(item.get("status", "MISSING"))
        if status not in FIELD_STATES:
            raise ValueError("Unknown evidence status")
        supplied[key] = dict(item)
    categories: dict[str, dict] = {}
    details = []
    critical_missing = []
    verified_count = 0
    for category, field, critical in required_fields:
        item = supplied.get((category, field), {})
        status = item.get("status", "MISSING")
        # A VERIFIED label without a source reference is not verified.
        source = str(item.get("source_url") or "").strip()
        if status == "VERIFIED" and not source.startswith("https://"):
            status = "AVAILABLE_UNVERIFIED"
        verified = status == "VERIFIED"
        verified_count += int(verified)
        group = categories.setdefault(category, {"verified": 0, "total": 0})
        group["verified"] += int(verified)
        group["total"] += 1
        detail = {
            "category": category, "field": field, "critical": critical,
            "status": status, "source_url": source,
            "notes": str(item.get("notes") or ""),
        }
        details.append(detail)
        if critical and not verified:
            critical_missing.append(field)
    total = len(details)
    percent = round(100 * verified_count / total, 1) if total else 0.0
    for category in categories.values():
        category["percent"] = round(100 * category["verified"] / category["total"], 1)
    if critical_missing:
        readiness = "NOT_READY"
    elif verified_count < total:
        readiness = "PARTIAL_ANALYSIS_ONLY"
    else:
        readiness = "READY_FOR_FULL_ANALYSIS"
    return {
        "available_percent": percent,
        "verified_fields": verified_count,
        "required_fields": total,
        "categories": categories,
        "fields": details,
        "critical_missing": critical_missing,
        "readiness": readiness,
    }
