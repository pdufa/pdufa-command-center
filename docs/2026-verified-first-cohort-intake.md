# Verified-first cohort intake — 2026 FDA decisions

This is a **source intake checklist**, not a completed dataset or a list of
predictions.

## Research priority
The pdufa.bio FDA decision timing study (updated 2026-11-17) states that
38 decisions have both a sourced FDA action date and sourced PDUFA goal date,
and another 19 have sourced outcomes but no usable exact goal date.
Source: https://www.pdufa.bio/research/fda-decision-timing

**Do not assume these 57 are all distinct eligible FDA application events**
until their identifiers and sponsor/partner relationships are reconciled.
Do not infer the remainder of the site's 183 from subtraction: page counts
can have different definitions and update times.

## Source intake fields (separate files)
1. `source_events.csv`: source, source_record_id, ticker, drug, indication,
   decision_date, application_id, source_url, source_status,
   source_retrieved_at. No outcome-bearing columns.
2. `outcomes.csv` (restricted): event_id, actual_outcome, outcome_source_url,
   outcome_source_date, verified_by.
3. `predecision_evidence.csv`: event_id, evidence_url, publication_date,
   evidence_type, extracted_claim, extraction_checked_by.
4. `blind_events.csv`: event_id and the four Level-1 gates, generated from
   validated pre-cutoff evidence only.

## Safeguards
- Verify that the goal date is a true PDUFA goal, not an announcement date.
- Maintain both FDA action date and goal date where available.
- Reconcile sponsor/partner duplicate tickers to one application event.
- Maintain a dated inclusion/exclusion ledger and frozen denominator.
- Use only pre-cutoff evidence when assigning the four Level-1 gates.
- Store outcome files in a separate location inaccessible to the blind runner.
- Run tests before claiming predictions are locked or accuracy is measured.
- Market-cap restriction is a separate cohort filter; define as-of date.

## Delivery milestones
A. Import 57 sourced outcome candidates and reconcile event identities.
B. Collect historical pre-cutoff evidence for each candidate.
C. Produce locked L1 predictions, including ABSTAIN when evidence is missing.
D. Unblind and report accuracy plus coverage for this cohort.
E. Expand to remaining archive records only after verifying outcomes.

No milestone is marked complete merely by adding this checklist.
