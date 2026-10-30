"""Read-only inventory of evidence needed to substantiate prospective FDA forecasts.

This produces a research retrieval worklist, never a claim that records exist.
"""
import json
from pathlib import Path
from research.fda_archive_chronology_gate import audit_archive_chronology


def build_prediction_provenance_worklist(archive, reconstruction):
    chronology = audit_archive_chronology(archive, reconstruction)
    cases = {case["event_key"]: case for case in reconstruction["cases"]}
    worklist = []
    for row in chronology["cases"]:
        case = cases[row["event_key"]]
        worklist.append({
            "event_key": row["event_key"],
            "action_date": case["action_date"],
            "original_prediction_cutoff": case.get("original_prediction_cutoff"),
            "verified_original_prediction": False,
            "required_artifacts": [
                "Independently timestamped pre-action prediction record with exact event key",
                "Contemporaneous immutable model version and training-data cutoff",
                "Contemporaneous frozen feature values and source publication timestamps",
                "Evidence that action outcome was not included in model features or training",
                "Program-family disjointness and full sampling denominator audit",
                "Independent source and prediction chronology review"
            ],
            "archive_chronology": row["reason"],
            "validation_status": "BLOCKED_PENDING_ORIGINAL_PREDICTION_ARTIFACTS",
        })
    return {"research_only": True, "verified_prospective_predictions": 0,
            "trading_authorized": False, "worklist": worklist}


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m research.fda_prediction_provenance_worklist archive.json reconstruction.json")
    archive = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reconstruction = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(build_prediction_provenance_worklist(archive, reconstruction), indent=2))
