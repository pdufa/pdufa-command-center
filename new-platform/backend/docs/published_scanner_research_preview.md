# Published Pipeline discovery → Phase 3 research (read-only, on demand)

## Purpose

The existing `source_workspace.workspace()` publishes a cached discovery index from
the original scanner sources. It is **not** a declaration that every indexed
trial passes Pipeline's $300m–$10b or Phase 3 restrictions. The new endpoint
**does not modify or rerank this index, its active GEM JR/GEM FS/FA
associations, or WT membership**.

### Endpoint

`POST /api/internal/phase3-research/preview-published-discovery`

Requires existing `x-pdufa-internal-key` authentication. Accepts a bounded
1–200 exact-identity selection:

```json
{
  "exact_keys": ["APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"]
}
```

It selects from the server's published original Pipeline index, joins
**only already-published linked ACTIVE stage memberships** (GEM JR, GEM, WT
if a verified WT stage feed is present), and evaluates via the existing
`evaluate_candidate_batch` and `build_sheet_population_preview` functions.
It returns discovery rows, source warnings, bounded eligibility counts,
and a `PREVIEW_ONLY` sheet projection. Missing exact identities remain
listed under `missingExactKeys` rather than silently being added.

The server's first reviewed public-announcement pair is PEAK (COGT /
NCT05208047). The source catalogue is committed at
`app/phase3_curated_announcements.json`, including source URLs and the
**2026-10-27 manual review date**. The catalogue is not accepted from
HTTP callers; scanner-provided `VERIFIED` flags, apparent Phase 3
stages, registry completion, FDA target dates and market-cap estimates
do **not** promote unreviewed candidates to deep scientific investigation.

This reflects *reviewed issuer disclosure chronology*, **not** FDA
receipt/cycle authentication or independent clinical assessment.

## Fail-closed conditions

- Missing, partial, or stale published source health blocks deep
  research while retaining discovery visibility.
- PDUFA target disagreement with the curated source, NCT mismatch,
  future/unreviewed source dates, and missing source attestations block
  research instead of inventing a verified fact.
- Duplicate exact identity or malformed input fails the request.
- No scheduled scans, new market-cap restrictions, trade decisions,
  persisted scores, database writes, or Google Sheets updates.
- Every currently eligible case starts with zero actual scientific
  evidence assessments; no FDA approval probability or independent
  conclusion is issued.
- The published index can include many trials that do not satisfy
  the Pipeline filters; these are **discovery records**, not members
  certified to meet those restrictions.

## Verification

```sh
pip install -r new-platform/backend/requirements.txt
PYTHONPATH=new-platform/backend pytest -q new-platform/backend/tests/test_phase3_published_discovery_preview.py
```

The on-demand HTTP endpoint becomes live only after reviewed merge,
passed CI, and a separately verified Render deployment.
The endpoint requires the private API key but never echoes it.
Use read-only API documentation for one exact case. No background scan
job is registered here.

### Important remaining engineering work

1. Source-by-source expert adjudication beyond the single PEAK fixture,
   including FDA receipt confirmation and publication chronology.
2. Full 40-question SCIENCE dossier evidence and uncertainty review.
3. Historical FDA cycle adjudication; out-of-time validation for OUTCOME.
4. Production-safe sequential scanner scheduling, checkpoint/retry/audit,
   and explicit authorization for any spreadsheet population.
