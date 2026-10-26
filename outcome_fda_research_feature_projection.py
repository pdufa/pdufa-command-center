"""Strict research-only feature projection from FDA receipt as-of audit.

No retrospective final FDA decision, unverified receipt, future sponsor
publication, or post-cutoff evidence may enter the as-of feature projection.
This does not certify the projected features for predictive modeling.
"""
from __future__ import annotations
import json
from outcome_fda_receipt_asof_audit import build_receipt_asof_audit

ALLOWED_RESEARCH_FIELDS = frozenset({
    "sponsor_submission_month_asof",
    "sponsor_exact_submission_day_asof",
    "sponsor_reported_acceptance_day_asof",
})

def build_research_feature_projection(asof: str) -> dict:
    audit = build_receipt_asof_audit(asof)
    rows = []
    for record in audit["records"]:
        fields = {key: record[key] for key in ALLOWED_RESEARCH_FIELDS}
        if not record["sponsor_submission_confirmation_public"]:
            assert fields["sponsor_submission_month_asof"] is None
        if not record["sponsor_exact_submission_day_public"]:
            assert fields["sponsor_exact_submission_day_asof"] is None
        if not record["sponsor_acceptance_disclosure_public"]:
            assert fields["sponsor_reported_acceptance_day_asof"] is None
        if any("fda_action" in key or "final_action" in key for key in fields):
            raise AssertionError("FDA retrospective outcome leaked into feature fields")
        rows.append({
            "application_key": record["application_key"],
            "submission_key": record["submission_key"],
            "asof_date": asof,
            "research_observations": fields,
            "historical_feature_asof_certified": False,
            "model_eligible": False,
        })
    return {
        "schema_version": "outcome-fda-research-feature-projection-v1",
        "dataset_role": "research_only_nontraining",
        "asof_date": asof,
        "selected_open_fda_receipt_denominator": len(rows),
        "allowed_observation_fields": sorted(ALLOWED_RESEARCH_FIELDS),
        "retrospective_fda_action_labels_excluded": True,
        "unverified_fda_receipt_dates_excluded": True,
        "historical_feature_asof_certified": False,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "records": rows,
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python outcome_fda_research_feature_projection.py YYYY-MM-DD")
    print(json.dumps(build_research_feature_projection(sys.argv[1]), sort_keys=True, indent=2))
