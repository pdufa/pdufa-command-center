"""Conservative FDA historical decision-label eligibility gate.

Research only. A candidate record is not automatically a training example.
No live forecasts, trading actions, or dataset mutations are performed.
"""
from datetime import date
import re
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
        try:
            parsed = urlparse(source)
            trusted = (parsed.scheme == "https" and parsed.hostname in {
                "fda.gov", "www.fda.gov", "accessdata.fda.gov", "www.accessdata.fda.gov",
                "download.open.fda.gov"
            } and parsed.username is None and parsed.password is None
                and parsed.port is None and not parsed.fragment and parsed.path not in {"", "/"})
        except ValueError:
            trusted = False
        if not trusted:
            reasons.append("unverified_fda_source_domain")
    if not record.get("application_id"):
        reasons.append("missing_application_id")
    cycle = record.get("review_cycle_id")
    if (not isinstance(cycle, str) or not cycle.strip() or any(
            token in cycle.casefold() for token in
            ("unverified", "unknown", "unresolved", "pending", "not_verified", "not verified"))):
        reasons.append("missing_review_cycle_id")
    try:
        action_text = record["action_date"]
        cutoff_text = record["evidence_cutoff_date"]
        if not all(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) for value in (action_text, cutoff_text)):
            raise ValueError("Dates must use strict YYYY-MM-DD format")
        action_date = date.fromisoformat(action_text)
        cutoff = date.fromisoformat(cutoff_text)
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
