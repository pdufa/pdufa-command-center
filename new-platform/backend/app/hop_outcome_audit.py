"""Offline diagnostics for quarantined historical FDA outcome *claims*.

This module does not verify source contents or calculate approval rates.  In
particular, FDA published-letter and approved-registry samples are not a
complete denominator of application review-cycle decisions.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .hop_outcomes_import import ALLOWED_OUTCOMES, HistoricalOutcomeRecord

GATES_NOT_MET = (
    "independently_adjudicated_exact_fda_action_and_review_cycle",
    "complete_approval_and_nonapproval_application_denominator",
    "independently_verified_point_in_time_trial_features",
    "independent_reviewer_signoff",
    "chronological_out_of_sample_validation_and_calibration",
)

_VALID_STATES = frozenset({
    "SCHEMA_VALIDATED_REVIEW_REQUIRED", "REVIEW_REQUIRED", "REJECTED_SCHEMA",
})


def audit_quarantined_outcome_intake(intake: dict[str, Any]) -> dict[str, Any]:
    """Summarize staged claims without converting them into outcomes or scores.

    Reject internally contradictory input, including any claim of model
    clearance.  Counts describe CSV entries, not verified FDA decisions.
    """
    if not isinstance(intake, dict) or intake.get("status") not in _VALID_STATES:
        raise ValueError("Unknown outcome intake status")

    records = intake.get("records")
    accepted = intake.get("accepted")
    rejected = intake.get("rejected")
    if (not isinstance(records, list)
            or type(accepted) is not int or accepted < 0
            or type(rejected) is not int or rejected < 0
            or len(records) != accepted
            or any(not isinstance(r, HistoricalOutcomeRecord) for r in records)
            or intake.get("model_eligible_records") != 0
            or intake.get("independently_verified") is not False
            or intake.get("probability") is not None):
        raise ValueError("Contradictory or model-eligible outcome intake")

    state = intake["status"]
    if ((state == "REJECTED_SCHEMA" and (accepted != 0 or rejected != 0))
            or (state == "SCHEMA_VALIDATED_REVIEW_REQUIRED"
                and (accepted == 0 or rejected != 0))
            or (state == "REVIEW_REQUIRED" and accepted > 0 and rejected == 0)):
        raise ValueError("Inconsistent outcome intake status/counts")

    rejected_entries = intake.get("rejections", [])
    if (not isinstance(rejected_entries, list)
            or (state != "REJECTED_SCHEMA" and len(rejected_entries) != rejected)
            or (state == "REJECTED_SCHEMA" and rejected_entries)):
        raise ValueError("Inconsistent outcome rejection details")

    reason_counts: Counter[str] = Counter()
    for entry in rejected_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("errors"), list):
            raise ValueError("Malformed rejection entry")
        reasons = entry["errors"]
        if not reasons or any(not isinstance(r, str) or not r for r in reasons):
            raise ValueError("Malformed rejection reason")
        reason_counts.update(set(reasons))

    label_counts: Counter[str] = Counter()
    app_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    for record in records:
        if record.outcome not in ALLOWED_OUTCOMES:
            raise ValueError("Unknown unverified outcome claim")
        prefix = record.application_id[:3]
        if prefix not in {"NDA", "BLA", "AND"}:
            raise ValueError("Unknown application ID")
        if prefix == "AND" and not record.application_id.startswith("ANDA"):
            raise ValueError("Unknown application ID")
        label_counts[record.outcome] += 1
        app_counts["ANDA" if prefix == "AND" else prefix] += 1
        year_counts[str(record.decision_date.year)] += 1

    return {
        "status": "QUARANTINED_REVIEW_ONLY",
        "intake_status": state,
        "staged_csv_rows": accepted,
        "rejected_csv_rows": rejected,
        "unverified_outcome_claims_by_type": {
            key: label_counts[key] for key in sorted(ALLOWED_OUTCOMES)
        },
        "unverified_application_claims_by_type": {
            key: app_counts[key] for key in ("NDA", "BLA", "ANDA")
        },
        "unverified_decision_year_claims": dict(sorted(year_counts.items())),
        "rejected_rows_by_reason": dict(sorted(reason_counts.items())),
        "independently_verified_review_cycle_outcomes": 0,
        "model_eligible_records": 0,
        "complete_decision_denominator_verified": False,
        "model_validated": False,
        "prediction_available": False,
        "prediction_probability": None,
        "approval_rate": None,
        "unmet_release_gates": list(GATES_NOT_MET),
        "note": (
            "Counts are unverified CSV claims, not measured FDA outcomes. "
            "No approval fraction, model fit, clinical score, or trading signal is authorized."
        ),
    }
