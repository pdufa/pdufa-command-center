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


def field_events(nct_id, dossier):
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id):
        raise ValueError("Invalid NCT identifier")
    if not isinstance(dossier, dict) or dossier.get("nct_id") != nct_id:
        raise ValueError("Dossier identity mismatch")
    yield {"type": "started", "nct_id": nct_id, "mode": "SAVED_EVIDENCE_REPLAY", "research_running": False}
    for key, label in FIELDS:
        value = dossier.get(key)
        present = value not in (None, "", [])
        yield {
            "type": "leaf",
            "nct_id": nct_id,
            "node_id": key,
            "label": label,
            "level": 4,
            "status": "AVAILABLE" if present else "UNAVAILABLE",
            "value": value if present else None,
            "research_running": False,
            "spinner": False,
        }
    available = sum(dossier.get(key) not in (None, "", []) for key, _ in FIELDS)
    yield {
        "type": "progress",
        "nct_id": nct_id,
        "section": "trial_identity",
        "available": available,
        "total": len(FIELDS),
        "status": "AVAILABLE" if available == len(FIELDS) else "PARTIAL",
        "research_running": False,
    }
    yield {"type": "complete", "nct_id": nct_id, "decision": "ABSTAIN", "research_running": False}


def sse_lines(nct_id, dossier):
    for event in field_events(nct_id, dossier):
        yield "event: " + event["type"] + "\n"
        yield "data: " + json.dumps(event, separators=(",", ":"), default=str) + "\n\n"
