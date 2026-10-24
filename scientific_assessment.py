"""Evidence-first clinical trial scientific assessment. No fabricated scores."""
from dataclasses import dataclass, asdict
from typing import Optional

DOMAINS = {
    "trial_design": ("randomization", "control_group", "blinding", "power", "endpoint_prespecification"),
    "efficacy": ("primary_endpoint", "effect_size", "confidence_interval", "multiplicity", "clinical_relevance"),
    "safety": ("serious_adverse_events", "discontinuations", "mortality", "exposure", "benefit_risk"),
    "biology": ("mechanism", "target_validation", "biomarkers", "translational_evidence"),
    "reliability": ("replication", "missing_data", "subgroup_consistency", "protocol_deviations"),
    "regulatory": ("endpoint_acceptability", "agency_feedback", "precedent", "filing_readiness"),
}

@dataclass(frozen=True)
class Evidence:
    value: Optional[float] = None  # normalized 0-100, when defensible
    source_url: str = ""
    source_date: str = ""
    rationale: str = ""
    status: str = "missing"  # verified, disputed, missing

def assess(evidence: dict) -> dict:
    """Return domain scores only when ALL component evidence is verified."""
    output = {}
    for domain, fields in DOMAINS.items():
        entries = [evidence.get(f"{domain}.{field}", {}) for field in fields]
        valid = all(
            isinstance(e, dict)
            and e.get("status") == "verified"
            and bool(e.get("source_url"))
            and isinstance(e.get("value"), (int, float))
            and not isinstance(e.get("value"), bool)
            and 0 <= e["value"] <= 100
            for e in entries
        )
        output[domain] = {
            "score": round(sum(e["value"] for e in entries) / len(entries), 2) if valid else None,
            "verified": valid,
            "verified_fields": sum(1 for e in entries if isinstance(e, dict) and e.get("status") == "verified" and e.get("source_url")),
            "required_fields": len(fields),
            "missing_fields": [f for f, e in zip(fields, entries) if not isinstance(e, dict) or e.get("status") != "verified" or not e.get("source_url")],
        }
    scored = [d["score"] for d in output.values() if d["score"] is not None]
    return {"domains": output, "overall_score": round(sum(scored)/len(scored), 2) if len(scored) == len(DOMAINS) else None,
            "status": "complete" if len(scored) == len(DOMAINS) else "insufficient_evidence",
            "note": "Scientific evidence assessment; not a probability of FDA approval."}
