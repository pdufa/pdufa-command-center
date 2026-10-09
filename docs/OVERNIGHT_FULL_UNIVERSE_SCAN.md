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
2. For EVERY tracked identity (company, ticker, asset, indication, NCT trial, regulatory application and event), scan ALL development phases and transitions: preclinical (when tracked), Early Phase 1, Phase 1, Phase 1/2, Phase 2, Phase 2/3, Phase 3, Phase 4, posted results, NDA/BLA submission, FDA acceptance/review, PDUFA decision and post-decision/commercial follow-up. Check all tracked clinical outcomes, endpoints and p-values; FDA applications/actions/designations; SEC financing/ATM/dilution and closure evidence; issuer announcements and partnerships; cash/runway/debt/revenue/pipeline; market cap, prices, volume, short interest, ownership and trading metrics when available. Do not limit checks to recently updated trials or Phase 2/3 records. Log explicit per-source coverage, unavailable data and evidence timestamps. Record unavailable sources explicitly.
3. Use incremental source queries and fingerprints to detect changes since the last verified snapshot. Deep-review only new, changed, conflicting, or time-sensitive evidence.
4. Checkpoint after each bounded batch, pace rate-limited sources, retry transient failures, and resume unprocessed identities without deleting prior verified evidence.
5. Write an auditable per-source, per-identity ledger with attempted/completed/warning/failed/skipped, checked_at, evidence URL, change hash, error and retry count.
6. Aggregate the four statuses **only after** checking the entire due-universe ledger. Show due, checked, clean, warnings, unfinished, failed, retries and last successful timestamp.
7. Publish a Pacific-time morning change report with source links, old/new values and NO NEW FINDINGS if appropriate. Separate batch completion from full-universe completion.
8. Keep PDUFA/FDA decision probability separate from trading opportunity scores. Never infer Phase 3 success from results posted or financing close from an expected closing date.

## Implementation state
The GitHub Phase 2/3 and Phase 3-results collectors use the four status labels. **They are not a full-universe overnight orchestrator.** A separate workflow, persistent audit ledger and per-source connectors are still required to implement the complete nightly scope above. The Streamlit page must not label the entire overnight scan COMPLETE from these two collectors alone.

## Mandatory full-tracked-universe scope
The complete inventory is the authority for what must be checked. Every active tracked row is due nightly, regardless of phase, age, PDUFA proximity, previous results or whether it changed. Change detection can be incremental, but a query for only recently updated Phase 2/3 studies is **not** a complete inventory check. Include Phase 1, Phase 1/2, Phase 2, Phase 2/3, Phase 3, Phase 4, NDA/BLA, FDA review, PDUFA, and post-decision records plus all other tracked record types. Count checked identities separately from checked sources and explicitly report omissions. Do not mark the full overnight run COMPLETE while a required phase or source family is unsupported.
