# HOP historical FDA outcomes CSV intake — quarantine only

This is an **offline, schema-only intake** for separately sourced historical FDA
action records. Passing format checks is not proof of a verified decision, a
complete application cohort, or a validated prediction model. All tests are fictitious.

Template: new-platform/backend/data/hop_historical_outcomes_template.csv

## Three distinct dates

- decision_date: official FDA action date for the exact application and review cycle;
  it still requires original-document verification.
- public_features_as_of: historical trial-feature snapshot date, strictly BEFORE
  the FDA action. Modern trial records are not historical snapshots.
- evidence_as_of: date FDA outcome evidence became available, on or AFTER the
  decision. It must never be used as a predictor.

Each record also carries an exact NDA/BLA/ANDA application identity, review cycle,
drug, sponsor, indication, modality, phase, primary FDA HTTPS source and source title.
A domain-format check never proves source-page content or outcome adjudication.

All parseable identity claims are reconciled before row-quality filtering.
Repeated trimmed case IDs or canonical application/cycle identities reject every
member row, including claims with invalid dates, missing fields or invalid
sources. An invalid claim cannot disappear and leave a contradictory sibling
apparently unique. Each rejected row retains its logical CSV record number
(header is 1) and combined reasons. The `line` field is a record number for
multiline quoted CSV fields, not a physical text-line offset. Malformed
application/cycle identifiers cannot manufacture a valid cycle identity.

The shared [JSON intake](hop-historical-outcome-ingestion.md) rejects an entire
invalid inventory. Both formats remain quarantined; source review must resolve
conflicts in a new version while preserving original claims.

## Run (from repository root)

    PYTHONPATH=new-platform/backend python new-platform/backend/scripts/validate_hop_outcomes_csv.py new-platform/backend/data/hop_historical_outcomes_template.csv --as-of 2026-10-25

The empty template is expected to report REVIEW_REQUIRED. A populated file can
report SCHEMA_VALIDATED_REVIEW_REQUIRED, but model_eligible_records=0,
independently_verified=false, probability=null must remain unchanged.

This importer does NOT fetch data, insert into a database, independently review
FDA decision letters, populate probabilities, run scans, or place orders.
Independent document-page attribution, complete approval/nonapproval denominator,
point-in-time trial evidence, and walk-forward validation remain prerequisites.

A publication-selected CRL PDF archive, approved-only product registry, or
provisional PDF page match does NOT establish a complete FDA review-cycle cohort.
