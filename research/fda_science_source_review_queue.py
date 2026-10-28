"""Build a conservative source-by-source SCIENCE review queue for historical cases.

The queue uses existing evidence metadata; it does not assert independent
document authentication or completed scientific assessment.
"""


def build_science_source_review_queue(reconstruction):
    rows = []
    for case in reconstruction["cases"]:
        cutoff = case.get("reconstruction_cutoff")
        for obs in case.get("observations", []):
            role = obs.get("source_role")
            available = obs.get("available_on")
            pre_cutoff = bool(cutoff and available and available <= cutoff)
            review_ready = bool(
                role == "PREDECISION_RESEARCH" and pre_cutoff
                and obs.get("source_bytes_retained")
                and obs.get("original_document_sha256")
                and obs.get("independently_reviewed")
            )
            rows.append({
                "event_key": case["event_key"],
                "observation_id": obs["id"],
                "source_url": obs.get("source_url"),
                "science_question_ids": obs.get("science_question_ids", []),
                "source_role": role,
                "available_on": available,
                "reconstruction_cutoff": cutoff,
                "before_reconstruction_cutoff": pre_cutoff,
                "original_prediction_cutoff_verified": bool(case.get("original_prediction_cutoff")),
                "source_bytes_retained": bool(obs.get("source_bytes_retained")),
                "document_sha256_present": bool(obs.get("original_document_sha256")),
                "independently_reviewed": bool(obs.get("independently_reviewed")),
                "ready_for_independent_science": review_ready,
                "eligible_for_predictive_training": False,
                "status": "REVIEW_INPUT_ONLY" if review_ready else "SOURCE_AUTHENTICATION_OR_CUTOFF_BLOCKED",
            })
    return {
        "research_only": True,
        "trading_authorized": False,
        "sources_reviewed": len(rows),
        "ready_for_independent_science": sum(row["ready_for_independent_science"] for row in rows),
        "eligible_for_predictive_training": 0,
        "sources": rows,
    }
