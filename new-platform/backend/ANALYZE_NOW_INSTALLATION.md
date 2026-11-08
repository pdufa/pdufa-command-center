# MAIN PDUFA — Analyze Now installation and pilot acceptance

**Priority:** Complete and verify Analyze Now before further advanced medical installations.
**Deployment:** Existing isolated MAIN preview branch and backend only, unmerged.
**Active architecture:** POOL → FOCUS → 12-stage independent source worker → evidence-gated FDA outcomes → independent certainty reliability.

## One independent worker and exact-NCT history

1. `medical_continuous.py` is the only research worker. Analyze Now starts it for one eligible exact NCT, records each of the 12 source stages and supports restart, stop and resume.
2. `medical_on_demand.py` records the initial dated, source-only report on request. A completed run writes its result to the existing append-only `medical_prediction_revisions` table, preserving the full NCT history across spreadsheet movements. Failed and pending initial reports are retained.
3. The active report uses **only collected trial identity, clinical, scientific, regulatory and CMC evidence**. It contains stage dispositions, source URL pointers, missing original documents and independently assessed review readiness. It never imports historical scoring archives or computes a numeric medical grade from them.
4. FDA approval, Complete Response Letter, and review-delay outcomes remain separate **ABSTAIN** decisions with `probability=null` unless independently validated historical calibration and complete current-cycle adjudication are proven. Certainty is separately `NOT_VALIDATED` with `rating=null`.
5. The source-change watcher checks exact ClinicalTrials.gov NCT evidence. Operational-component changes use a versioned fingerprint. Both are opt-in, database-dependent and canary-gated; FDA/SEC/publication change coverage is not yet comprehensive.
6. `/api/analyze-now` requires user session, exact NCT and a same-origin UUID request. Historical GET accepts an exact NCT even after a trial exits FOCUS, but no further work can start for an ineligible trial.
7. Retired historical scoring and archived trial observations are retained as **read-only evidence records**, never loaded in the active Analyze Now worker. See repository `AGENTS.md` and the permanent retired-architecture audit.

## Canary acceptance sequence

**Canary:** `NCT06081894`; FOCUS candidate listed in the dated 2026-11-07 snapshot.

- [x] One-click control is present on each of the 29 FOCUS rows.
- [x] Only the canary button is enabled before real validation; the same restriction applies to registry and component-change reruns.
- [x] Backend and frontend code use the original worker and immutable revision tables rather than duplicating source jobs.
- [x] Separate approval, CRL, review-delay abstentions; independent null certainty; original source pointers and missing evidence.
- [x] Retired scoring input dependency removed from the active source report, component signature and UI.
- [x] Dedicated regression tests defined for canary, failed-run retention, source changes, NCT moves, idempotency and all-29 rollout simulation.
- [ ] Green QA on the exact latest commit, including permanent retirement guard.
- [ ] Preview Postgres configured and `/health` returns `storage_ready=true`.
- [ ] Real canary POST and all 12 saved stage documents verified in persistent PostgreSQL.
- [ ] Source links, missing information, three abstaining outcome fields and null certainty confirmed by reading the live saved report and immutable history.
- [ ] Stop/resume and restart recovery confirmed against the same persistent database.
- [ ] Only then enable the other 28 eligible trials by setting `PDUFA_ANALYZE_NOW_ALL_ENABLED=true` on both Render and preview-branch Vercel.
- [ ] Validate automated reanalysis after actual new evidence or newly operational components; no fabricated rerun claims.

## Credentials and deployment boundaries

Preview service: https://dashboard.render.com/web/srv-dbntrkpsrm7s73aec3lg

Preview database: https://dashboard.render.com/d/dpg-dbnts20u01pc73do32qg-a

The internal `DATABASE_URL` must be copied in Render's own dashboard into its isolated service environment. **Do not paste credentials into chat, logs, documentation or commits.** The free preview database expires December 8, 2026.

No production merge, no POOL/FOCUS Google Sheet mutation, no unvalidated numerical prediction and no claim that a source check equals a completed multidisciplinary medical assessment.
