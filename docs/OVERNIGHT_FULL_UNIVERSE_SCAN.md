# Overnight PDUFA full-universe scan contract

The scheduled ChatGPT task and GitHub collectors must not conflate *one source complete* with *full-universe complete*.

## Four statuses
- **COMPLETE**: every due company/event had all required checks successfully completed.
- **COMPLETE WITH WARNINGS**: every due company/event was attempted, but some sources/evidence remain unavailable, stale or require review.
- **PARTIAL**: at least one due company/event or required check was not attempted or did not finish; preserve checkpoints and retry.
- **FAILED**: no reliable run was possible, or an unrecoverable setup/data error prevented meaningful checks.

A source-specific scanner may report COMPLETE while the *overall* scan is PARTIAL. Never infer overall status from a single source's `complete` flag.

## Nightly workflow requirements
1. Snapshot the complete tracked company + ticker + drug + indication + trial + PDUFA event universe at the start; record the source and snapshot timestamp.
2. For each due identity, run ClinicalTrials.gov Phase 1/2/3 and posted-results checks; FDA application/action-date/outcome/designation checks; SEC financing/ATM/dilution checks; issuer investor-relations news checks; cash/runway checks; and obtainable market/ownership checks. Record unavailable sources explicitly.
3. Use incremental source queries and fingerprints to detect changes since the last verified snapshot. Deep-review only new, changed, conflicting, or time-sensitive evidence.
4. Checkpoint after each bounded batch, pace rate-limited sources, retry transient failures, and resume unprocessed identities without deleting prior verified evidence.
5. Write an auditable per-source, per-identity ledger with attempted/completed/warning/failed/skipped, checked_at, evidence URL, change hash, error and retry count.
6. Aggregate the four statuses **only after** checking the entire due-universe ledger. Show due, checked, clean, warnings, unfinished, failed, retries and last successful timestamp.
7. Publish a Pacific-time morning change report with source links, old/new values and NO NEW FINDINGS if appropriate. Separate batch completion from full-universe completion.
8. Keep PDUFA/FDA decision probability separate from trading opportunity scores. Never infer Phase 3 success from results posted or financing close from an expected closing date.

## Implementation state
The GitHub Phase 2/3 and Phase 3-results collectors use the four status labels. **They are not a full-universe overnight orchestrator.** A separate workflow, persistent audit ledger and per-source connectors are still required to implement the complete nightly scope above. The Streamlit page must not label the entire overnight scan COMPLETE from these two collectors alone.
