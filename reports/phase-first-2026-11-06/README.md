# Phase-first company research — 6 November 2026

Axsome (AXSM) is the next most prevalent company in the existing census: 28 records, after Alkermes (34 census records). This batch reviews those exact 28 NCTs, not every historical or acquired Axsome trial. The preserved Alkermes discovery set contains 128 records (125 NCTs and three ISRCTNs), broader than its 34 census records.

## Axsome results

| Measurement | Verified result |
|---|---:|
| Company reviewed | 1 — Axsome Therapeutics |
| Exact registry documents reviewed | 28 |
| Other source documents/excerpts reviewed | 13 |
| Documentary facts linked | 38 (includes previously known supporting facts) |
| Verified Phase 3 trials | 27 |
| Verified Phase 2/3 trials | 1 |
| Checklist requirements per trial | 36 |
| Available evidence items | 319 |
| Missing expected evidence items | 369 |
| Pending items | 196 |
| Not yet expected items | 80 |
| Not applicable items | 42 |
| Conflicting items | 2 |
| New numerical clinical grades | 0 |
| New calibrated RAAS/FDA predictions | 0 |

These classifications sum to 1,008 items. Missing plus conflicting items total 371 unresolved research items. Pending results and later-stage requirements are excluded from the completeness denominator and are never scored zero. The 36-item phase-first checklist is a new research view; it must not be confused with the existing 30-question, 190-column export or its missing-cell count.

All 28 Axsome trials show N/A for five-metric grades because the existing accepted benchmark-review feed contains no AXSM grades. Public results are available for several studies; documentation alone is not a benchmark-reviewed scientific grade. FDA predictions abstain, preserving existing calibration gates. The source ledger documents AXS-12 NDA acceptance and the future May 1, 2027 application target for the exact SYMPHONY/ENCORE program crosswalk. These facts do not create a forecast or modify the existing regulatory-link census.

## Specific issues

- **CREATE-1, NCT02504008:** issuer/SEC disclosure says the IDMC recommended stopping for futility; the stale registry says UNKNOWN. Both are displayed; no active recruitment is inferred.
- **COAST-1, NCT02746068:** historical interim continuation is documented, but a final efficacy readout and resolved current status remain unverified.
- **EMERGE, NCT05550207:** issuer calls mTOQ-4 the primary endpoint; the current registry lists different primary measures. The discrepancy is flagged, and the open-label comparison is not described as randomized superiority.
- **STRIDE-1, NCT02741791, and PARADIGM, NCT06360419:** failed primary endpoints remain visible, independently of later approvals or subgroup signals.
- Direct manufacturer fetches returned HTTP403. Indexed manufacturer text, original issuer releases and SEC originals provided alternatives. Source-level limitations remain in the evidence ledger; controls were not bypassed.
- Expected evidence marked missing was not found in the reviewed source set. This is not a claim that exhaustive publication research has proven nonavailability.
- Earlier Alkermes issue remains: the current valiloxybate healthy-volunteer Phase 1 study lacks a verified exact-registry match; its historical withdrawn Phase 2 record is not substituted.

## Implementation and preservation

The reusable engine verifies the individual phase before assessing applicability, keeps mixed phases, distinguishes pending outcomes from missing evidence, normalizes only over eligible scored factors, and refuses undated, unbenchmarked, future-dated or wrong-phase grades. The research API supports `scope=axsome`, `scope=alkermes` and `scope=census`; exact-trial details load on expansion to stay within response limits. The UI defaults to Axsome, separates missing/pending/premature requirements, shows source confidence separately from FDA confidence, and provides bordered horizontal expansion and phone scrolling.

New Git-persisted append-only history uses the trial identifier as the continuity key. An initial 918 scope-specific snapshots cover 856 distinct identifiers; running the snapshot script again adds zero duplicate events. No database schema or live database records are changed. Existing clinical grades, survey responses, RAAS ledgers, calibration, trial membership and restricted Pipeline filters are unchanged. GEM/GEM JR and Streamlit are not enabled.

The existing production audit before release reported 762 trials, 190 export columns, 13,053 unscored question slots, four trials with numerical predictions and 100 endpoint-adjudicated trials (72 met, 17 not met, 11 nonbinary). Those are the separate legacy audit, not phase-first counts. This batch does not rewrite that audit's source models or historical endpoint adjudications.

## Validation

- 12 focused phase-first checks passed, including all census identities, mixed/early phases, partial normalization, null handling, chronology, source conflicts, summary response budgets and history continuity.
- Three Python collector checks passed: exact identity, future-source rejection and unknown-company rejection.
- Frontend suite: 213 of 216 files passed in the initial restricted execution; the three subprocess-dependent suites passed on rerun in the configured environment (19 checks). Required remote CI is the final release gate.
- TypeScript passed. Production build passed; the initial restricted subprocess configuration failed while reading TypeScript config, then the configured retry succeeded.
- Production-build browser check passed at desktop and 393px mobile: all three API scopes, detail expansion, source conflicts, history rendering and no browser errors.
- Existing CSV checked end to end: 762 data rows, 762 unique NCTs, exactly 190 fields in every row.

Deployment and PR status must be verified separately; these local checks do not claim a production release.

## Reproduce

Run from the repository root:

```sh
python scripts/collect_company_phase_first.py --ticker AXSM --cache /tmp/axsm-registry-cache --output /tmp/axsm-registry.json
node scripts/export_phase_first_reports.cjs axsome
node scripts/snapshot_phase_first.cjs
node new-platform/frontend/tests/phase-first-clinical.test.cjs
python -m unittest discover -s tests -p test_phase_first_registry.py
```

The CSVs provide trial-level five-metric coverage, requirement-level missingness and exact-trial evidence provenance. The larger census evidence-register CSV can be regenerated with `node scripts/export_phase_first_reports.cjs census`; it is not duplicated in Git.
