# Historical FDA outcome cohort — quarantine audit

This is an **offline, read-only diagnostic**, not a source adjudicator, FDA
approval-rate calculator, predictive model, or permission to trade. The
historical outcome intake is deliberately quarantined, even if its format is
valid. This work does not modify the PDUFA scanner or GEM JR, GEM, WT, FS/FA
presets.

## Run

From repository root:

```sh
PYTHONPATH=new-platform/backend python new-platform/backend/scripts/audit_hop_outcome_cohort.py \
  new-platform/backend/data/hop_historical_outcomes_template.csv --as-of 2026-10-25
```

The checked-in CSV is header-only and is **not** a historical FDA cohort. The
expected result is `QUARANTINED_REVIEW_ONLY`, zero staged records and a
nonzero CLI exit code. For a locally curated CSV, schema-validated results may
return exit code zero, but that means **only** the CSV format is internally
consistent; all model and probability fields remain blocked.

## What the report means

- `staged_csv_rows`: syntactically accepted, **not independently verified** rows.
- `rejected_csv_rows` and `rejected_rows_by_reason`: blocked input rows and
  validation issues, including duplicate review-cycle and temporal-leakage errors.
- `unverified_outcome_claims_by_type`: labels **claimed** in an offline CSV;
  not demonstrated FDA actions.
- `unverified_application_claims_by_type` and
  `unverified_decision_year_claims`: file composition, not a complete FDA
  denominator or representative historical trend.
- `unmet_release_gates`: source adjudication, complete application denominator,
  predecision evidence provenance, independent review and time-forward calibration
  are **not demonstrated** by this tool.
- `approval_rate: null`, `prediction_probability: null`,
  `model_eligible_records: 0`, `prediction_available: false` are invariant.
  Do not substitute a fraction of accepted CSV rows for a real approval rate.

The importer checks **three different dates**: decision date,
`public_features_as_of` strictly before the FDA decision, and
`evidence_as_of` on or after the decision. Postdecision outcome evidence must
not enter a predecision prediction. An FDA-domain URL is not sufficient to
verify the content or actual action date of its referenced letter.

## Before moving toward a real prospective model

Independent reviewers must attribute original FDA action letters to exact NDA,
BLA or ANDA applications, indications and review cycles; reconcile **both**
approval and nonapproval outcomes using a complete sampling frame; establish
point-in-time source evidence and a freeze cutoff for every feature; and pass
prespecified chronological holdout tests for discrimination, calibration,
uncertainty and bias. Until then, keep quantitative predictions unassigned.

All automated test fixtures in this change are fictional. No new FDA download,
database write, import, background job, model training or release is performed.
