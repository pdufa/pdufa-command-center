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
