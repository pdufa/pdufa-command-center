"""Level 1 phase-first evidence intake, not a validated scientific prediction.

Never infer phase from trial status or the candidate's PDUFA date. Registry
snapshots dated after the assessment cutoff are ineligible for scoring.
"""
from __future__ import annotations

from datetime import date


def _date(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def phase_first_intake(registry, *, cutoff, registry_checked):
    """Return an auditable, non-scoring Level 1 phase intake."""
    cutoff_day = _date(cutoff)
    checked_day = _date(registry_checked)
    updated = _date((registry.get("last_update_posted") or {}).get("date"))
    eligible = bool(cutoff_day and checked_day and updated
                    and updated <= checked_day <= cutoff_day)
    phases = registry.get("phases") or registry.get("phase") or []
    if isinstance(phases, str):
        phases = [phases]
    if not isinstance(phases, (list, tuple)):
        phases = []
    phases = [str(phase).upper().replace(" ", "") for phase in phases]
    known = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"}
    verified = eligible and bool(phases) and all(phase in known for phase in phases)
    phase = phases[-1] if verified else None
    status = registry.get("status") if verified else None
    expected = []
    not_yet_expected = []
    if verified:
        expected = ["registry phase and status", "trial design", "primary endpoint definition"]
        if phase in {"PHASE2", "PHASE3", "PHASE4"}:
            expected.append("phase-appropriate efficacy and safety evidence")
        else:
            not_yet_expected.append("pivotal efficacy or marketing-application dossier")
        if phase in {"EARLY_PHASE1", "PHASE1", "PHASE2"}:
            not_yet_expected.append("completed Phase 3 results")
    return {
        "level": 1,
        "name": "Phase-first evidence intake",
        "executionStatus": "INTAKE_ONLY" if verified else "BLOCKED_UNVERIFIED_PHASE",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "phase": phase,
        "trialStatus": status,
        "registrySourceDate": updated.isoformat() if updated else None,
        "registryCheckedAt": checked_day.isoformat() if checked_day else None,
        "assessmentCutoff": cutoff_day.isoformat() if cutoff_day else None,
        "expectedEvidence": expected,
        "notYetExpected": not_yet_expected,
        "missingEvidence": [] if verified else ["Verified phase and chronological registry provenance"],
        "note": "Evidence expectations are intake categories, not proof that documents exist or scientific scores.",
    }
