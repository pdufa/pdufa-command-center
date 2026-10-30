import re

"""Build a conservative source-by-source SCIENCE review queue for historical cases.

The queue uses existing evidence metadata; it does not assert independent
document authentication or completed scientific assessment.
"""


def build_science_source_review_queue(reconstruction, authenticated_intakes=None):
    # Intake hashes are identity metadata only; never auto-certify source evidence.
    authenticated_intakes = authenticated_intakes or {}
    if not isinstance(authenticated_intakes, dict):
        raise ValueError('intakes must be a mapping keyed by observation ID')

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
            intake = authenticated_intakes.get(obs["id"])
            if intake is not None:
                if not isinstance(intake, dict):
                    raise ValueError("intake must be a mapping")
                if intake.get("schema_version") != "fda-crl-offline-intake-v1":
                    raise ValueError("unknown intake schema")
                if intake.get("fda_authenticity_verified") or intake.get("eligible_for_predictive_training"):
                    raise ValueError("offline intake cannot self-certify evidence")
                if not re.fullmatch(r"[0-9a-f]{64}", intake.get("sha256", "")):
                    raise ValueError("intake requires a valid lowercase SHA-256 digest")
                if intake.get("status") != "HASHED_UNVERIFIED_SOURCE":
                    raise ValueError("offline intake status must remain unverified")
                if role != "OUTCOME_ONLY":
                    raise ValueError("FDA action letters cannot be attached to predecision observations")
                if intake.get("application") != case.get("application_id"):
                    raise ValueError("intake application does not match case")
                if intake.get("action_date") != case.get("action_date"):
                    raise ValueError("intake action date does not match case")
                if intake.get("source_url_claimed") != obs.get("source_url"):
                    raise ValueError("intake source URL does not match observation")
            rows.append({
                "event_key": case["event_key"],
                "offline_intake_sha256": intake.get("sha256") if intake else None,
                "offline_intake_status": intake.get("status") if intake else None,
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
