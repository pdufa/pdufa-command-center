# MAIN R65 — phase-first independent scientific adjudication intake and display

**Verified November 9, 2026 PST.** Draft-only [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965), development branch `feature/medical-stage4-verified-method-matrix-20261108`. No production merge, production deployment or FDA forecast release.

## Engineering acceptance and archived original research

- [R65 full original-source, frontend and local browser CI #42718930965](https://github.com/pdufa/pdufa-command-center/actions/runs/42718930965) — **SUCCESS** on commit `e64dd0395d500750209f9209691f41b411f4e872`. Both **independent source-intake builder** and **read-only assessment view** jobs succeeded, including original R63 SHA checks, tamper/membership tests, exact archived R65 source-to-UI checklist comparisons, TypeScript, optimized Next.js build and browser interaction checks.
- [Original R65 unsigned 232-task worklist #13717809389](https://github.com/pdufa/pdufa-command-center/actions/runs/42718930965/artifacts/13717809389) retained through February 7, 2027: `FOCUS_29_TRIAL_232_HUMAN_REVIEW_INTAKE_R65.json` and `FOCUS_HUMAN_REVIEW_READINESS_R65.md`. Rebuilt from **SHA-pinned immutable original R63 source** `b39028e972c45949147d405c447af45ef8ceab7089d8e89247cacd1d2cef6a18`, which is the unreviewed archived clinical PDF page-lead matrix, not a clinical source adjudication.
- [Exact original R65 output #13717848415](https://github.com/pdufa/pdufa-command-center/actions/runs/42717833879/artifacts/13717848415), from first fully verified R65 source-intake run, is byte-locked with SHA-256 `1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a`. The frontend presentation and source-to-UI parity tests explicitly use that original archived docket, rather than a fabricated or newly inferred review result.
- [Local-browser UI evidence #13717989320](https://github.com/pdufa/pdufa-command-center/actions/runs/42718930965/artifacts/13717989320) retained through December 9, 2026: real local Chromium desktop (1365×850) and iPhone-sized touch-viewport (390×844) exercises checked expanding/collapsing review checklists, 17 required source/signoff fields, the 8 original domains, correct original-PDF anchor, missing-source NCT `NCT05126758`, unscored grade state and **zero browser JavaScript errors**. This is *not* physical iPhone Safari or a signed-in clinical reviewer acceptance.
- Exact-commit [Vercel medical development preview](https://pdufa-new-dashboard-i79g6gfit-pdufa.vercel.app/predictions/assessment?nct=NCT04544293) was READY and returned HTTP 200. The selected Savara case renders the R65 review-readiness section below original R64 PDF page leads and above the existing separate 800-method assessment matrix. A CAPR no-current-PDF source case also renders all eight unsigned review tasks with zero page hits, not a fabricated failure.

## Scope and actual installation

- **29 unique FOCUS trial NCTs** and **23 provisional FDA application groups**, preserving the exact source crosswalk and avoiding double-counting shared NCT research.
- **8 domains × 29 NCTs = 232 original-source reviewer tasks**, and **466 machine-generated PDF page references** from 22 public PDF files in the existing R63 corpus; 12 NCTs have machine page hits and 17 do not have currently attached page leads. **These are not 232 independently graded scientific methods or the user's contemplated 800 assessed scientific methods per trial.**
- Eight domain-specific independent research checklists: original primary endpoint; estimand and analysis population; statistical model; multiplicity control; missing data and intercurrent events; sensitivity; adverse events and safety; protocol/SAP version changes.
- Each task identifies original page leads, prospectively locked original source-document provenance, source version and date, first-public/unblinding chronology, source-positive/negative/contradictory/missing evidence classifications, method applicability, reviewer identity and role, independent second verifier, signed review-event identity, and review rationale. Phase must be independently verified **first**.
- The generated worklist and dashboard have **zero signed independent phase reviews**, **zero signed scientific method reviews**, **zero clinical grades**, **zero scientific safety/efficacy adjudications**, **zero validated FDA application forecasts** and **no measured historical accuracy**. `ABSTAIN` remains the only approved future FDA approval/CRL/review-timing status.
- A separate disabled-by-default clinical reviewer API already exists under `medical_reviewer_submission.py` with explicit role separation and a **single pilot trial** gate. **R65 does not enable it or provide 29-trial reviewer write access.** Full roster authentic reviewer submission and scientific review must be separately approved, properly credentialed, and auditable.
- No production, science ledger, FOCUS roster, retired RAAS scanner, original clinical source, historical Track B outcomes, or model training writes occurred.

## Files installed and verified

- `new-platform/backend/scripts/build_focus_reviewer_adjudication_intake_r65.py`
- `new-platform/backend/tests/test_focus_reviewer_adjudication_intake_r65.py`
- `new-platform/frontend/lib/focus-r65-independent-review-gates.ts`
- `new-platform/frontend/app/predictions/assessment/IndependentReviewerReadinessR65.tsx`
- `new-platform/frontend/app/predictions/assessment/IndependentReviewerReadinessR65.module.css`
- `new-platform/frontend/tests/focus-r65-independent-review-gates.test.cjs`
- `new-platform/frontend/tests/focus-r65-original-worklist-parity.test.cjs`
- `new-platform/frontend/scripts/verify-r65-human-review-gates-browser.cjs`
- `.github/workflows/main-r65-scientific-reviewer-intake.yml`
- Source page route integration in `new-platform/frontend/app/predictions/assessment/page.tsx`.

## Next release gates

1. Conduct a qualified external independent trial phase review with real identity, documented authority, original signed pre-unblinding protocol/SAP version and source timing, not inferred from PDF keywords.
2. Reconcile complete Phase 3 efficacy, estimand/multiplicity hierarchy, missingness, and exposure-adjusted safety for each trial; recover sponsor/CSR/journal/regulatory originals for trials without posted registry results. Document contradictory evidence rather than auto-failing an absent current registry source.
3. Only after real human review authorization, implement and validate a separate audited, least-privilege reviewer workflow for authorized 29-trial scope. Never quietly expand the existing single-trial pilot write API or convert source-intake flags into scores.
4. Use append-only reviewer event history and explicit supersession, independent secondary verification and source hashes before considering any 0–5 method grade, clinical level, or aggregate science score.
5. Keep **historical Track B** embargoed while taking prospective predictions; independently verify 23 application-cycle identities and complete prospective/out-of-time FDA outcome validation and calibration before releasing any numerical probability or accuracy claim.

**Status:** R65 engineering intake and read-only dashboard acceptance **COMPLETE**; authenticated independent scientific adjudication **NOT STARTED/NOT VERIFIED**; Stage 4 research remains active; production remains untouched.
