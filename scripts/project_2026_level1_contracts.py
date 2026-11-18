"""Offline projections of the unrestricted FDA cohort for interface review."""
import hashlib
import json
import re

from scripts.audit_2026_unrestricted_level1 import identity

OUTCOMES = {"APPROVE": "APPROVAL", "CRL": "CRL", "INDETERMINATE": "ABSTAIN"}


def application_cycle_id(row):
    # Separate indications can share an FDA submission and review cycle.
    return "|".join(identity(row))


def project(rows, *, pool_ncts, focus_ncts):
    """Join research to caller-supplied roster membership by exact trial ID."""
    views = {name: [] for name in ("PAST", "POOL", "FOCUS", "ASSESSMENTS")}
    for row in sorted(rows, key=lambda row: (row["pdufa_date"], row["record_id"])):
        if row["verification_status"] != "VERIFIED":
            continue
        key = application_cycle_id(row)
        ncts = sorted({trial for trial in row["trial_ids"] if re.fullmatch(r"NCT\d{8}", trial)})
        base = {
            "applicationCycleId": key,
            "recordId": row["record_id"],
            "ticker": row["ticker"] or None,
            "company": row["sponsor"],
            "drug": row["drug"],
            "indication": row["indication"],
            "pdufaDate": row["pdufa_date"],
            "ncts": ncts,
            "researchOnly": True,
        }
        outcome = OUTCOMES.get(row["actual_outcome"])
        if row["assessment_kind"] == "OUTCOME_AWARE":
            views["PAST"].append({
                **base, "eventKey": key, "cutoffDate": None, "level4Score": None,
                "blindPrediction": None, "confidence": None, "status": "OUTCOME_AWARE",
                "actualOutcome": outcome, "actualDecisionAt": row["outcome_action_date"],
                "actualDecisionSourceUrl": row["source_url"],
            })
        for surface, roster in (("POOL", pool_ncts), ("FOCUS", focus_ncts)):
            for nct in ncts:
                if nct in roster:
                    views[surface].append({**base, "id": nct, "nct": nct})
        assessment_at = row["assessment_recorded_at"]
        archived_versions = row["prior_prediction_artifacts"]
        version_fields = (key, row["model_version"], assessment_at, row["prediction_frozen_at"])
        version_id = hashlib.sha256(json.dumps(version_fields).encode()).hexdigest()
        views["ASSESSMENTS"].append({
            **base, "assessmentVersionId": version_id, "level": 1,
            "assessmentKind": row["assessment_kind"], "assessedAt": assessment_at,
            "assessment": OUTCOMES[row["assessment"]],
            "predictedOutcome": OUTCOMES.get(row["prediction"]),
            "actualOutcome": outcome,
            "evidenceCutoffAt": row["evidence_cutoff_at"] or None,
            "frozenAt": row["prediction_frozen_at"] or None,
            "modelVersion": row["model_version"],
            "confidence": row["confidence"] or None,
            "confidencePercent": float(row["confidence_percent"]) if row["confidence_percent"] else None,
            "rationale": row["rationale"], "evidenceGaps": row["evidence_gaps"],
            "evidenceSources": row["evidence_sources"], "priorPredictionArtifacts": archived_versions,
        })
    return views
