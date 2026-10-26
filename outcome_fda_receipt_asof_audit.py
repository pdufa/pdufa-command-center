"""Research-only receipt evidence readiness at an explicit historical as-of date.

Never treats company statements as an FDA submission receipt or turns source
availability into model clearance. Outputs a separate, auditable provenance view.
"""
from __future__ import annotations
from datetime import date
import json
from outcome_fda_receipt_boundary_gap_report import build_receipt_boundary_gap_report

def _published_by(source_date: str | None, asof: date) -> bool:
    return source_date is not None and date.fromisoformat(source_date) <= asof

def build_receipt_asof_audit(asof: str) -> dict:
    cutoff = date.fromisoformat(asof)
    gaps = build_receipt_boundary_gap_report()
    rows = []
    for action in gaps["unlinked_actions"]:
        sponsor = action["sponsor_submission_provenance"]
        confirmation_available = _published_by(
            sponsor["sponsor_submission_publicly_confirmed_by"], cutoff)
        exact_available = _published_by(
            sponsor["sponsor_exact_day_source_published_on"], cutoff)
        acceptance_available = _published_by(
            sponsor["fda_acceptance_disclosure_published_on"], cutoff)
        sponsor_day = sponsor["sponsor_reported_exact_submission_date"]
        rows.append({
            "application_key": action["application_key"],
            "submission_key": action["submission_key"],
            "final_fda_action_date": action["final_fda_action_date"],
            "asof_date": asof,
            "sponsor_submission_confirmation_public": confirmation_available,
            "sponsor_submission_month_asof": (
                sponsor["sponsor_reported_submission_month"]
                if confirmation_available else None
            ),
            "sponsor_exact_submission_day_public": exact_available,
            "sponsor_exact_submission_day_asof": sponsor_day if exact_available else None,
            "sponsor_exact_day_source_published_on": (
                sponsor["sponsor_exact_day_source_published_on"]
            ),
            "sponsor_acceptance_disclosure_public": acceptance_available,
            "sponsor_reported_acceptance_day_asof": (
                sponsor["sponsor_reported_fda_acceptance_date"]
                if acceptance_available else None
            ),
            "fda_exact_receipt_day": None,
            "fda_receipt_independently_verified": False,
            "historical_feature_asof_certified": False,
            "model_eligible": False,
        })
    return {
        "schema_version": "outcome-fda-receipt-asof-audit-v1",
        "asof_date": asof,
        "research_only": True,
        "selected_open_fda_receipt_denominator": len(rows),
        "sponsor_submission_confirmation_public_count": sum(
            r["sponsor_submission_confirmation_public"] for r in rows),
        "sponsor_exact_day_public_count": sum(
            r["sponsor_exact_submission_day_public"] for r in rows),
        "sponsor_acceptance_disclosure_public_count": sum(
            r["sponsor_acceptance_disclosure_public"] for r in rows),
        "fda_exact_receipts_independently_verified": 0,
        "historical_feature_asof_certified": False,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "records": rows,
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python outcome_fda_receipt_asof_audit.py YYYY-MM-DD")
    print(json.dumps(build_receipt_asof_audit(sys.argv[1]), indent=2, sort_keys=True))
