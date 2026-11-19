"""Dispatch independent Levels 7–20 over a frozen evidence snapshot."""
from datetime import datetime, timezone
import json

from .assessment_runtime import clinical_context, now, sha

VERSION = "extended-assessment-v1.0.0"
NAMES = {
    7: "Evidence collection and provenance",
    8: "Trial identity and evidence readiness",
    9: "Phase and indication hierarchy",
    10: "Efficacy",
    11: "Safety",
    12: "Statistical validity",
    13: "Subgroups and unmet need",
    14: "FDA regulatory intelligence",
    15: "CMC and manufacturing",
    16: "Advisory committees and exceptions",
    17: "Sponsor and commercial intelligence",
    18: "Versioned predictions",
    19: "Historical backtesting and calibration",
    20: "Integrated validation and release readiness",
}


def assess_extended(request, source):
    doc = json.loads(source["document_json"])
    official_url = f"https://clinicaltrials.gov/api/v2/studies/{request.nct}"
    if (sha(doc) != source["input_sha256"] or source["nct_id"] != request.nct
            or doc["protocolSection"]["identificationModule"]["nctId"] != request.nct
            or source["source_url"] != official_url):
        raise ValueError("Frozen evidence identity, source URL or digest mismatch")

    captured = datetime.fromisoformat(source["captured_at"])
    if captured.tzinfo is None:
        raise ValueError("Source capture timestamp must include timezone")
    captured_day = captured.astimezone(timezone.utc).date().isoformat()
    if request.cutoffDate and max(captured_day, source["published_at"]) > request.cutoffDate.isoformat():
        raise ValueError("Historical evidence leakage detected")

    level = request.level
    if level <= 8:
        from .extended_evidence_assessment import assess_evidence_level
        details = assess_evidence_level(request, source)
    elif level <= 12:
        from .extended_scientific_assessment import assess_extended_science
        details = assess_extended_science(request, source)
    elif level <= 16:
        from .extended_clinical_assessment import assess_clinical_level
        details = assess_clinical_level(level, source, nct=request.nct, cutoff=request.cutoffDate)
    else:
        from .extended_prediction_assessment import assess_prediction_level
        details = assess_prediction_level(request, source)

    checks = details["checks"]
    gaps = [check["explanation"] for check in checks
            if check["state"] in {"MISSING", "UNVERIFIED", "CONFLICTING"}]
    states = {check["state"] for check in checks}
    evidence_status = ("CONFLICTING" if "CONFLICTING" in states else "INSUFFICIENT" if gaps
                       else "AVAILABLE_WITH_LIMITATIONS")
    observations = details.get("observations", [])
    explanation = details.get("explanation", "Source evidence and unresolved requirements are retained for owner review.")
    return {
        **details,
        "schemaVersion": 3,
        "kind": "EXTENDED_TRIAL_ASSESSMENT",
        "contract": request.contract,
        "nct": request.nct,
        "level": level,
        "name": details.get("name", NAMES[level]),
        "engineVersion": details.get("engineVersion", f"{VERSION}/level-{level}"),
        "mode": request.mode,
        "cutoffDate": request.cutoffDate.isoformat() if request.cutoffDate else None,
        "executedAt": now(),
        "executionStatus": details.get("executionStatus", "COMPLETED_WITH_LIMITATIONS"),
        "evidenceStatus": details.get("evidenceStatus", evidence_status),
        "scientificStatus": details.get("scientificStatus", "SOURCE_BOUND_ANALYSIS_NOT_VALIDATED"),
        "ownerReviewStatus": "OWNER_NOT_REVIEWED",
        "activationStatus": "RESEARCH_EXECUTION_ONLY",
        "historicalAccuracyEligible": False,
        "score": {"value": None, "kind": "NOT_VALIDATED", "status": "NOT_SCORED",
                  "available": 0, "applicable": 0, "method": explanation},
        "fdaPrediction": {"outcome": "ABSTAIN", "probability": None, "confidence": "NOT_VALIDATED",
                          "calibration": "NO_VALIDATED_FDA_MODEL"},
        "explanation": explanation,
        "context": {**clinical_context(doc), **details.get("context", {})},
        "observations": observations if isinstance(observations, list) else [observations],
        "risks": details.get("risks", gaps),
        "recommendations": details.get("recommendations", gaps),
        "limitations": details.get("limitations", []),
        "evidence": {key: source[key] for key in ("snapshot_id", "nct_id", "captured_at",
                     "published_at", "source_url", "raw_sha256", "input_sha256")},
        "savedToDatabase": True,
    }
