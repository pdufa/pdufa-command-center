"""Independent Phase 3 scientific investigation: evidence-led, no invented scores.

Evaluates methodological, efficacy, safety and biological questions separately.
A missing document is an unknown, never a negative or an automatic PASS.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from urllib.parse import urlparse

DOMAINS = {
 "biology": ("mechanism", "target_engagement", "translational_support"),
 "design": ("randomization", "blinding", "comparator", "eligibility", "protocol_amendments"),
 "statistics": ("analysis_plan", "multiplicity", "effect_size", "confidence_interval",
                "missing_data", "sensitivity_analyses"),
 "efficacy": ("primary_endpoint", "clinical_meaningfulness", "secondary_endpoints",
              "subgroup_consistency", "durability"),
 "safety": ("serious_adverse_events", "discontinuations", "deaths",
            "exposure_adjusted_risks", "benefit_risk"),
 "consistency": ("phase2_phase3_agreement", "independent_replication",
                 "population_generalizability"),
 "regulatory": ("endpoint_precedent", "fda_feedback", "manufacturing_risk"),
 "critical_review": ("alternative_explanations", "contradictory_evidence",
                     "remaining_uncertainties"),
}
ALLOWED = {"SUPPORTS", "CHALLENGES", "MIXED", "INCONCLUSIVE"}
def scientific_investigation(*, exact_key: str, evidence: dict, as_of: str) -> dict:
    if not isinstance(exact_key, str) or not exact_key.strip() or not isinstance(evidence, dict):
        raise ValueError("Exact identity and evidence map required")
    cutoff = date.fromisoformat(as_of)
    sections = []
    all_items = []
    for domain, questions in DOMAINS.items():
        findings = []
        for question in questions:
            record = evidence.get(question, {})
            record = record if isinstance(record, dict) else {}
            url = record.get("source_url")
            try:
                source_date = date.fromisoformat(record["published_at"])
                timely = source_date <= cutoff
            except (KeyError, TypeError, ValueError):
                timely = False
            parsed = urlparse(url) if isinstance(url, str) else None
            verified = (record.get("review_status") == "VERIFIED" and timely and
                        parsed is not None and parsed.scheme == "https" and
                        bool(parsed.netloc) and
                        isinstance(record.get("finding"), str) and
                        bool(record["finding"].strip()) and
                        record.get("interpretation") in ALLOWED)
            finding = {"question": question, "status": "REVIEWED" if verified else "MISSING_OR_UNVERIFIED",
                       "interpretation": record["interpretation"] if verified else None,
                       "finding": record["finding"] if verified else None,
                       "sourceUrl": url if verified else None,
                       "sourceDate": source_date.isoformat() if verified else None}
            findings.append(finding)
            all_items.append(finding)
        sections.append({"domain": domain, "reviewed": sum(x["status"] == "REVIEWED" for x in findings),
                         "required": len(findings), "findings": findings})
    reviewed = sum(x["status"] == "REVIEWED" for x in all_items)
    challenges = [x["question"] for x in all_items if x["interpretation"] in {"CHALLENGES", "MIXED"}]
    return {"schemaVersion": "science-independent-investigation-v1",
            "exactKey": exact_key, "asOf": as_of, "sections": sections,
            "reviewed": reviewed, "required": len(all_items),
            "evidenceCoveragePercent": round(100*reviewed/len(all_items), 1),
            "criticalQuestions": challenges,
            "scientificScore": None, "approvalProbability": None,
            "independentScientificConclusion": None,
            "tradeAuthorized": False, "researchOnly": True}
