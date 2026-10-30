"""Evidence inventory for independently verifying original pre-action predictions.

This is an artifact-location plan, not a proof that an artifact existed in 2025.
"""
from research.fda_prediction_provenance_worklist import build_prediction_provenance_worklist


def build_original_artifact_inventory(archive, reconstruction):
    base = build_prediction_provenance_worklist(archive, reconstruction)
    archive_groups = archive.get("prediction_archives", [])
    rows = []
    for case in base["worklist"]:
        matches = [group for group in archive_groups if case["event_key"] in group.get("matched_priority_event_keys", [])]
        if len(matches) != 1:
            raise ValueError("priority event must map to exactly one archive")
        group = matches[0]
        rows.append({
            "event_key": case["event_key"],
            "action_date": case["action_date"],
            "retrospective_archive_sha256": group["prediction_file_sha256"],
            "retrospective_archive_lock_created_at": group["archive_lock_created_at"],
            "retrospective_model_sha256": archive["model_spec"]["computed_sha256"],
            "candidate_sources_to_inspect": [
                "Original Git commit and file history before FDA action date",
                "Timestamped CI job artifacts and immutable build logs before FDA action date",
                "Timestamped prediction database backups or append-only logs",
                "Third-party contemporaneous emails or signed prediction exports",
                "Frozen model, training cutoff and input-feature evidence from the same date"
            ],
            "source_records_found": 0,
            "pre_action_prediction_verified": False,
            "status": "REQUIRES_INDEPENDENT_SOURCE_RETRIEVAL"
        })
    return {"research_only": True, "trading_authorized": False,
            "verified_original_predictions": 0,
            "cases": rows}
