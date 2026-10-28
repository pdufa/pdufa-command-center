"""Read-only recovery manifest for independent historical forecast authentication."""
from research.fda_original_artifact_inventory import build_original_artifact_inventory
from research.fda_archive_lock_chronology import audit_archive_lock_chronology


def build_recovery_manifest(archive, reconstruction):
    inventory = build_original_artifact_inventory(archive, reconstruction)
    chronology = audit_archive_lock_chronology(inventory, archive)
    by_key = {case["event_key"]: case for case in chronology["cases"]}
    cases = []
    for item in inventory["cases"]:
        key = item["event_key"]
        case = by_key[key]
        cases.append({
            "event_key": key,
            "fda_action_date": item["action_date"],
            "retrospective_lock_date": case["archive_lock_date"],
            "retrospective_lock_after_action": case["archive_lock_after_fda_action"],
            "original_prediction_found": False,
            "required_next_evidence": [
                "Pre-action timestamped original prediction and artifact bytes",
                "Independent creation-time provenance, not file modification time",
                "Frozen model hash and training cutoff before the decision",
                "Original feature inputs with contemporaneous publication dates",
                "Independent reviewer verification and leakage audit",
            ],
            "status": "AWAITING_INDEPENDENT_PRE_ACTION_ARTIFACT",
        })
    return {
        "research_only": True,
        "trading_authorized": False,
        "cases": cases,
        "cases_requiring_original_evidence": len(cases),
        "retrospective_archives_after_action": chronology["archives_locked_after_action"],
        "verified_prospective_predictions": 0,
    }
