# FDA historical candidate audit integration contract (research-only)

## Purpose
Connect the FY2024–2025 FDA candidate-source union to a conservative
action-level review queue. The 412 source candidates reported in the
historical research packet are **not** a representative denominator, verified
review cycles, or 412 model-training examples.

## Required source-to-review mapping
For each independently verified review cycle, map:
- `application_id`: verified NDA/BLA identifier, not a ticker.
- `review_cycle_id`: source-backed action cycle, not inferred from a filing.
- `action_type`: exactly `approval` or `complete_response_letter`; all other
  actions abstain.
- `action_date`: verified FDA action date (YYYY-MM-DD).
- `official_fda_action_source`: exact official HTTPS FDA document URL.
- `evidence_cutoff_date`: last date for evidence allowed in a historical
  prediction; must be strictly before the action.
- `source_cohort`: cohort provenance, retaining `candidate_union` for the
  selected-source union.
- `original_filing_denominator_verified`: true **only** with an independently
  audited complete action population for the declared sampling frame.
- `program_family_disjoint_verified`: true **only** after related-program
  holdout checks.

Do not populate missing fields with invented values or mark cohort/holdout
flags true merely to make a record pass. Verify PDF bytes, action identity,
duplicate cycles, negative decisions, and chronology upstream. The current
host allowlist is only a URL-format check, not proof that an FDA document
exists or supports the claimed action.

## Output and safety
Run `audit_candidates(records)` on normalized, independently inspected
records. Report total candidates, abstentions, reason counts and records
eligible for **further review**. Never compute an approval rate, performance
metric, or forecast from the selected-source candidate union. Do not feed
this audit directly into SCIENCE, OUTCOME, MAIN, or trading.

## Integration acceptance criteria
1. Regression tests and existing historical safety CI pass.
2. The 412-source candidate cohort remains abstained without verified
   representative denominator and individual action-cycle evidence.
3. A separate complete cohort includes verified approvals **and** CRLs.
4. No post-action evidence enters any historical prediction feature.
5. Related programs remain separated across training and test periods.
6. Review-cycle labels are audited before any research model training.
7. Deployment and trading authorization remain independent approvals.
