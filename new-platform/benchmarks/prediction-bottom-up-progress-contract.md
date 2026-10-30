# Prediction tab — bottom-up progressive population

Status: approved interaction requirement; NOT proof of deployed background research, live updates, or UI.

## Dependency hierarchy
Level 4 (leaf): source retrieval, dated evidence extraction, provenance and verification.
Level 3: individual SCIENCE assessment or subordinate regulatory analysis, calculated only from verified leaves.
Level 2: subordinate group aggregate, calculated only from relevant Level 3 results.
Level 1: top-level TRIAL, SCIENCE, OUTCOME and MAIN sections, calculated from their validated dependencies.

## Per-node states
- PENDING: not started or blocked by prerequisites. No spinner.
- RUNNING: actual in-flight retrieval, verification or calculation. Show animated spinner with accessible label "Researching".
- VERIFIED: finished and evidence-backed. Show checkmark, citation, verification timestamp.
- PARTIAL: some child nodes verified, others pending/running/failed. Show completed/total and partial summary; no fabricated final result.
- UNAVAILABLE: no source or insufficient data; explain why.
- FAILED: operation failed; expose error state and retry; never show spinner indefinitely.
- STALE: verified snapshot exists but freshness threshold exceeded; retain snapshot with timestamp and warning.

## Update semantics
1. Input is exactly one NCT identifier. Changing it increments request generation, cancels/ignores prior generation responses, and clears prior trial's displayed data.
2. Emit state changes as each leaf starts and finishes, then recompute its parent and ancestors incrementally. Never wait for the whole dossier.
3. A spinner appears only for work genuinely underway; no fake progress.
4. Display child completion counts (e.g. SCIENCE 12/40) and source details as soon as verified.
5. Aggregation cannot mark a parent VERIFIED until all mandatory children satisfy acceptance criteria; partial results remain visible.
6. OUTCOME and MAIN may update provisional readiness but must remain ABSTAIN until required evidence and independent regulatory checks are complete.
7. Historical prediction runs enforce predecision cutoff and frozen evidence manifests; no future knowledge in source leaves.
8. Each update carries NCT, generation, node ID, state, timestamp, provenance, and error if applicable.
9. Recover safely after refresh/reconnect using server-persisted job state. Do not imply that work persists until backend workers and state storage are implemented.
10. Do not auto-trade or change existing GEM JR/GEM FS/FA preset associations.

## Acceptance criteria
- Simulated slow source A and fast source B: B appears before A; parent shows PARTIAL until dependencies complete.
- Running leaf shows spinner; pending leaf does not.
- Failed leaf removes spinner and shows failure.
- Changing NCT while old fetch is in flight never leaks old data.
- Completed evidence remains visible while siblings continue.
- Full top-level prediction never appears before required evidence is verified.
