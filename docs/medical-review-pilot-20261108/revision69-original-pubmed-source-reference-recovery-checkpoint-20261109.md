# MAIN Revision 69 — Source-locked PubMed reference leads for unposted FOCUS primary outcomes

**Verified November 9, 2026 PST.** Existing development branch `feature/medical-stage4-verified-method-matrix-20261108`, draft [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965). No production merge, clinical adjudication, external publication content verification or Track B historical lookups.

## Confirmed original-source research and engineering

- [Original registry citation source recovery run #42727350931](https://github.com/pdufa/pdufa-command-center/actions/runs/42727350931) **SUCCESS** at commit `c17da91e667bbba9b42fb4155de1c69f18f32201`.
- Original research [artifact #13723526354](https://github.com/pdufa/pdufa-command-center/actions/runs/42727350931/artifacts/13723526354), `FOCUS_17_ORIGINAL_PUBMED_REFERENCE_RECOVERY_R69.json` and human-readable `.md`, original report SHA-256 `8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77`. The original R53 registry JSON bytes, original R46 source receipts and independent R66 dated phase report were cross-checked against exact NCT IDs and SHA-256 receipts.
- Among **17** exact NCTs with **no primary table in the retained original registry copy**, **7** list **11 registry-derived PubMed reference leads**; the other **10** list no PubMed references in the frozen copy. **DERIVED** indicates a reference association in ClinicalTrials.gov, not an independently verified publication reporting that NCT's primary pivotal outcome. The article texts were **not** independently fetched, inspected or adjudicated in this revision.
- Special case retained: NCT02500381 is **one unique NCT** supporting two provisional application groups, with two different registry-listed reference PMIDs. Clinical significance and direct NCT applicability remain unknown.
- No reference was used as a clinical grade, FDA outcome, safety score, multiplicity pass or predictive calibration input. All are potential leads requiring publication body, exact NCT, original pre-unblinding SAP, study design and efficacy verification.

## Actual development dashboard installation

- [R69 original PubMed UI and source-parity run #42728063170](https://github.com/pdufa/pdufa-command-center/actions/runs/42728063170) **SUCCESS** at exact commit `ac8bd4daad06a15537d311bb0910e63106581007`.
- Source-original byte parity pass for **all 17 NCTs** and all 11 exact displayed PMIDs against the immutable original R69 report. The runtime projection additionally has a source-lock whitelist of NCT-to-PMID strings and exact R68 29/23 membership/zero-grade checks.
- **8 focused Node frontend tests passed, 0 failed**; TypeScript typecheck and optimized Next.js build passed; **real LOCAL Chromium** desktop (1365×850) and emulated iPhone-sized touch viewport (390×844) tests passed. These do not constitute actual physical iPhone Safari, signed-in production, or human publication review.
- [Browser audit and screenshots artifact #13722279145](https://github.com/pdufa/pdufa-command-center/actions/runs/42728063170/artifacts/13722279145), retained through **December 10, 2026**.
- [Exact-CI-commit READY Vercel development preview](https://pdufa-new-dashboard-7ug4pgdkz-pdufa.vercel.app/predictions/evidence-gaps), verified with HTTP 200. Includes all 29 NCTs, the 17 no-primary cases, the 7/11 reference summary, and per-NCT original PubMed links for the seven with DERIVED citations. Each missing-primary trial also links to a PubMed exact-NCT **search** (an unexecuted research option, not verification).
- The R68 scientific source-availability queue and its original 29-NCT/23-application membership, source checks, patient safety tables, eight unscored review domains, and PDF links remain intact. No automated source article fetching or scientific grading was added.

## Files installed

- `new-platform/backend/scripts/build_focus_original_literature_leads_r69.py`
- `new-platform/backend/tests/test_focus_original_literature_leads_r69.py`
- `.github/workflows/main-r69-original-publication-reference-recovery.yml`
- `new-platform/frontend/data/focus-r69-original-pubmed-leads.json`
- `new-platform/backend/scripts/verify_r69_original_literature_ui_parity.py`
- `new-platform/frontend/lib/focus-r69-original-publication-leads.ts`
- `new-platform/frontend/app/predictions/evidence-gaps/OriginalPublicationLeadsR69.tsx`
- `new-platform/frontend/app/predictions/evidence-gaps/OriginalPublicationLeadsR69.module.css`
- Modified `new-platform/frontend/app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx` to insert these references with clear source-only warnings.
- `new-platform/frontend/tests/focus-r69-original-publication-leads.test.cjs`
- `new-platform/frontend/scripts/verify-r69-original-pubmed-browser.cjs`
- `.github/workflows/main-r69-original-publication-dashboard.yml`

## True scientific readiness

- 29 exact FOCUS trials; 23 provisional application cycles.
- 17 with no current posted primary table in the retained registry version; only 11 unverified PubMed reference leads across 7 of those records. The other 10 have no such reference in that archived copy, not proof that relevant papers do not exist.
- Original 232 eight-domain source-review positions **unscored** and original 466 indexed method PDF page references **not adjudicated**.
- Qualified phase reviewers **0**, independent actual clinical method grades **0**, independently verified exact trial publication primary outcome reports **0**, FDA future approval/CRL/review-delay forecasts independently validated **0/23**, historical accuracy unavailable; FDA future outcome **ABSTAIN**.
- No production, medical review ledger, historic Track B, GEM/retired scan, FOCUS/POOL membership, or model-training write.

## Next development (R70)

Independently inspect full candidate article content and exact-NCT references, and search original sponsor/journal/CSR/regulatory documents for the remaining evidence gaps. If the publication is not a direct result report for the exact NCT, explicitly flag it as background/indirect rather than changing the no-primary status. Maintain evidence receipts, source dates, contradictory information, clinical reviewer/signature gating, and rigorous no-forecast-release limits.
