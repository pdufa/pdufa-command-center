"""Read-only 40 x 20 view of *independent* medical assessment revisions.

Never project source-triage positions or phase registry snapshots into grades.
A review belongs to the current, explicitly verified phase event; superseded
phase evidence and retracted grades remain visible only in historical records.
This is evidence-strength reporting, not FDA prediction or clinical signoff.
"""
from __future__ import annotations

import re
from collections import Counter

from .medical_grading_policy import grading_policy

POSITIONS_PER_ASSESSMENT = 20
ASSESSMENTS = 40
STATES = ("SCORED", "NOT_APPLICABLE", "RETRACTED", "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE")


def project_trial_history(history: dict, *, assessment_index: int | None = None) -> dict:
    """Project latest, phase-matched reviewer events without writing or regrading.

    When assessment_index is None, return 40 compact assessment summaries.
    On selection, return the exact 20-method drill-down for that assessment.
    The full append-only history remains available from the history endpoint.
    """
    nct = history.get("nct")
    if not isinstance(nct, str) or not re.fullmatch(r"NCT\d{8}", nct):
        raise ValueError("An exact NCT is required")
    if assessment_index is not None and (type(assessment_index) is not int or not 1 <= assessment_index <= ASSESSMENTS):
        raise ValueError("Select a scientific assessment from 1 to 40")
    phases = history.get("phaseEvents") or []
    current = phases[-1] if phases else None
    phase = current.get("verified_phase") if current else None
    phase_event_id = current.get("phase_event_id") if current else None
    if current and (not phase or not phase_event_id):
        raise ValueError("Latest phase review event is incomplete")

    # Only current phase-matched events can count. A changed/reverified phase
    # requires fresh examination, even when the phase label is unchanged.
    latest = {}
    revisions = {}
    seen_revisions = set()
    stale_positions = set()
    for review in history.get("reviewEvents") or []:
        a, m, rev = review.get("assessment_index"), review.get("method_index"), review.get("revision")
        if (type(a) is not int or not 1 <= a <= ASSESSMENTS or
                type(m) is not int or not 1 <= m <= POSITIONS_PER_ASSESSMENT or
                type(rev) is not int or rev < 1):
            raise ValueError("Stored scientific review has an invalid position or revision")
        key = (a, m)
        # Revision numbers are scoped to a phase label in the durable ledger.
        revision_key = (review.get("verified_phase"), a, m, rev)
        if revision_key in seen_revisions:
            raise ValueError("Duplicate review revision")
        seen_revisions.add(revision_key)
        revisions.setdefault(key, []).append(review)
        if not current or review.get("verified_phase") != phase or review.get("phase_event_id") != phase_event_id:
            stale_positions.add(key)
            continue
        before = latest.get(key)
        if before is None or rev > before["revision"]:
            latest[key] = review
        elif rev == before["revision"]:
            raise ValueError("Duplicate latest review revision")

    totals = Counter({key: 0 for key in STATES})
    assessments = []
    detail = None
    for a in range(1, ASSESSMENTS + 1):
        counts = Counter({key: 0 for key in STATES})
        scored = []
        methods = []
        for m in range(1, POSITIONS_PER_ASSESSMENT + 1):
            review = latest.get((a, m))
            if not current:
                state = "VERIFY_PHASE"
            elif review:
                state = review.get("disposition")
                if state not in ("SCORED", "NOT_APPLICABLE", "RETRACTED"):
                    raise ValueError("Unknown reviewer disposition")
            else:
                state = "STALE_PHASE" if (a, m) in stale_positions else "UNREVIEWED"
            grade = review.get("grade") if state == "SCORED" else None
            if state == "SCORED":
                if type(grade) is not int or not 0 <= grade <= 5:
                    raise ValueError("Verified scientific grade must be 0–5")
                scored.append(grade)
            counts[state] += 1
            if assessment_index == a:
                method_history = sorted(revisions.get((a, m), []),
                                        key=lambda r: (r.get("created_at", ""),
                                                       r["revision"], r.get("review_event_id", "")))
                gaps = [dict(g) for g in history.get("explicitGapEvents", [])
                        if g.get("assessment_index") == a
                        and g.get("method_index") in (None, m)]
                methods.append({
                    "methodIndex": m, "status": state, "grade": grade,
                    "reviewEventId": review.get("review_event_id") if review else None,
                    "revision": review.get("revision") if review else None,
                    "reviewedAt": review.get("evidence_reviewed_at") if review else None,
                    "reviewerId": review.get("reviewer_id") if review else None,
                    "rationale": review.get("rationale") if review else None,
                    "sourceEvidence": review.get("evidence", []) if review else [],
                    # Historical evidence is shown verbatim, never promoted
                    # into the current phase's grade or completion count.
                    "history": [dict(r) for r in method_history],
                    "evidenceGaps": gaps,
                    "gapResolutionStatus": "NOT_ADJUDICATED" if gaps else "NO_RECORDED_GAP",
                })
        totals.update(counts)
        eligible = POSITIONS_PER_ASSESSMENT - counts["NOT_APPLICABLE"]
        unready = counts["VERIFY_PHASE"] + counts["UNREVIEWED"] + counts["STALE_PHASE"] + counts["RETRACTED"]
        rating = round(sum(scored) / len(scored) * 20, 1) if scored else None
        if not current:
            status = "VERIFY_PHASE"
        elif not eligible:
            status = "NOT_APPLICABLE"
        elif not scored:
            status = "NOT_REVIEWED"
        elif unready:
            status = "PROVISIONAL"
        else:
            status = "COMPLETE"
        row = {"assessmentIndex": a, "status": status, "scoreOutOf100": rating,
               "reviewedMethods": len(scored), "excludedMethods": counts["NOT_APPLICABLE"],
               "pendingMethods": unready, "applicableMethods": eligible}
        assessments.append(row)
        if assessment_index == a:
            detail = {**row, "methods": methods}

    return {
        "schema": "EXACT_NCT_REVIEWED_METHOD_MATRIX_V1", "nct": nct,
        "verifiedPhase": phase, "phaseEventId": phase_event_id,
        "status": ("VERIFY_PHASE" if not current else
                   "PHASE_VERIFIED_NOT_REVIEWED" if not totals["SCORED"] and not totals["NOT_APPLICABLE"] else
                   "PHASE_VERIFIED_REVIEW_COMPLETE" if all(a["pendingMethods"] == 0 for a in assessments) else
                   "PHASE_VERIFIED_REVIEW_PARTIAL"),
        "totalPositions": ASSESSMENTS * POSITIONS_PER_ASSESSMENT,
        "counts": dict(totals),
        "assessments": assessments,
        "selectedAssessment": detail,
        "historicalReviewEvents": len(history.get("reviewEvents") or []),
        "phaseHistory": [dict(p) for p in phases],
        "recordedGapEvents": len(history.get("explicitGapEvents") or []),
        "gradingPolicy": grading_policy(),
        "clinicalSignoff": False,
        "fdaPredictions": {"APPROVAL": "ABSTAIN", "CRL": "ABSTAIN", "REVIEW_DELAY": "ABSTAIN"},
        "certainty": "NOT_VALIDATED",
        "note": "Only current phase-event reviewer grades are counted. No source lead, stale grade, or missing evidence is a clinical result.",
    }
