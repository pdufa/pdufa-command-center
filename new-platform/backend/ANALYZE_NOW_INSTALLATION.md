# MAIN PDUFA — Analyze Now installation and pilot acceptance

**Priority:** Complete/verify Analyze Now before further advanced-analysis work.
**Location:** existing FOCUS trial rows (`/focus`), read-only cross-stage lookup (`/analyze-now?nct=NCT...`), authenticated `/api/analyze-now` proxy, isolated Render medical backend.
**Production status:** Draft preview only. No RAAS/survey dependencies restored, no POOL/FOCUS sheet writes, no production merge, no generated FDA probabilities.

## Architecture — one worker, one history

1. `medical_continuous.py` provides the existing durable 12-source-stage worker, restart and stop/resume behavior. Analyze Now calls it with an exact NCT rather than duplicating a pipeline.
2. `medical_on_demand.py` records request provenance by `run_id`, but all completed research goes into the **existing** append-only `medical_prediction_revisions` table as `analyzeNow`. This is the same trial keyed history across spreadsheet moves.
3. The initial analysis (with archive score, three abstaining outcomes, reliability status and date) is stored **when the request is made** in `medical_analyze_requests.initial_report`. Failed and interrupted runs remain in NCT history instead of disappearing.
4. `focus_legacy_score_snapshot.json` is an optional, read-only backend mirror from existing historical RAAS and clinical-five research. The medical source worker does not require RAAS or surveys. The snapshot is **dated 2026-11-07**, not a live recalculation or newly issued RAAS score.
5. ClinicalTrials.gov exact-NCT change monitoring can request a new source-run revision; newly operational components are fingerprinted by the same existing source watcher. Both are opt-in, PostgreSQL-dependent and canary-gated until rollout.
6. `/api/analyze-now` is signed-in, same-origin, exact-NCT-only for POST with UUID idempotency, no-store for GET; GET history remains accessible by NCT even after the trial exits FOCUS.
7. MAIN installation monitor reports live canary saved status and activation flags from database records, not page presence.

## Pilot and score provenance

**Canary:** `NCT06081894`, a current FOCUS NCT.

| Field | Dated archive status |
| --- | --- |
| Full 30-metric RAAS overall score | Not available (null); no validated score is calculated |
| Five-factor clinical research grade | **45/100**, with 5 graded factors, archived 2026-11-07 |
| Historical source pointers | Published trial research and issuer releases from the historical archive; not independent regulatory adjudication |
| Scientific source stage analysis | Available only after a real 12-stage worker run |
| Approval, CRL and review-delay probabilities | Separate **ABSTAIN**, null |
| Independent certainty | **NOT_VALIDATED**, null |
| Missing data | Individual source gaps, full multidisciplinary statistical/CMC review, complete RAAS and independent calibration |

This archived clinical **45/100 is not RAAS 30-metric, an FDA forecast, or a reliability percentage**.

## Acceptance gates — one real canary before 29-trial activation

- [x] Source-code integration of per-row Analyze Now UI, authenticated proxy and one underlying worker.
- [x] Read-only historical clinical-five / RAAS mirror, dated source evidence and abstention safeguards.
- [x] Store initial request report and immutable completed research revision by exact NCT, with failed-run history.
- [x] Fail-closed, pilot-only UI and backend gates; all 29 FOCUS rows display the control but 28 remain disabled.
- [x] Dedicated regression test suite defined for pilot, score provenance, two revisions, moves, duplicate requests, failure retention and simulation of all 29 after gate.
- [ ] **Dedicated regression suite green on current exact SHA**; inspect GitHub Actions results before calling tests passed.
- [ ] **Preview PostgreSQL connected and `/health` reporting `storage_ready: true`.** Backend is live but currently reports `postgres_required: true` and `persistent database ready: false`.
- [ ] **Real operator POST** for `NCT06081894` returns a persisted exact-NCT run in the backend; verify full original source fetch and all 12 stage dispositions.
- [ ] **Read GET and history** to verify 45/100 research score where archived, null full RAAS score, three abstaining FDA outcomes, null certainty, dated original-source links, source gaps, and the same run after reload.
- [ ] **Restart/stop/resume and source update** produce immutable source revisions without overwriting the old record.
- [ ] **Enable all 29** only after the pilot above is evidenced; configure `PDUFA_ANALYZE_NOW_ALL_ENABLED=true` on both backend Render and branch-scoped preview Vercel, redeploy and verify 29 actual enabled buttons and exact-NCT authorizations. Do not enable this flag as a workaround for missing PostgreSQL.
- [ ] After confirmed live pilot, consider enabling `PDUFA_MEDICAL_AUTO_WATCH=true` for six-hour source and component monitoring; this covers ClinicalTrials.gov and explicitly enabled components, **not** comprehensive FDA, SEC, sponsor or PubMed changes.

## Commands and sources

- Frontend: `npm run typecheck`; `node --test tests/medical-analyze-now.test.cjs`.
- Backend: `PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests/test_medical_on_demand.py`.
- CI workflow: `Deep Medical Intelligence Preview QA` includes these checks.
- Project: `pdufa/pdufa-command-center`; draft PR #928; feature branch `feature/deep-medical-intelligence-preview-20261107`.
- Separate preview Render backend: `https://dashboard.render.com/web/srv-dbntrkpsrm7s73aec3lg`.
- Separate preview Render Postgres: `https://dashboard.render.com/d/dpg-dbnts20u01pc73do32qg-a`. Free trial expiration 2026-12-08.

**Secure connection step:** In Render database → Connect → copy *Internal Database URL*, then service → Environment → set `DATABASE_URL`, save/deploy. Never paste credentials into chat or commit them. This connector currently cannot retrieve the internal URL; do not fabricate a connection.

**No claimed operational readiness until real saved pilot and external evidence checks pass.**
