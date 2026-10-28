"""Fail-closed observation chronology and outcome-leakage audit.

Research reconstruction cutoffs are NOT authenticated original forecast times.
"""
from datetime import date


def audit_reconstruction_leakage(reconstruction):
    reports = []
    for case in reconstruction["cases"]:
        cutoff = date.fromisoformat(case["reconstruction_cutoff"])
        action = date.fromisoformat(case["action_date"])
        seen = set()
        excluded = []
        candidates = []
        for observation in case.get("observations", []):
            oid = observation["id"]
            if oid in seen:
                raise ValueError("duplicate observation id within case")
            seen.add(oid)
            available = date.fromisoformat(observation["available_on"])
            role = observation.get("source_role")
            reasons = []
            if role != "PREDECISION_RESEARCH":
                reasons.append("NOT_PREDECISION_SOURCE")
            if available > cutoff:
                reasons.append("AVAILABLE_AFTER_RECONSTRUCTION_CUTOFF")
            if available >= action:
                reasons.append("AT_OR_AFTER_FDA_ACTION")
            if observation.get("original_document_sha256") is None:
                reasons.append("SOURCE_BYTES_NOT_HASH_VERIFIED")
            if observation.get("independently_reviewed") is not True:
                reasons.append("NOT_INDEPENDENTLY_REVIEWED")
            entry = {"observation_id": oid, "reasons": reasons}
            (excluded if reasons else candidates).append(entry)
        reports.append({
            "event_key": case["event_key"],
            "reconstruction_cutoff": case["reconstruction_cutoff"],
            "original_prediction_cutoff": case.get("original_prediction_cutoff"),
            "candidate_observations": candidates,
            "excluded_observations": excluded,
            "validated_prediction_inputs": 0,
            "status": "RESEARCH_ONLY_NO_AUTHENTICATED_FORECAST_CUTOFF",
        })
    return {"research_only": True, "trading_authorized": False,
            "verified_prediction_inputs": 0, "cases": reports}
