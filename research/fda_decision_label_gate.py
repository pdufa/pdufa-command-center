"""Conservative FDA historical decision-label eligibility gate.

Research only. A candidate record is not automatically a training example.
No live forecasts, trading actions, or dataset mutations are performed.
"""
from datetime import date
from urllib.parse import urlparse
from typing import Mapping, Any

VALID_ACTIONS = {"approval", "complete_response_letter"}

def assess_label_eligibility(record: Mapping[str, Any]) -> dict:
    """Return an auditable abstention or eligible binary FDA action label.

    Dates must be ISO YYYY-MM-DD. Evidence cutoff must strictly precede the
    action date. This is a necessary, not sufficient, training-data gate.
    """
    reasons = []
    action = record.get("action_type")
    if action not in VALID_ACTIONS:
        reasons.append("unverified_or_unsupported_action")
    source = record.get("official_fda_action_source")
    if not isinstance(source, str) or not source:
        reasons.append("missing_official_fda_action_source")
    else:
        parsed = urlparse(source)
        if parsed.scheme != "https" or parsed.hostname not in {"fda.gov", "www.fda.gov", "accessdata.fda.gov"}:
            reasons.append("unverified_fda_source_domain")
    if not record.get("application_id"):
        reasons.append("missing_application_id")
    if not record.get("review_cycle_id"):
        reasons.append("missing_review_cycle_id")
    try:
        action_date = date.fromisoformat(record["action_date"])
        cutoff = date.fromisoformat(record["evidence_cutoff_date"])
        if cutoff >= action_date:
            reasons.append("hindsight_or_same_day_evidence")
    except (KeyError, ValueError, TypeError):
        reasons.append("invalid_or_missing_dates")
    if record.get("source_cohort") == "selected_approvals_only":
        reasons.append("selection_bias_approval_only")
    if record.get("source_cohort") == "candidate_union":
        reasons.append("candidate_union_not_representative")
    if record.get("original_filing_denominator_verified") is not True:
        reasons.append("unverified_sampling_denominator")
    if record.get("program_family_disjoint_verified") is not True:
        reasons.append("related_program_leakage_not_ruled_out")
    return {
        "status": "ABSTAIN" if reasons else "ELIGIBLE_FOR_FURTHER_REVIEW",
        "label": None if reasons else (1 if action == "approval" else 0),
        "reasons": reasons,
        "research_only": True,
        "trading_authorized": False,
    }
