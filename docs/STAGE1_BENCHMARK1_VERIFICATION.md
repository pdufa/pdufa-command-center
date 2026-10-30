# Stage 1 / Benchmark 1 verification

Final completion status: **INCOMPLETE**.

This status remains incomplete until every mandatory requirement has actual
execution evidence, including an authenticated deployed frontend/browser flow.
Successful GitHub, Render or Vercel deployment alone is insufficient.

## Implementation and deployment identifiers

Application commit SHA: pending commit publication.
Render deployment ID and deployed mirror SHA: pending.
Vercel deployment ID and exact main SHA: pending.
Test execution timestamps and CI run URLs: pending.

The application implementation is on main. The existing Render service tracks
new-platform-bootstrap; only corresponding Stage1 files are mirrored there, with
an additive route/lifespan integration into that branch's own main.py. No branch-
wide merge, rollback of existing features, or scoring-rule modification is used.

## Current implementation findings

The pre-existing /api/prediction-events/{nct_id} endpoint is a saved-evidence SSE
replay, not live research. Its existing ABSTAIN/not-assessed behavior is preserved.
Stage1 adds /api/nct-stream/{nct_id}/runs (authenticated POST), run snapshot GET,
and events GET, using the existing internal credential and frontend session auth.
POST also requires the existing same-origin browser boundary. Dossiers must exist,
match the NCT and pass their canonical stored checksum before a run can start.

## Live processing and persistence

New runs retrieve genuine ClinicalTrials.gov APIv2 JSON at the exact NCT URL.
Receipt URLs, HTTP200, source SHA256 and timezone-aware verification timestamps
are retained. The native source is saved separately with its own canonical hash.
Leaves start PENDING, enter LOADING only during real processing, and finish
VERIFIED/FAILED/INSUFFICIENT_EVIDENCE. The smallest leaves commit first; their
evidence-availability parents recalculate only from persisted dependency states.
These are collection/readiness states, not scientific scores or FDA predictions.
MAIN remains ABSTAIN; the scientific scoring and outcome methodology are unchanged.

Each normalized event is committed before SSE delivery. Unique run/request keys,
event keys and strictly increasing event IDs prevent duplicate updates. Last-Event-ID
resumes committed events; heartbeats and bounded connections support reconnection.
Workers use separate connections and database advisory locks, recover interrupted
runs, and retain completed leaves. Original dossiers, archived trials and manifests
are read-only; only new stream metadata is written. Source/events reject updates
or deletes. Failures stop loading indicators and never overwrite original evidence.

The React client displays each received leaf immediately, animates LOADING only,
handles incomplete EOF, retries with the last cursor, and rejects cross-run/NCT
events. Reload stores only a run/NCT pointer and reads all evidence from PostgreSQL.

## Selected real dossier and deployed execution

Selected NCT ID: pending actual deployed selection from existing saved dossiers.
Saved dossier identifier/hash: pending actual deployed retrieval.
Live authoritative retrieval and normalized identity match: pending.
Authentication/authorization rejection and accepted request: pending actual HTTP.
Incremental delivery before completion: pending actual HTTP.
Deliberate disconnect and duplicate-free cursor resume: pending actual HTTP.
Database persistence and identical reload snapshot: pending actual HTTP.
Authenticated frontend population/reload against that same dossier: **unverified**.

No clinical information, tokens, passwords or protected source values are logged.
The backend runtime diagnostic records only the selected NCT/dossier/run IDs,
hashes, counts, timestamps and verification booleans requested for this benchmark.

## Automated tests

Focused backend suite:29 passed locally;1 actual HTTP TestClient case is skipped
locally because the execution environment's AnyIO blocking portal stalls. That
case must execute in CI. Tests include authentication, authorization by saved
dossier, exact source identity/provenance, incremental persistence, event order,
resume, duplicate prevention, interrupted-run recovery, missing evidence,
append-only source/events, unchanged original dossier and source failures.

Focused frontend suite:11 tests passed locally, including real React component
updates/reconnect/reload/cross-NCT cancellation, parser byte splits, auth/origin
rejection, source validation and loading/rendering behavior. Strict focused
TypeScript passed. Full existing backend/frontend regression CI remains pending.
Synthetic fixtures are confined to automated tests; none substitutes for live proof.

## Remaining defects and blockers

- No authenticated browser/application session is currently available. Provider
  protection access does not grant the dashboard's own session. No authentication
  bypass or credential retrieval is used. A legitimate signed-in deployed UI test
  must show the same run/dossier and survive reload before VERIFIED COMPLETE.
- Live backend, persistence, resume, deployment health and runtime-error checks
  must be filled from actual execution after tests pass and deployment completes.
- Clinical significance, effect meaningfulness, FDA pathway, designations,
  submissions and PDUFA evidence are not inferred from a populated field. Missing
  or unadjudicated evidence remains insufficient. This benchmark does not complete
  SCIENCE's40 assessments, OUTCOME or MAIN, and authorizes no trading.

Existing PIPELINE/GEMJR/GEM/WT restrictions, original FS/FA associations, schedules,
scan history, protected data and trading controls are unchanged.
