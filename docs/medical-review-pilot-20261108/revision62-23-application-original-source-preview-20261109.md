# MAIN Revision 62 — 23-application source drilldown on FDA Predictions page

**Status: successfully verified in development, NOT production.** November 9, 2026. Original draft [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965), branch `feature/medical-stage4-verified-method-matrix-20261108`.

## Applied change

- The development `/predictions` screen now includes **23 expandable provisional FDA application source-review groups**, each containing links back to the unique exact-NCT clinical evidence records. Groups display sponsor-reported stage **as unverified**, current-registry primary result coverage, current reported statistical comparison count, current adverse-event arm coverage and case-specific missing-originals/reviewer tasks.
- Group source data derive **only** from [R60 original source challenge](https://github.com/pdufa/pdufa-command-center/actions/runs/42709199117/artifacts/13715890359) through the already reviewed R61 preview and retained original preliminary application crosswalk. Shared NCTs do not duplicate a unique trial's evidence or purport to be independent clinical studies.
- Search by ticker/drug/indication/NCT, source availability filters, and expandable application → exact NCT → source/assessment links work through client-side read-only rendering. They do not create a medical grade, run an FDA prediction, fetch unauthenticated live data, edit sources, call a backend, or change the historical outcome ledger.
- All future approval-vs-CRL and review-delay outputs remain **ABSTAIN**. `signedScientificReview=false` for every application, `independentlyValidatedFdaForecasts=0`, numeric probability `null`, measured accuracy `null`. Existing R39 unofficial research leans are not converted into model predictions.

## Files in draft branch

- `new-platform/frontend/lib/focus-r62-application-source-review.ts`: membership-preserving 29→23 derivation; fails closed on duplicate/unknown/missing exact-NCT links, approval claims, forged clinical grade, or source-verification mismatch.
- `new-platform/frontend/app/predictions/FocusApplicationSourceReviewR62.tsx`: expandable source-only application dashboard.
- `new-platform/frontend/app/predictions/page.tsx`: renders the R62 source grouping before the existing R60 trial source drilldown.
- `new-platform/frontend/tests/focus-r62-application-source-review.test.cjs`: canonical roster, shared-trial, safety/primary source availability, Savara, missing-source recovery, tamper/reviewer-status and read-only visual integration tests.
- `new-platform/backend/scripts/verify_r61_view_projection_r62.py`: extra explicit output receipt comparing **all** compact fields exactly to the SHA-256-pinned immutable R60 original record, rather than relying only on totals.
- `.github/workflows/main-r62-application-source-review.yml`: branch-scoped guarded test, pinned original-source restore, 7 adversarial field-tamper checks, frontend TypeScript check and full production-mode Next.js compilation, without deployment.

## Verified original-source engineering run

[GitHub Actions run #42712151086](https://github.com/pdufa/pdufa-command-center/actions/runs/42712151086) **SUCCESS** at `6948d84b421383f51caa093660a77cc0ede63e64`:
- Fixed original POOL/FOCUS data hashes and retired-feature guard passed.
- Immutable R60 original SHA and every R61 UI source field, including posted p-value literals, serious AE affected/at-risk denominators and NCT source hashes, matched; seven deliberate valid-looking mutations were rejected.
- Frontend R60/R62 behavior tests, TypeScript typechecking and Next.js build passed.
- Source parity certificate saved to [artifact #13716910703](https://github.com/pdufa/pdufa-command-center/actions/runs/42712151086/artifacts/13716910703) through **2027-02-07**.

**Not completed:** independent medical/statistical adjudication for 29 FOCUS trials, original prereadout locked SAP authentication, CMC/FDA action-cycle verification, prospective FDA outcome scoring, original Track B backtests, reliability calibration, production deployment or automated onboarding of the R62 research panel into the main live service. Only a guarded draft development UI and its source audit passed.

**Next:** maintain the established isolation; add original source-specific clinical/statistical review assignments and signed attestations with a safe reviewer identity contract, then validate historical forecasts out of time before releasing calibrated predictions. Do not promote a preliminary research signal to clinical or FDA outcome certainty.
