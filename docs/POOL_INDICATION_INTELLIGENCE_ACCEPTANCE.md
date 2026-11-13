# POOL → INDICATIONS → FOCUS: integration acceptance

Status: DRAFT implementation, **not** production acceptance. All requested capabilities must share source identities; a UI shell is not a completed scientific assessment.

## Required capabilities (15)

| # | Requested capability | Draft coverage | Definition of complete |
|---|---|---|---|
| 1 | Full disease hierarchy and deeper subtypes | Existing MeSH hierarchy and unified 5-level selector | Preserve all source paths, custom deeper levels and source provenance |
| 2 | Biomarkers and mutations | Missing / explicitly marked unverified | Clinical subtype, gene, assay, cutoff and source tied to exact indication |
| 3 | Disease severity and patient subgroups | Registry eligibility on demand | Severity, line of therapy, subgroup definition, and independently sourced criteria |
| 4 | All clinical phases and FDA stages | Separate phase columns including mixed phases, results and FDA | Phase verified from exact-NCT source with stage updates and status provenance |
| 5 | Click phase counts to show matching trials | Implemented in draft matrix | Verified full-POOL counts, distinct exact NCT + ticker within each branch and stage |
| 6 | Multiple indications per drug or trial | Split indication rows; deduplicate trials | Adjudicated many-to-many indication IDs; do not treat punctuation alone as a verified identity |
| 7 | Search disease, company, drug, NCT | Implemented in draft UI | Search full source inventory, audit query and restrictions |
| 8 | Indication-specific scientific assessment | On-demand registry facts; no adjudication | Disease-specific clinical questions, source-backed findings, independent challenge |
| 9 | Efficacy and endpoints | Official registry endpoints and posted measurements | Effect size, statistical uncertainty, prespecification, clinical importance and phase readiness |
| 10 | Existing treatments and competitors | Pending | Current standard of care, competing clinical trials, resistance and differentiation |
| 11 | Eligible patient population and unmet need | Registry eligibility only; market denominator unavailable | Disease prevalence distinct from eligible patients, enrollment and commercial TAM |
| 12 | Scores, risk reasons and confidence | Explicit NOT SCORED | Phase-specific calibrated rubrics, documented uncertainty, no unsupported probabilities |
| 13 | Trial/company details and popups | Trial modal, links to current Analyze Now / FOCUS | Full company ownership, rights, trial, indication and exact source relationships |
| 14 | POOL → FOCUS assessment integration | Exact NCT + ticker FOCUS flag; missing matches surfaced | Verified promotion gates and evidence reuse without treating historical scores as active |
| 15 | Automated evidence updates and assessment history | Live source retrieval only | Dated source snapshots, trigger-based reassessment, immutable versions, diff explanations |

## Identity and evidence rules

- Preserve POOL without applying the restricted FOCUS market cap to the master universe.
- Trial identity is exact NCT ID; FOCUS cross-link requires exact NCT + ticker.
- Indication-specific analysis must not be transferred automatically between different tumor subtypes, treatment lines or clinical populations even if the drug is shared.
- Taxonomy matching is **candidate routing**. An exact unique MeSH name is not independent clinical validation; ambiguous names remain explicit review tasks.
- One NCT with several indications is one trial in ancestor branch totals; retain distinct indication-analysis records.
- Phase 1 is not penalized for missing phase 3 results. Unknown, not yet expected, source unavailable and failed evidence are separate states.
- Registry endpoint posting is not outcome adjudication, a drug approval or an investment signal.
- No assumed approval probabilities, confidence intervals, earnings or patient market sizes.
- Do not change production scans, existing predictions, FDA outcome archives, trading, merges or deployments as part of this draft PR.

## Final acceptance gates

1. Frontend TypeScript, unit tests, end-to-end authenticated browser check and full production build pass on the exact head SHA.
2. Backend regression suite passes; any unrelated baseline failures are separately reconciled with the canonical FOCUS roster rather than suppressed.
3. Test minimum multi-indication and hierarchy-branch cases with double-count prevention; verify unmatched FOCUS identities are visible.
4. Confirm POOL source parity and all clinical phases against backend; verify eligible FOCUS matches using both ticker and NCT.
5. Review adverse cases: stale sources, conflicting indication matches, missing biomarker evidence, discontinued/withdrawn studies, FDA cycles without exact NCT linkage.
6. Verify full clinical dossiers against authoritative sources for a representative Phase 1 oncology, Phase 2 non-oncology and late-stage FDA candidate.
7. Confirm immutable assessment version history, recomputation trigger, and specialist source-review signoff before marking the 15-feature installation complete.

No merge or deployment authorization is implied by implementation work or these acceptance conditions.
