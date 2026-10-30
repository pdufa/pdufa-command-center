"""SSE transport for progressive rendering of existing saved dossier fields.

This is a replay of available evidence, NOT a background research worker.
"""
import json
import re

FIELDS = (
    ("sponsor", "Sponsor"),
    ("products", "Drug or product"),
    ("indication", "Indication"),
    ("phase", "Trial phase"),
)


def evidence_available(value):
    """A populated placeholder or unverified regulatory claim is not verified evidence."""
    if value is None or value == "" or value == [] or value == {}:
        return False
    if isinstance(value, dict):
        if value.get("interpretation") in ("NOT_INFERRED", "NOT_ADJUDICATED"):\n            return False\n        status = value.get("status")
        if status is not None and status != "VERIFIED":
            return False
        if status == "VERIFIED":
            return bool(value.get("source_url") and value.get("source_document_sha256") and value.get("value") is not None)
    return True


def field_events(nct_id, dossier):
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id):
        raise ValueError("Invalid NCT identifier")
    if not isinstance(dossier, dict) or dossier.get("nct_id") != nct_id:
        raise ValueError("Dossier identity mismatch")
    yield {"type": "started", "nct_id": nct_id, "mode": "SAVED_EVIDENCE_REPLAY", "research_running": False}
    for key, label in FIELDS:
        value = dossier.get(key)
        present = evidence_available(value)
        yield {
            "type": "leaf",
            "nct_id": nct_id,
            "node_id": key,
            "section": "trial_identity",
            "label": label,
            "level": 4,
            "status": "AVAILABLE" if present else "UNAVAILABLE",
            "value": value if present else None,
            "research_running": False,
            "spinner": False,
        }
    available = sum(evidence_available(dossier.get(key)) for key, _ in FIELDS)
    yield {
        "type": "progress",
        "nct_id": nct_id,
        "section": "trial_identity",
        "available": available,
        "total": len(FIELDS),
        "status": "AVAILABLE" if available == len(FIELDS) else "PARTIAL",
        "research_running": False,
    }
    sections = (
        ("trial_design", "Trial design", ("primary_endpoints", "study_completion_status")),
        ("clinical_results", "Clinical results", ("primary_endpoint_results", "statistical_significance", "clinical_effect_size", "safety_findings", "serious_adverse_events")),
        ("regulatory", "FDA & regulatory", ("fda_regulatory_pathway", "special_designations", "regulatory_submission_evidence", "pdufa_date")),
    )
    for section_id, label, keys in sections:
        present_count = 0
        for key in keys:
            value = dossier.get(key)
            present = evidence_available(value)
            if present:
                present_count += 1
            yield {
                "type": "leaf", "nct_id": nct_id, "node_id": key,
                "section": section_id, "label": key.replace("_", " ").title(),
                "level": 4, "status": "AVAILABLE" if present else "UNAVAILABLE",
                "value": value if present else None, "research_running": False, "spinner": False,
            }
        yield {
            "type": "progress", "nct_id": nct_id, "section": section_id,
            "label": label, "available": present_count, "total": len(keys),
            "status": "AVAILABLE" if present_count == len(keys) else "PARTIAL",
            "research_running": False,
        }
    # Readiness is an inventory of evidence, not an adjudication or FDA forecast.
    evidence_keys = (
        "primary_endpoints", "primary_endpoint_results", "statistical_significance",
        "clinical_effect_size", "safety_findings", "serious_adverse_events",
        "study_completion_status", "fda_regulatory_pathway",
        "regulatory_submission_evidence", "pdufa_date",
    )
    missing = [key for key in evidence_keys if not evidence_available(dossier.get(key))]
    yield {
        "type": "readiness", "nct_id": nct_id, "section": "science",
        "status": "EVIDENCE_INCOMPLETE" if missing else "EVIDENCE_PRESENT_NOT_ADJUDICATED",
        "evidence_fields_present": len(evidence_keys) - len(missing),
        "evidence_fields_total": len(evidence_keys),
        "missing_fields": missing,
        "assessments_completed": 0,
        "decision": "ABSTAIN",
        "research_running": False,
    }
    # The catalog is a planned framework, not proof that its assessments ran.
    # Emit all forty explicitly pending records; never infer scores from field presence.
    for number in range(1, 41):
        yield {
            "type": "assessment", "nct_id": nct_id,
            "assessment_id": f"S{number:02d}", "section": "science",
            "status": "NOT_ASSESSED", "evidence_count": 0,
            "spinner": False, "research_running": False,
        }
    yield {
        "type": "progress", "nct_id": nct_id, "section": "science",
        "available": 0, "total": 40, "status": "NOT_ASSESSED",
        "research_running": False,
    }
    yield {"type": "complete", "nct_id": nct_id, "decision": "ABSTAIN", "research_running": False}


def sse_lines(nct_id, dossier):
    for event in field_events(nct_id, dossier):
        yield "event: " + event["type"] + "\n"
        yield "data: " + json.dumps(event, separators=(",", ":"), default=str) + "\n\n"
