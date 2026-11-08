# MAIN — Revision 13: durable 800-position source-audit job wired to live monitor

**Exact pilot:** ACACIA-HCM / NCT06081894 / CY 6033.  
**Research and implementation date:** 2026-11-08.  
**Environment:** Vercel draft preview plus isolated Render medical canary `pdufa-medical-intelligence-preview`; **not** production.

## What exists and what is genuinely processed

The existing `medical_scientific_triage.analyze` already generated a reproducible **source-only classification** for each of the 40 × 20 scientific-method slots. Revision 13 adds `medical_method_audit_worker.py`: an independent, additive execution ledger that verifies **each persisted triage position**, its catalog order, source class and source-lead count and writes one actual immutable receipt per position.

- Creates **exactly 800 possible position receipts**, grouped into 40 transactional batches of 20. Completion is calculated from persisted receipt counts, never from animation, timers, request count or a static percentage.
- Restricts scope to **NCT06081894** and the original saved triage snapshot identified by snapshot UUID plus source/catalog SHA-256. Initial preflight checks all 800 positions before the first insert.
- **Idempotent by NCT and source snapshot:** a rerun of the same saved source packet does not manufacture extra work or a new revision. Interrupted batches can resume from the last transactionally committed group of 20.
- In separate tables `medical_pilot_method_audit_runs` and `medical_pilot_method_audit_events`, stores status PENDING/RUNNING/COMPLETE/FAILED, source snapshot identity, per-position classification receipt, progress, timestamps, and error class. No original source run or reviewer ledger row is modified.
- A narrowly gated, **isolated preview** startup may automatically launch the canary once when `PDUFA_MEDICAL_METHOD_AUDIT_CANARY_AUTORUN=true`; manual same-origin Start/Resume remains available. No other NCT can start.
- **The audit is NOT an independent clinical grade, a new trial source retrieval, a medical assessment pass, a Phase III regulatory prediction or a model accuracy calibration.** The separate reviewer and FDA prediction states remain unchanged.

## Live interface and API

- New `PilotMethodAuditMonitor.tsx` inside the MAIN live monitor shows exact-NCT job status, **0–800 saved source-check positions**, 0–40 assessed source groups, next source position, last actual receipt and last verified status time. It only shows source method progress when returned by the isolated backend.
- `/api/predictions/medical-method-audit` requires a signed-in ChatGPT-adjacent dashboard session and exact pilot ID. GET uses a read key, POST uses the medical operational key and enforces same-origin request. No fallback to production, no client-visible secret.
- `/api/internal/medical-method-audit/{nct}/latest` is read-only. `POST /api/internal/medical-method-audit/{nct}/runs` starts only this saved source-classification audit and requires operational internal-key authorization.
- Both paths have strict fail-closed event/status validations, 800-position sum, source-category allowlist, timestamp checks, and **ABSTAIN / NOT_CALIBRATED** invariants. A malformed source event or unauthenticated read returns unavailable, not success.
- Main review ledger continues to show **independently graded** methods out of 800 separately from the 800 source-check receipts, and the original 12-stage source research worker remains separately visible.
- The actual **FDA prediction worker and 800-method clinical grading process are still not operational**; no class probabilities or validated accuracy have been generated. The real worker added here is a *source-audit verifier*.

## Deployment and operational safeguards

- Draft Vercel feature: `feature/medical-stage4-verified-method-matrix-20261108`, PR #965.
- Original isolated Render backend tracked a different protected canary branch: `feature/predictions-durable-medical-canary-20261108`. The source-audit module and guarded main initialization/routes were installed there without copying unrelated features or changing production.
- The first isolated deployment failed startup due to a missing read-key helper on that older canary branch; the helper was added. A later deployment on 2026-11-08 returned **LIVE** and emitted original startup lines `PDUFA_MEDICAL_METHOD_AUDIT_CANARY status=PENDING sourceAuditOnly=True reviewGradesWritten=0` and `PDUFA_MEDICAL_METHOD_AUDIT_READY status=PASS ... prediction=ABSTAIN`.
- The Render preview database blocks outside network queries (empty IP allowlist). This security was **not weakened**. Job completion needs source-side authenticated status or restart readback, not inference from deployment success.
- **Restart-confirmed pilot completion:** the isolated service re-deployed [as LIVE](https://dashboard.render.com/web/srv-dbntrkpsrm7s73aec3lg) from canary commit `c9fc1baada2e4dcb4391ef664e8fd13a46708630`. Application startup logs at **2026-11-08T23:14:13Z** reported `PDUFA_MEDICAL_METHOD_AUDIT_CANARY status=COMPLETE sourceAuditOnly=True reviewGradesWritten=0` and `PDUFA_MEDICAL_METHOD_AUDIT_READY status=PASS resumed=0 gradesWritten=0 prediction=ABSTAIN`. Because the saved-run schema rejects `COMPLETE` unless 800 durable position receipts exist, this constitutes an application-level restart/readback confirmation of **800/800 source-audit positions**, **not 800 graded clinical assessments**. We did not weaken DB network protections to query records externally.
- **Browser integration not independently exercised:** the Vercel preview build and automated tests passed, but actual signed-in iPhone session credentials and a live user GET/POST through Vercel have not been verified.

- Backend and frontend regression suites include real 800 receipt persistence, exact trial restriction, incomplete-packet blocking, resumable per-assessment checkpointing, session/origin authentication, and no reviewer/grade/FDA writes.

## Scientific balance

| Work item | Completed | Remaining |
| --- | ---: | ---: |
| Original FOCUS 12-stage source packets | 29 | 0 |
| First pilot candidate source-to-method *research leads* | 15 | 785 not individually mapped in that provisional memo |
| **Independent** phase verifications | 0 | 29 |
| **Independent** 40-heading clinical reviews | 0 | 1,160 |
| **Independently graded** 20-method positions | 0 | 23,200 |
| Validated FDA approval/CRL/delay predictions | 0 | 29 |

A source check is not a clinically examined method. The missing final locked **CY 6033 SAP**, unresolved safety-event accounts, independent reviewer signoff and historical forward validation still prevent a calibrated pilot prediction.
