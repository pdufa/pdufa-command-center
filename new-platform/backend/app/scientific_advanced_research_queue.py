"""Stable exact-trial Levels 9–20 scientific evidence research queue.

This is a queue of missing SOURCE-REVIEW TASKS, not assessment scores, an
automated crawler, a scientific acceptance workflow, or an FDA forecast.
It does not create or claim any source review. No repository or database writes.
"""
from __future__ import annotations
from datetime import date
import re

from .scientific_levels_nine_to_twenty import LEVELS
from .scientific_research_avenues import candidate_research_avenues

VERSION = "scientific-advanced-research-queue-v1"
_VALID_STATES = {
    "REJECTED_EVIDENCE": (0, "RESOLVE_REJECTED_SOURCE", "Resolve rejected identity, chronology, provenance or conflict before re-review."),
    "UNVERIFIED_UNPUBLISHED_CLAIM": (1, "VERIFY_PUBLICATION_CLAIM", "Verify the claimed lack of public evidence using an original dated source."),
    "NOT_ASSESSED": (2, "COLLECT_AND_REVIEW_SOURCE", "Find relevant dated, exact-trial evidence and record source-review provenance."),
    "UNPUBLISHED": (3, "RECHECK_REPORTED_UNPUBLISHED", "Recheck the source-reviewed unavailable evidence claim; absence is not a negative finding."),
}
_ACCEPTED = {"SUPPORTS", "CONCERNS", "INCONCLUSIVE"}


def _base(trial_id, cutoff):
    return {
        "methodVersion": VERSION,
        "nctId": trial_id,
        "asOf": cutoff,
        "scope": "SCIENTIFIC_LEVELS_09_TO_20",
        "status": "BLOCKED_UNVERIFIED_INTAKE",
        "tasks": [],
        "deferred": [],
        "reviewedCriteria": 0,
        "unresolvedCriteria": 0,
        "sourceReviewCompletion": "NOT_ESTABLISHED",
        "score": None,
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "rankingMeaning": "Deterministic source-review workflow order, not scientific priority, predictive confidence, severity, or FDA probability.",
    }


def build_advanced_research_queue(intake, levels, *, trial_id):
    cutoff = intake.get("assessmentCutoff") if isinstance(intake, dict) else None
    result = _base(trial_id, cutoff)
    try:
        valid_cutoff = isinstance(cutoff, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cutoff) and date.fromisoformat(cutoff)
    except ValueError:
        valid_cutoff = False
    if (not isinstance(intake, dict) or
            intake.get("executionStatus") != "INTAKE_ONLY" or
            intake.get("scientificValidation") != "NOT_VERIFIED" or
            intake.get("fdaPrediction") != "ABSTAIN" or
            intake.get("phase") not in {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"} or
            not isinstance(trial_id, str) or re.fullmatch(r"NCT[0-9]{8}", trial_id) is None or
            not valid_cutoff or not isinstance(levels, dict) or
            set(levels) != {str(i) for i in range(9, 21)}):
        return result
    tasks, deferred, reviewed_count = [], [], 0
    for number, (_, expected) in LEVELS.items():
        record = levels.get(str(number))
        if (not isinstance(record, dict) or record.get("level") != number or
                record.get("nctId") != trial_id or
                record.get("score") is not None or
                record.get("scientificValidation") != "NOT_VERIFIED" or
                record.get("fdaPrediction") != "ABSTAIN" or
                record.get("status") == "BLOCKED_UNVERIFIED_PHASE" or
                not isinstance(record.get("criteria"), dict) or
                set(record["criteria"]) != set(expected) or
                not isinstance(record.get("acceptedEvidence"), dict)):
            return result
        accepted = record["acceptedEvidence"]
        for criterion in expected:
            state = record["criteria"][criterion]
            task_id = f"{trial_id}:L{number:02d}:{criterion}"
            if state == "NOT_YET_EXPECTED":
                deferred.append({
                    "id": task_id, "level": number,
                    "criterion": criterion, "state": state,
                    "reason": "Not expected at this trial phase/status; not missing or failed.",
                })
            elif state in _ACCEPTED:
                if criterion not in accepted:
                    return result
                reviewed_count += 1
            elif state in _VALID_STATES:
                rank, action, reason = _VALID_STATES[state]
                reason_code = (record.get("rejectionReasons") or {}).get(criterion)
                tasks.append({
                    "id": task_id, "level": number, "criterion": criterion,
                    "state": state, "action": action, "reason": reason,
                    "rejectionReason": reason_code if isinstance(reason_code, str) else None,
                    "workflowClass": rank,
                })
            else:
                return result
    tasks.sort(key=lambda v: (v["workflowClass"], v["level"], v["criterion"]))
    for rank, task in enumerate(tasks, 1):
        task["priorityOrder"] = rank
        task.pop("workflowClass")
    return {
        **result,
        "status": "RESEARCH_QUEUE_READY" if tasks else "NO_ACTIVE_GAPS_NOT_SCIENTIFIC_VALIDATION",
        "tasks": tasks,
        "deferred": deferred,
        "reviewedCriteria": reviewed_count,
        "unresolvedCriteria": len(tasks),
        "researchAvenues": candidate_research_avenues(trial_id),
    }


def compact_historical_research_queue(queue):
    """Bounded auditable queue history; no copied excerpts or sensitive source text.

    Keep states and exact criterion identities so each dated version can be
    compared; task actions can be derived from the immutable state catalog.
    """
    if not isinstance(queue, dict) or queue.get("methodVersion") != VERSION:
        raise ValueError("Invalid research queue for historical summary")
    tasks, deferred = queue.get("tasks"), queue.get("deferred")
    if not isinstance(tasks, list) or not isinstance(deferred, list):
        raise ValueError("Invalid historical queue items")
    if len(tasks) > 60 or len(deferred) > 60:
        raise ValueError("Research queue exceeds fixed 60-criterion inventory")
    states = []
    for task in tasks:
        if (not isinstance(task, dict) or task.get("state") not in _VALID_STATES
                or not isinstance(task.get("id"), str)):
            raise ValueError("Invalid historical task state or identity")
        states.append([task["id"], task["state"], task.get("rejectionReason")])
    deferred_ids = []
    for item in deferred:
        if (not isinstance(item, dict) or item.get("state") != "NOT_YET_EXPECTED"
                or not isinstance(item.get("id"), str)):
            raise ValueError("Invalid historical deferred task")
        deferred_ids.append(item["id"])
    return {
        "methodVersion": VERSION,
        "nctId": queue["nctId"],
        "asOf": queue["asOf"],
        "status": queue["status"],
        "reviewedCriteria": queue["reviewedCriteria"],
        "unresolvedCriteria": queue["unresolvedCriteria"],
        "taskStates": states,
        "deferredTaskIds": deferred_ids,
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "score": None,
        "note": "Saved source-workflow states only. Not validated scientific scores or FDA predictions.",
    }
