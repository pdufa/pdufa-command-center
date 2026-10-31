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


## Follow-up: cryptographic document and SCIENCE readiness verification (October 31, 2026)

The following additional checks used **read-only SELECT** on the existing Neon main branch `pdufa_new`; no evidence or job state was changed.

| Evidence | Observed rows | SHA-256 mismatches | Interpretation |
| --- | ---: | ---: | --- |
| `scientific_candidate_dossiers` | 228 | **0** | Every stored canonical UTF-8 dossier document matched its recorded SHA-256 |
| `phase3_dossier_versions` | 14,847 | **0** | All stored catalog dossier documents matched their saved SHA-256 |
| `archive_manifests` | 1 | **0** | Manifest text hash is internally consistent; **not a PostgreSQL backup/restore test** |

Example strict expression: `COUNT(*) FILTER (WHERE sha256 <> encode(sha256(convert_to(document,'UTF8')),'hex'))`. Document-content integrity alone does not certify upstream scientific sources, historical FDA outcomes, evidence completeness or source-to-destination database parity.

The `scientific_review_runs` record is explicit: **228 candidates independently checked, 228 source-linked scientific dossiers, 226 RELUCTANT, 2 NOT READY, 0 READY, 0 full scientific investigations completed, and 228 requiring additional external evidence**. It reports 122 openFDA product-candidate matches, 99 no matches, 7 unavailable, **0 verified regulatory identifiers**. None is a validated FDA PASS/CRL/EXTENSION result.

All `phase3_trials.scientific_readiness` values are `NOT READY` (**14,847** rows). The `phase3_predictions` table has **0** rows. The trial stream contains **55 COMPLETE** runs and **3,850** events with **0 orphan event rows**. All 228 independently reviewed scientific dossier NCTs are present in both the Phase 3 catalog and full-trial archive. Stream-run `dossier_id` references are not the same namespace as `phase3_dossier_versions.dossier_id` and were **not** interpreted as broken foreign-key references without a documented key relationship.

Two `archive_verification_runs` entries include `archive_integrity=PASS` for the saved ClinicalTrials.gov archive (one dated October 30 Pacific). These are **source-archive integrity checks**, not `pg_dump` and isolated PostgreSQL restore proof.

### Diagnosed FDA source error and draft mitigation

Neon `phase3_regulatory_sources` identifies the **INDEX** (not an openFDA search) as `RETRY:HTTP_404` at 2026-10-31 12:54:53 UTC. Its valid FDA URL was fetched successfully through independent web access, not the Render worker. Draft PR #530 now has a *bounded one-time index-only retry with alternate browser-compatible request headers*, verifies the official HTML title, and retains failure when retry is unsuccessful; five new 404/redirect/body spoofing regressions passed staging CI. **This fix has not been deployed to Render**, so the live outage is not claimed resolved. An empty openFDA application lookup remains unverified and cannot generate a decision.

Do not promote the draft branches or migrate live data based on these findings. Source/target fingerprints, restore and authenticated live scientific pipeline acceptance remain outstanding.
