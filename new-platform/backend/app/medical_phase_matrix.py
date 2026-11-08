"""Stage 3: phase-aware 40 × 20 review projection over the Stage-2 PostgreSQL ledger.

Read-only. Scientific test scores require saved, independently reviewed evidence.
Priority is an INVESTIGATION ORDER, never evidence of clinical risk or FDA success.
Never read retired RAAS/GEM scores, fabricate test outcomes, or mutate source data.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

CATALOG = Path(__file__).resolve().parent / "data" / "medical_phase_assessment_catalog.json"
PHASES = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4")
ORDER = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "VERIFY_PHASE": 4}
WEIGHTS = (3, 2, 2, 3, 3, 2, 1, 2, 2, 1, 3, 3, 2, 2, 2, 2, 1, 1, 3, 3)


def catalog() -> dict:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    layers = data["layers"]
    assessments = data["assessments"]
    methods = data["methods"]
    ids = [a["id"] for a in assessments]
    if (len(layers) != 8 or len(assessments) != 40 or len(methods) != 20
            or len(set(ids)) != 40
            or ids != [f"{layer}.{assessment}" for layer in range(1, 9)
                       for assessment in range(1, 6)]
            or [m["id"] for m in methods] != list(range(1, 21))):
        raise RuntimeError("Exact 8-layer, 40-assessment, 20-method catalog is required")
    layer_ids = {item["id"] for item in layers}
    if len(layer_ids) != 8 or any(x["layerId"] not in layer_ids for x in assessments):
        raise RuntimeError("Layer metadata does not match the 40 assessments")
    all_ids = set(ids)
    policy = data["phasePriority"]
    for phase in PHASES:
        seen = []
        for tier in ("critical", "high", "forward"):
            seen += policy[tier][phase]
        if len(set(seen)) != len(seen) or any(x not in all_ids for x in seen):
            raise RuntimeError("Phase priority policy has duplicates or unknown assessments")
    if "UNKNOWN" not in data["phaseRiskWatchlist"]:
        raise RuntimeError("Phase status validation prompt is required")
    return data


def registry_phase(engine, run_id: str, nct: str) -> dict:
    with engine.connect() as c:
        document = c.execute(text("""SELECT document FROM medical_continuous_stages
            WHERE run_id=:run AND stage_index=0"""), {"run":run_id}).scalar()
    if document is None:
        raise LookupError("Saved original registry identity stage is missing")
    saved = json.loads(document)
    if saved.get("nct") != nct:
        raise RuntimeError("Source identity mismatch with exact FOCUS NCT")
    source_url = saved.get("source")
    if source_url != f"https://clinicaltrials.gov/study/{nct}":
        raise RuntimeError("Original source URL does not match exact trial")
    raw = saved.get("phases", [])
    reported = [x for x in PHASES if isinstance(raw, list) and x in raw]
    return {"reportedPhases": reported, "sourceUrl": source_url,
            "phaseStatus": "REGISTRY_REPORTED_NOT_REVIEWER_VERIFIED",
            "registryTitle": saved.get("title"),
            "reportedPhase": reported[0] if len(reported) == 1 else "UNKNOWN"}


def _priority(aid: str, phase: str, policy: dict) -> tuple[str, str]:
    if phase not in PHASES:
        return "VERIFY_PHASE", "VERIFY_PHASE"
    if aid in policy["critical"][phase]:
        return "CRITICAL", "CURRENT_PHASE"
    if aid in policy["high"][phase]:
        return "HIGH", "CURRENT_PHASE"
    if aid in policy["forward"][phase]:
        return "LOW", "FORWARD_LOOKING"
    return "MODERATE", "CURRENT_PHASE"


def matrix(engine, nct: str) -> dict:
    """Generate 800 positions per exact NCT; no bulk grade or phase fabrication."""
    from . import medical_assessment_ledger as ledger
    historical = ledger.trial_history(engine, nct)
    data = catalog()
    source = registry_phase(engine, historical["sourceRunId"], nct)
    phase_events = historical["phaseEvents"]
    verified_event = phase_events[-1] if phase_events else None
    phase = verified_event["verified_phase"] if verified_event else source["reportedPhase"]
    phase_basis = ("REVIEWER_VERIFIED" if verified_event
                   else ("PROVISIONAL_REGISTRY_REPORT" if phase in PHASES
                         else "VERIFY_PHASE_FIRST"))
    if phase in PHASES and phase not in source["reportedPhases"] and verified_event:
        # A newer registry source may be required, but never silently override
        # an independently signed phase from an earlier source snapshot.
        phase_basis = "VERIFIED_PHASE_REQUIRES_SOURCE_RECONCILIATION"
    reviews = {}
    for review in historical["reviewEvents"]:
        if not verified_event or review["phase_event_id"] != verified_event["phase_event_id"]:
            continue
        key = (review["assessment_index"], review["method_index"])
        if key not in reviews or (review["revision"], review["created_at"]) > (
            reviews[key]["revision"], reviews[key]["created_at"]
        ):
            reviews[key] = review
    gaps = {}
    for g in historical["explicitGapEvents"]:
        if g["method_index"] is not None:
            gaps.setdefault((g["assessment_index"], g["method_index"]), []).append({
                "gapCode": g["gap_code"], "note": g["evidence_note"],
                "recordedAt": g["recorded_at"]})
    out = []
    flat = []
    policy = data["phasePriority"]
    for assessment_index, a in enumerate(data["assessments"], start=1):
        tier, applicability = _priority(a["id"], phase, policy)
        methods = []
        scored = []
        excluded = 0
        for item in data["methods"]:
            i = item["id"]
            review = reviews.get((assessment_index, i))
            status = review["disposition"] if review else "NOT_REVIEWED"
            if status == "RETRACTED":
                status = "NOT_REVIEWED"
            grade = review["grade"] if status == "SCORED" else None
            if status == "SCORED":
                scored.append(grade)
            elif status == "NOT_APPLICABLE":
                excluded += 1
            row = {"id": a["id"] + ":L" + str(i), "methodIndex": i,
                   "method": item["name"], "methodDescription": item["method"],
                   "question": ("For " + a["label"] + ": " + a["objective"]
                                + "; investigate whether " + a["failureMechanism"].lower() + "."),
                   "requiredSources": a["requiredSources"],
                   "deliverable": item["deliverable"],
                   "priorityTier": tier, "phaseApplicability": applicability,
                   "priorityRank": None, "grade": grade, "gradeStatus": status,
                   "evidenceGaps": gaps.get((assessment_index, i), []),
                   "review": None if not review or status == "NOT_REVIEWED" else {
                       "reviewEventId": review["review_event_id"],
                       "revision": review["revision"], "reviewerId": review["reviewer_id"],
                       "rationale": review["rationale"], "evidence": review["evidence"],
                       "evidenceReviewedAt": review["evidence_reviewed_at"]}}
            methods.append(row)
            flat.append((ORDER[tier], -WEIGHTS[i-1], assessment_index, i, row))
        pending = 20 - len(scored) - excluded
        if len(scored) + excluded == 20:
            status = "COMPLETE" if scored else "NOT_APPLICABLE"
        elif scored or excluded:
            status = "PROVISIONAL"
        else:
            status = "NOT_REVIEWED"
        provisional = round(sum(scored) / len(scored) * 20, 2) if scored else None
        out.append({"assessmentId": a["id"], "assessmentIndex": assessment_index,
                    "layerId": a["layerId"], "label": a["label"],
                    "objective": a["objective"], "failureMechanism": a["failureMechanism"],
                    "requiredSources": a["requiredSources"],
                    "gradeStatus": status, "finalScore": provisional if status == "COMPLETE" else None,
                    "provisionalScore": provisional if status == "PROVISIONAL" else None,
                    "scoredMethods": len(scored), "excludedMethods": excluded,
                    "unreviewedMethods": pending, "methods": methods})
    if phase in PHASES:
        for rank, (_, _, _, _, row) in enumerate(sorted(flat), start=1):
            row["priorityRank"] = rank
    return {
        "nct": nct, "sourceRunId": historical["sourceRunId"],
        "sourceCompletedAt": historical["sourceCompletedAt"],
        "sourceResearchStages": 12, "phase": phase,
        "phaseBasis": phase_basis, "registry": source,
        "phaseEvents": phase_events,
        "latestVerifiedClinicalMilestone": None,
        "priorCompletedPhaseBenchmark": None,
        "phaseRiskQuestions": [{"domain": x["domain"], "question": x["question"],
                                "status": "PROMPT_NOT_OBSERVED_RISK"}
                               for x in data["phaseRiskWatchlist"].get(phase, data["phaseRiskWatchlist"]["UNKNOWN"])],
        "observedClinicalRiskFindings": [],
        "investigationPriority": {"status": phase_basis,
                                  "rankedPositions": 800 if phase in PHASES else 0,
                                  "totalPositions": 800,
                                  "isScientificResult": False},
        "assessments": out, "assessmentCount": 40, "methodsPerAssessment": 20,
        "testPositions": 800,
        "reviewedMethodPositions": sum(
            a["scoredMethods"] + a["excludedMethods"] for a in out),
        "completedAssessmentCount": sum(a["gradeStatus"] == "COMPLETE" for a in out),
        "scientificSignoff": False,
        "fdaPredictions": {"approval": "ABSTAIN", "crl": "ABSTAIN",
                           "reviewDelay": "ABSTAIN"},
        "certainty": "NOT_VALIDATED",
        "note": "Priorities are research order, not observed medical risks. "
                "Recorded source stages are not reviewed or scored clinical tests."
    }


def coverage(engine) -> dict:
    from . import medical_assessment_ledger as ledger
    core = ledger.coverage(engine)
    info = catalog()
    ready = core["status"] == "READY_FOR_REVIEW" and core["canonicalTrials"] == 29
    return {"status": "READY_FOR_PHASE_REVIEW" if ready else "INCOMPLETE",
            "trialCount": core["canonicalTrials"],
            "sourceComplete": core["sourceComplete"],
            "sourceStages": core["sourceStageCount"],
            "subjectLayers": len(info["layers"]), "assessments": len(info["assessments"]),
            "methodsPerAssessment": len(info["methods"]),
            "positionsPerTrial": 800,
            "totalPotentialPositions": core["canonicalTrials"] * 800,
            "phaseVerifiedNcts": core["phaseVerifiedNcts"],
            "savedReviewEvents": core["reviewEvents"],
            "scientificSignoff": False, "fdaPrediction": "ABSTAIN",
            "certainty": "NOT_VALIDATED",
            "sourceCatalog": info["source"],
            "note": "These are investigation positions, not completed scientific reviews."}


def install_routes(app, engine_provider, require_key, require_storage) -> None:
    """Authenticated, read-only matrix endpoints, no reviewer write API."""
    router = APIRouter(prefix="/api/internal/medical-phase-matrix",
                       dependencies=[Depends(require_key), Depends(require_storage)])

    @router.get("/coverage")
    def get_coverage():
        return coverage(engine_provider())

    @router.get("/{nct}")
    def get_matrix(nct: str):
        try:
            return matrix(engine_provider(), nct)
        except ValueError:
            raise HTTPException(422, "An exact NCT from FOCUS is required")
        except LookupError:
            raise HTTPException(404, "Research and phase ledger not found")

    app.include_router(router)
