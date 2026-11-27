"""Cross-check two *unverified* FDA research inputs without promoting either.

A publication-selected CRL source worklist is NOT a complete denominator.
Agreement between a historical CSV row and an adjudicator claim is not
independent review, original source verification, or training authorization.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from .hop_fda_cycle_claim_register import (
    CLAIM_FIELDS, STATUS, WORKLIST_FIELDS, prepare_claim_register,
    screen_claim_register,
)
from .hop_outcomes_import import HistoricalOutcomeRecord, ALLOWED_OUTCOMES


def crosscheck_historical_outcome_claims(
    intake: dict,
    source_queue: list[dict],
    cycle_submissions: list[dict],
    *, as_of: date,
) -> dict:
    """Diagnose source-claim mismatches, keeping *every* model gate closed.

    Intentionally does not check outcome source bytes, decision population
    coverage or signatures; it only matches syntactically valid claimed cycles.
    """
    if not isinstance(as_of, date):
        raise ValueError("A calendar cutoff is required")
    if (not isinstance(intake, dict)
            or intake.get("status") not in {"SCHEMA_VALIDATED_REVIEW_REQUIRED", "REVIEW_REQUIRED", "REJECTED_SCHEMA"}
            or intake.get("model_eligible_records") != 0
            or intake.get("independently_verified") is not False
            or intake.get("probability") is not None
            or type(intake.get("accepted")) is not int
            or type(intake.get("rejected")) is not int
            or intake["accepted"] < 0 or intake["rejected"] < 0
            or not isinstance(intake.get("records"), list)
            or len(intake["records"]) != intake["accepted"]
            or any(not isinstance(r, HistoricalOutcomeRecord) for r in intake["records"])
            or (intake["status"] == "REJECTED_SCHEMA" and intake["accepted"] != 0)
            or (intake["status"] == "SCHEMA_VALIDATED_REVIEW_REQUIRED"
                and (intake["accepted"] == 0 or intake["rejected"] != 0))):
        raise ValueError("Historical outcome intake is not quarantined or coherent")

    # Re-run the strict source/cycle audit; external claimed verification is
    # never accepted as a substitute. Reject modified identity or promotion.
    source_audit = screen_claim_register(source_queue, cycle_submissions, as_of=as_of)
    expected = {r["source_record_sha256"]: r for r in prepare_claim_register(source_queue)}
    claims_by_cycle = defaultdict(list)
    for claim in cycle_submissions:
        sid = claim["source_record_sha256"]
        if sid not in expected:
            raise ValueError("Unknown original source reference")
        if any(claim.get(key) != expected[sid][key] for key in WORKLIST_FIELDS):
            raise ValueError("Original FDA published source linkage changed")
        if not all(claim[field].strip() for field in CLAIM_FIELDS):
            continue
        if claim["claimed_fda_action_type"] not in ALLOWED_OUTCOMES:
            continue
        key = (claim["claimed_application_id"].replace("-", ""),
               int(claim["claimed_review_cycle"]))
        claims_by_cycle[key].append(claim)

    records_seen = set()
    case_ids = set()
    decisions = []
    reason_totals = Counter()
    for record in intake["records"]:
        if record.case_id in case_ids:
            raise ValueError("Duplicated historical case identifier")
        case_ids.add(record.case_id)
        key = (record.application_id, record.review_cycle)
        if key in records_seen:
            raise ValueError("Duplicated historical application and review cycle")
        records_seen.add(key)
        if (record.outcome not in ALLOWED_OUTCOMES
                or record.decision_date > as_of
                or record.public_features_as_of >= record.decision_date
                or record.evidence_as_of < record.decision_date
                or record.evidence_as_of > as_of):
            raise ValueError("Historical outcome record violated chronological quarantine")
        claims = claims_by_cycle.get(key, [])
        reasons = []
        if not claims:
            reasons.append("NO_MATCHING_PUBLISHED_SOURCE_CYCLE_CLAIM")
        elif len(claims) > 1:
            reasons.append("AMBIGUOUS_MULTIPLE_PUBLISHED_LETTER_REFERENCES")
            if len({(c["claimed_fda_action_type"], c["claimed_fda_action_date"])
                    for c in claims}) > 1:
                reasons.append("CONFLICTING_SOURCE_ACTION_OR_DATE_CLAIMS")
        if claims:
            if not any(c["claimed_fda_action_date"] == record.decision_date.isoformat()
                       for c in claims):
                reasons.append("FDA_ACTION_DATE_MISMATCH")
            if not any(c["claimed_fda_action_type"] == record.outcome for c in claims):
                reasons.append("FDA_ACTION_LABEL_MISMATCH")
            if not any(record.source_url in {
                c["fda_pdf_url"], c["claimed_independent_fda_url"]
            } for c in claims):
                reasons.append("OUTCOME_SOURCE_URL_NOT_LINKED_TO_REVIEW_CLAIM")
        if not reasons:
            reasons.append("MATCHING_UNVERIFIED_CLAIMS_REQUIRES_HUMAN_ADJUDICATION")
        reason_totals.update(reasons)
        decisions.append({
            "case_id": record.case_id,
            "application_id": record.application_id,
            "review_cycle": record.review_cycle,
            "status": "QUARANTINED_REVIEW_REQUIRED",
            "diagnostic_reasons": reasons,
            "candidate_source_references": len(claims),
            "independently_verified": False,
            "model_eligible": False,
        })
    return {
        "status": "UNVERIFIED_OUTCOME_TO_SOURCE_CYCLE_CROSSCHECK",
        "historical_csv_intake_status": intake["status"],
        "staged_historical_outcome_rows": len(decisions),
        "rejected_historical_csv_rows": intake["rejected"],
        "source_selected_letter_references": source_audit["published_source_references"],
        "cycle_claim_audit_status": source_audit["status"],
        "diagnostic_reason_counts": dict(sorted(reason_totals.items())),
        "case_diagnostics": decisions,
        "independent_fda_review_cycle_decisions_verified": 0,
        "complete_fda_approval_nonapproval_denominator_verified": False,
        "chronological_predictive_calibration_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "This compares unverified historical CSV entries with unverified "
            "review-cycle assertions from a publication-selected FDA letter "
            "collection. A textual match is not FDA outcome verification."
        ),
    }
