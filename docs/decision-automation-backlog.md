# DECISION automated development backlog and safety contract

## Current automation

The nightly audit workflow runs DECISION tests and TypeScript checks against the isolated development branch and publishes a GitHub Actions job summary. It does not generate or modify code. Scheduled GitHub Actions only activate when the workflow exists on the repository default branch; workflow_dispatch can be run on an eligible branch.

## Agent integration — NOT CONFIGURED

Autonomous code generation requires a separately installed and authorized coding agent, configured credentials, an execution environment, and repository policies. Do not describe the audit workflow as autonomous development. Do not install an agent or grant repository write permissions without explicit authorization and an implementation review.

## Approved research backlog, in order

1. Integrate FDA source publication chronology into the complete historical decision gate.
2. Add authenticated read-only historical data retrieval and source provenance checks.
3. Build a reviewable application-indication review-cycle ledger with explicit missing-data flags.
4. Bind verified historical comparison status to each trial dashboard panel.
5. Backtest pre-decision predictions with a fixed chronological holdout, calibration, and cohort selection audits.
6. Validate production readiness separately from scientific and predictive readiness.

## Required controls for any future coding agent

- Only isolated feature branches and draft pull requests; never push directly to main.
- No automatic merge, production deployment, trade execution, order routing, or secrets disclosure.
- Require human review for scientific thresholds, approval probabilities, data-source claims, and trading gates.
- Each proposed change must include test evidence, affected files, unresolved issues, and rollback instructions.
- Stop on failing CI or missing source evidence rather than fabricating historical decisions.
- The user may stop or disable automation at any time.
