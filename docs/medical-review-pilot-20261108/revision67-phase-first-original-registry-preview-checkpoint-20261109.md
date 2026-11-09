# MAIN Revision 67 — phase-first original registry evidence dashboard

**November 9, 2026 (PST).** Continued directly on existing development branch `feature/medical-stage4-verified-method-matrix-20261108` and draft [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965) after the Codex cloud-agent work session hit its usage limit. Uncommitted changes from that interrupted session were **not** present at the branch head when checked; R67 was implemented as new commits against verified R66 source evidence instead. No merge or production promotion.

## Verified research source and engineering

- Immutable verified original **R66** [run #42720903307](https://github.com/pdufa/pdufa-command-center/actions/runs/42720903307), [artifact #13720041195](https://github.com/pdufa/pdufa-command-center/actions/runs/42720903307/artifacts/13720041195), research SHA-256 `be3f8f0f4351579a7eddea2ebb67654992f8dd8f5125cbd78bf56ed440f43257`.
- **[R67 acceptance workflow #42723793892](https://github.com/pdufa/pdufa-command-center/actions/runs/42723793892) SUCCESS** at commit `f904ae301c11ac460c89ea10b03cdb126f3d6d30`. Original R66 source-to-frontend comparison passed for **all 29** original NCTs; **23** existing provisional FDA application memberships were retained. Five R67 test cases passed (zero failures), TypeScript typecheck and optimized Next.js build succeeded, and real **local Chromium** browser interactions succeeded at desktop (1365×850) and an iPhone-sized touch viewport (390×844).
- Browser receipt and screenshots: [artifact #13721807125](https://github.com/pdufa/pdufa-command-center/actions/runs/42723793892/artifacts/13721807125), retained through **December 9, 2026**. This is local-browser emulation, not physical iPhone Safari, user-authenticated production testing, or qualified clinical validation.
- The [exact development Vercel deployment at R67 CI SHA](https://pdufa-new-dashboard-c0nf8kqsz-pdufa.vercel.app/predictions/assessment?nct=NCT04544293) reports **READY**. Signed-in-capable Vercel preview retrieval returned HTTP **200** with the new R67, original R64 pages, R65 independent reviewer readiness, and the final FDA outcome-status section. The combined Phase 2/3 case `NCT04871282` also rendered the special design-review flag in the exact-SHA Vercel preview.
- No source data, original FOCUS/POOL roster, production forecasts, model training, Track B outcomes, independent reviewer signatures, or clinical-grade ledger were changed.

## Actual installed UI / source files

1. `new-platform/frontend/data/focus-r67-original-phase-source.json`: tiny, read-only 29-NCT snapshot of source-reported phase, registry status/update date, status verification month, allocation, masking, enrollment, enrollment reporting type, primary completion and date reporting type. Derived strictly from original R66 artifact; no synthetic status values.
2. `new-platform/backend/scripts/verify_r67_original_phase_ui_parity.py`: byte-pinned original R66 source and source fields parity, 29 unique NCTs/23 memberships, all saved columns, no FDA release or phase signatures.
3. `new-platform/frontend/lib/focus-r67-phase-source.ts`: fail-closed cross-check against existing R60/ R65 exact NCT, shared application crosswalk, original registry sha, research-level abstain invariants and observed-at archive cutoff.
4. `new-platform/frontend/app/predictions/assessment/OriginalRegistryPhaseR67.tsx` and CSS: new responsive phase-first panel, original ClinicalTrials.gov link, updated source evidence and date, expandable study design and issue flags, and explicitly unverified independent phase.
5. Existing `new-platform/frontend/app/predictions/assessment/page.tsx`: R67 phase evidence **before** R64 protocol/SAP method PDF pages and R65 unsigned independent reviewer intake. Adds a clear FDA outcome and certainty status immediately after R65, before the existing separate 800-method architecture display.
6. `new-platform/frontend/tests/focus-r67-original-phase-first.test.cjs`, `new-platform/frontend/scripts/verify-r67-phase-browser.cjs`, `.github/workflows/main-r67-phase-first-source-dashboard.yml`: adversarial data changes, original source parity, actual browser links/expand-collapse, cross-viewport ordering and no-score constraints.

## Exactly what the source evidence says

- Original registry snapshot: **28 Phase 3 only**, **1 combined Phase 2/3**, **19 completed**, **8 active-not-recruiting**, **2 recruiting**. These statuses are registry-reported **as of each stored last-update-posted date**, not live current trial-phase validation.
- Combined Phase 2/3: `NCT04871282` remains a review-required study-design classification; its phase has not been independently adjudicated.
- Allocation N/A: `NCT06331299` is explicitly flagged as not automatically randomized; no unsupported double-blind/risk inference or negative score is asserted.
- Shared trial `NCT02500381` remains **one NCT under two provisional application groups**, not two independent source trials.
- The existing eight scientific domains, 232 unscored source-review positions, 466 machine-indexed original PDF page leads and separate 800-method architecture are untouched and do not imply completed scientific reviews.
- All **29 source-reported phases collected**, **0 qualified independent phase-verification events**, **0 signed method grades**, **0/23 validated FDA approval/CRL/review-timing predictions**, and **no measured/calibrated historical accuracy**. `ABSTAIN` is the only authorized future FDA outcome.

## Next installation steps

- Obtain genuine qualified independent phase signoffs and original pre-unblinding phase/endpoint/SAP version chronology.
- Reconcile original posted and unposted efficacy/safety sources, statistical multiplicity, source conflicts and the exact regulatory application cycles.
- Keep a signed, append-only two-reviewer clinical event ledger separately permissioned from the disabled single-pilot reviewer API. Do not automatically expand write access to all 29 studies.
- Continue historical out-of-time blinded FDA outcome validation in the separately embargoed Track B dataset before numerical prediction accuracy, probabilities or certainty are published.

**Status:** R67 engineering research/UI installation **COMPLETE on development**; clinical independent assessments and measured FDA forecast accuracy **NOT COMPLETED**; draft PR unmerged and production unchanged.
