# Reproducible historical evaluation preparation

Status: **NOT READY / ABSTAIN**. No FDA forecasts are evaluated by this module.

`research.official_evaluation_manifest` extends existing chronological readiness
triage with explicit TRAIN, CALIBRATION and EVALUATION partitions. It reuses the
existing outcome, publication, feature-cutoff, duplicate-cycle and missing-data
gates. It never fits a model, imputes a value, accepts client verification flags
or reports operational metrics.

The operator proposes aware calibration and final-evaluation boundaries and
unique required fields. TRAIN evidence cutoffs and labels must precede the
calibration boundary. CALIBRATION cutoffs occupy the half-open interval from
calibration start to final evaluation; calibration outcomes must already be
public strictly before final evaluation. EVALUATION cutoffs cannot precede the
final boundary. Every pair of partitions is isolated by exact application and
case-insensitive program family. Mapping proposals do not independently establish
biological program relationships.

Every row remains in the manifest, including malformed rows, missing fields,
unassigned partitions, duplicate cycles and conflicting labels. Per-partition
and therapeutic-area counts retain those denominators. Missing area is UNKNOWN,
not an inferred disease class. Preparation abstention counts describe blocked
inputs, never an observed forecasting coverage or abstention rate.

## Event target binding

Each record can supply an `event_target` with exactly `events`,
`original_target_date`, `horizon_at` and `evaluation_as_of`. The record's own
application/cycle/program and evidence cutoff bind that proposal to
`official_event_protocol.prepare_event_target`. Missing target/horizon proposals
block preparation. Malformed target proposals remain visible blockers.

The manifest includes the frozen event-protocol SHA, event preparation report,
first-formal-event target candidate and preserved chronology. A structurally
usable candidate must agree with the record's separate `outcome_label`; its
publication must also precede the next partition's boundary. This prevents an
early legacy label from hiding a later-published event label. Imported original
target dates remain unverified operator claims.

The first-formal-event protocol preserves multiple events; it does not make
extension, later CRL and eventual approval mutually exclusive across a history.
Its window target is one explicitly defined event question. No event is inferred
from elapsed time, and no later action replaces an inadequately sourced first
event. Independent source/scientific review remains required for every candidate.

## Replay

```sh
python -m research.official_evaluation_manifest \
  --records /authorized/proposed-records.json \
  --proposal /authorized/proposed-parameters.json \
  --output /authorized/evaluation-preparation.json
```

The proposal supplies `calibration_starts_at`, `evaluation_starts_at` and
`required_fields`. No actual cohort boundary, prediction horizon, field selection
or trained model has been scientifically prespecified here. Record envelopes use
the existing `official_history_readiness` contract, with optional therapeutic
area and event-target metadata described above. Repeated JSON keys are rejected.
Outputs never overwrite an existing report.

Input snapshot, proposed parameters, engineering protocol and final manifest
digests support exact replay. They are local integrity identifiers, not proof of
an untouched final holdout, an externally timestamped forecast or independent
adjudication. The output omits scientific input values; event provenance remains
available for review and must not be supplied to a prediction model.

## Metrics and separate readiness

The existing `official_validation.synthetic_fixture_diagnostics` remains the
only metric entry point: named synthetic fixtures exercise precision/recall,
three-class confusion, Brier, log loss, calibration bins, abstention and area/year
strata. Existing Wilson intervals are descriptive binomial arithmetic. They are
not valid empirical FDA uncertainty estimates without a justified independent
sampling design; score intervals still require a prespecified family-cluster
protocol and sufficient clusters. No new real-case accuracy is reported.

The existing authorized prediction projection now exposes four separate grades:
evidence availability, independent scientific assessment, historical validation
and prediction confidence. Timely source observations cannot upgrade the latter
three. All numerical predictions and trading recommendations remain unavailable.
