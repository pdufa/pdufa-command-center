"""Read-only single-NCT prediction-tab payload.

Never equate a scientific evidence dossier with a completed FDA prediction.
"""
import re

def prediction_payload(nct_id, dossier):
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id):
        raise ValueError("Invalid NCT identifier")
    if dossier is None:
        raise LookupError("No verified dossier for this NCT")
    if dossier.get("nct_id") != nct_id:
        raise ValueError("Dossier NCT mismatch")
    return {
        "nct_id": nct_id,
        "status": "EVIDENCE_REVIEW_ONLY",
        "decision": "ABSTAIN",
        "prediction_authorized": False,
        "full_scientific_investigation_complete": False,
        "headline_metrics": [{"number": i, "status": "NOT_ASSESSED"} for i in range(1, 13)],
        "supporting_metrics": [{"number": i, "status": "NOT_ASSESSED"} for i in range(1, 49)],
        "scientific_assessments": [{"number": i, "status": "NOT_ASSESSED"} for i in range(1, 41)],
        "dossier": dossier,
        "message": "Source-grounded evidence only; full SCIENCE/OUTCOME/MAIN prediction pending.",
    }


def progressive_snapshot(nct_id, dossier):
    """Read-only bottom-up snapshot; never claim an unstarted task is running."""
    payload = prediction_payload(nct_id, dossier)
    leaves = []
    for key, label in (
        ("sponsor", "Sponsor"),
        ("products", "Drug or product"),
        ("indication", "Indication"),
        ("phase", "Trial phase"),
    ):
        value = dossier.get(key)
        present = value is not None and value != "" and value != []
        leaves.append({
            "id": key,
            "label": label,
            "level": 4,
            "status": "AVAILABLE" if present else "UNAVAILABLE",
            "value": value if present else None,
            "spinner": False,
        })
    complete = sum(x["status"] == "AVAILABLE" for x in leaves)
    payload["progress"] = {
        "mode": "BOTTOM_UP",
        "live_research_active": False,
        "leaves": leaves,
        "subordinate": {
            "id": "trial_identity",
            "level": 2,
            "status": "AVAILABLE" if complete == len(leaves) else "PARTIAL",
            "completed": complete,
            "total": len(leaves),
        },
        "main": {
            "id": "prediction",
            "level": 1,
            "status": "PARTIAL",
            "decision": "ABSTAIN",
        },
    }
    return payload
