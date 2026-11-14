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
    # Multi-phase trials must not depend on the order of registry phase tags.
    order = {"EARLY_PHASE1": 0, "PHASE1": 1, "PHASE2": 2, "PHASE3": 3, "PHASE4": 4}
    status_value = registry.get("status")
    verified = eligible and bool(phases) and all(phase in known for phase in phases) and bool(status_value)
    phase = max(phases, key=order.__getitem__) if verified else None
    status = status_value if verified else None
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
    design = registry.get("study_design") or {}
    design_info = design.get("designInfo") or {}
    endpoints = registry.get("primary_outcomes") or []
    evidence_inventory = {
        "registry phase and status": "OBSERVED" if verified else "UNVERIFIED",
        "trial design": ("OBSERVED" if verified and design_info else "MISSING" if verified else "UNVERIFIED"),
        "primary endpoint definition": ("OBSERVED" if verified and endpoints and all(
            isinstance(item, dict) and item.get("measure") and item.get("timeFrame") for item in endpoints
        ) else "MISSING" if verified else "UNVERIFIED"),
    }
    # Registry design metadata cannot establish clinical efficacy, safety, or
    # regulatory dossier completeness. These require separate source review.
    if verified and "phase-appropriate efficacy and safety evidence" in expected:
        evidence_inventory["phase-appropriate efficacy and safety evidence"] = "NOT_ASSESSED"
    missing = ([name for name, state in evidence_inventory.items() if state == "MISSING"]
               if verified else ["Verified phase and chronological registry provenance"])
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
        "evidenceInventory": evidence_inventory,
        "notYetExpected": not_yet_expected,
        "missingEvidence": missing,
        "requiresSourceReview": [name for name, state in evidence_inventory.items() if state == "NOT_ASSESSED"],
        "note": "OBSERVED means present in eligible registry metadata, not clinically adjudicated. NOT_ASSESSED requires separate source review; it is not missing evidence or scientific scoring.",
    }
