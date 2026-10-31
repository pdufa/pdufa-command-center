# Read-only Neon PostgreSQL acceptance inventory — 2026-10-31 UTC

**Scope:** Existing Neon project `pdufa-new-persistent-db` (main branch), database `pdufa_new`, PostgreSQL 16. All observations below were obtained with `SELECT`-only SQL through the connected Neon data access. **No migration, deployment, schema mutation, scan dispatch, credential read, trial rating, or trade occurred.** Do not treat a count as proof of content parity or restore success.

## Current database observations

- Database main branch: ready. **36** application-visible tables in `public` (information_schema list).
- `program_identity`: **11,820** persistent identity mappings.
- `candidate_assessment_history`: **244,557** rows, **11,820** distinct exact IDs.
- `full_trial_records`: **11,623** rows (each distinct NCT).
- `phase3_trials`: **14,847** rows.
- `scientific_candidate_dossiers`: **228** rows, **228** distinct NCTs.
- `scientific_review_runs`: **1** run.
- `phase3_predictions`: **0** rows.
- `phase3_fda_decisions`: **0** rows.
- `phase3_fda_applications`: **0** rows.
- `phase3_evidence`: **14,847** rows (not equivalent to independently reconciled FDA decisions).
- `checklists`: **0** rows; `program_checklists`: **0** rows. Do not assume zero means migration complete or that stage restrictions/FS-FA presets are stored in these tables.
- `full_trial_download`: one row in COMPLETE state. `nct_stream_runs`: **55** COMPLETE rows; this is execution state, not proof of all-source coverage.
- `archive_verification_runs`: **2** rows. Their existence is not proof of a PostgreSQL dump and isolated restore.

### Identity and row-reference sanity

- Assessment rows whose exact ID has **no** `program_identity.source_key`: **0**.
- Assessment rows whose saved program ID **differs** from `PDUFA-` plus the canonical padded `program_identity.id`: **0**.
- Scientific dossiers missing a corresponding `phase3_trials.nct_id`: **0**.
- Database constraints observed: `program_identity.source_key` UNIQUE, registry primary key, assessment history primary key, scientific dossier composite primary key, scientific dossier FK to scientific review run and SHA-256 length check.
- Only **2,619** NCTs are in **both** `full_trial_records` and `phase3_trials`. There are **9,004** full trial records not present in the separate Phase 3 catalog and **12,228** catalog trials without a full-record row. These may be separate collection populations: **do not call this a migration defect or use either count as total global PDUFA candidate coverage** without establishing table purpose, scope and source snapshots.

### Timing and regulatory-source incident

- Latest `full_trial_records.fetched_at`: 2026-10-31 03:47:29.792 UTC.
- Latest `candidate_assessment_history.assessed_at`: 2026-10-31 04:45:10.320 UTC.
- Latest `program_identity.created_at`: 2026-10-31 03:33:48.702 UTC.
- One `phase3_regulatory_sources` entry: `INDEX`, state **RETRY**, error **HTTP_404**, attempts **15**, last checked 2026-10-31 12:54:53.655 UTC.
- The persisted URL is FDA's official oncology/hematology approval-notification index. Read-only web verification on the same date **successfully retrieved** that exact official FDA URL, which means the URL is valid through that retrieval path; the backend-specific HTTP 404 root cause is **not yet established**.
- The Render staging log at 12:54:53 UTC records the same FDA index HTTP_404 time. This is **strong circumstantial evidence** that the staging service and this Neon database are related, **not** direct proof of the configured `DATABASE_URL` value or of source/target parity.
- FDA official index coverage is incomplete; **zero** independently persisted decision rows exist here. A published FDA clinical result is not a verified NDA/BLA decision. Missing historical labeling cannot be filled by inference.

## Open cutover gates

| Gate | Status | Evidence needed |
| --- | --- | --- |
| Neon table existence and selected aggregate counts | **Observed** | Above read-only SQL |
| Neon identity/history mapping consistency | **Passed on observed checks** | 0 missing/mismatched mappings |
| Render source vs Neon target row- and content-level parity | **Not verified** | Authenticated read-only source inventory, source/target row digests within one consistent snapshot |
| Private Render PostgreSQL access | **Blocked externally** | Use in-network authorized execution, not an opened public allowlist |
| Full private backup and isolated **restore** | **Not verified** | Restore logs, schema/constraint checks, row/content digest compare |
| SCIENCE → OUTCOME → MAIN → RESULTS for same saved trial | **Not verified end-to-end live** | Authorized authenticated replay and dashboard read with identity, cutoff, provenance and abstention checks |
| Saved FDA PASS/CRL/EXTENSION prediction calibration | **Not available** | 0 saved `phase3_predictions` rows; no validated classifier or outcome accuracy |
| Clinical/regulatory source completeness | **Partial** | October 30 overnight source audit: 24 required findings unresolved, 2 conflicts; FDA/SEC/FINANCIAL still partial |
| Production cutover | **Hold** | All preceding acceptance gates complete and operator-approved |

**Safety:** Leave Streamlit, all production scripts/scanners, FS/FA associations, stage restriction settings, source facts and production deployment intact. The branch contains only safe review/test material. This is not permission to migrate or trade.
