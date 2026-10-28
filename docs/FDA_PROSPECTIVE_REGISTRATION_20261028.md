# Prospective ABSTAIN registration manifests — October 28, 2026

This implements a missing engineering primitive for future research evaluation. It is **not a completed prospective validation process**, a calibrated model or a registry of successful predictions. No real trial registration was created in this milestone.

`research.fda_prospective_registration` creates a research-only manifest from exact application/review-cycle identity, indication/program/ticker, target date, evidence cutoff and prespecified action horizon. The event policy selects the first formal FDA action by the horizon; EXTENSION requires a formal target revision. A delay or absence of action is unresolved, not automatic EXTENSION. Registration on the target day or after the horizon is rejected conservatively.

The function hashes actual supplied feature, evidence, protocol and screening-cohort bytes; model bytes are optional for ABSTAIN. When supplied, model version and training cutoff must be linked and training cannot follow the evidence cutoff. Screening inputs freeze included/excluded events and exclusion reasons. Duplicate application/cycle aliases are rejected even when target dates differ. Denominator completeness and program-family disjointness are not independently established by this metadata.

Every record uses the existing PASS/CRL/EXTENSION contract with **ABSTAIN and three null probabilities**. Independent timing, unseen-outcome status, scientific/model validation, validated-accuracy eligibility and trading flags stay false. A future target does not prove no FDA action has already occurred: FDA can act early.

## Use

```sh
python -m research.fda_prospective_registration \
  --spec /path/spec.json \
  --features /path/features.json \
  --evidence /path/evidence.json \
  --protocol /path/protocol.json \
  --cohort /path/screening-cohort.json \
  --output /path/new-registration.json
```

An optional `--model /path/model.bin` requires the matching model version/training metadata. There is no CLI backdating option. The command writes only the explicitly selected manifest and never scans, selects a trial, changes a list or places an order. Keep the input artifacts separately: the manifest records their hashes and sizes; it does not copy or upload those originals.

The specification requires canonical `application_id`, positive integer `review_cycle`, `indication`, canonical `program_family` and `ticker`, `target_date`, aware UTC `evidence_cutoff_at` and `horizon_at`, exact `event_policy`, and `model_version`/`model_training_cutoff_at` (null without model bytes). The module exports the policy/schema constants. The cohort schema freezes a selection rule and members with application, cycle, target, INCLUDED/EXCLUDED disposition and exclusion reason.

Publication uses a complete temporary file, fsync and same-directory atomic link; an existing output or input path cannot be overwritten. This is **per-path write-once storage, not a global append-only registry**. Separate paths are not automatically deduplicated or governed as prediction revisions.

`audit_registration(manifest, artifacts=None)` checks canonical structure, counts and manifest integrity. Supplying retained artifacts additionally checks their bytes against the committed hashes. A matching digest, local clock, Git author/committer date or caller-supplied receipt does not independently authenticate timing, truth or unseen outcomes.

## Before genuine prospective evaluation

Independently anchor the exact manifest bytes to a server-observed timestamp, such as independently fetched GitHub run metadata bound to the trusted repository/workflow/head SHA and retained manifest blob. Independently establish the earliest FDA action/public-disclosure clock and audit source availability, training chronology, cohort selection and program-family independence. Even an authentic timestamp proves byte existence, not scientific correctness.

A later separately governed experimental-model registration can freeze research outputs for untouched future evaluation without advertising them as calibrated or trading-ready. Model validation cannot be required before collecting the first prospective experimental forecast; research registration and validated public predictions are different stages. The current v1 intentionally supports only ABSTAIN because no eligible validated model/trial has been established here. Existing binary backtests remain separate from future three-class scoring until the event/horizon policy and multiclass evaluation are prespecified.

## Verification

**36 registration regressions passed**, covering timestamp boundaries, real-byte commitments, altered artifacts, cohort aliases/counts, unsupported predictions/claims, overwrite protection and the CLI. These use synthetic fixtures and provide no evidence of FDA prediction accuracy. Final combined research and GitHub Actions results are recorded in PR #522.
