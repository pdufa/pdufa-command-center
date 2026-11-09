# Frozen Level 3-style historical research: AZN / Ultomiris / IgA nephropathy

## Method and provenance

**Directional assessment (recorded before consulting the official decision record in this workflow): APPROVAL LEAN** for a potential **accelerated-approval label expansion**. This assessment is qualitative and not a validated numerical probability.

**Critical contamination disclosure:** Historical search results displayed that this case had an approval outcome *before this dossier was authored*. The analysis is therefore **NOT BLIND** and must not enter accuracy or calibration calculations, even though the official decision will be opened only **after** this predecision-evidence dossier has been committed. This ordering alone cannot undo outcome exposure.

- Sponsor: Alexion / AstraZeneca (AZN).
- Product: Ultomiris (ravulizumab-cwvz), C5 complement inhibitor.
- Indication: adults with primary IgA nephropathy at risk for disease progression.
- Exact Phase 3 study: **I CAN, NCT06291376**.
- FDA review: supplemental BLA for a new IgAN indication, priority review **June 15, 2026**.
- **Goal date caveat:** June 15 company disclosure specifies **Q4 2026**, not an exact Oct 21 target. Oct 21 is sourced separately as the **eventual FDA action date**; do not backfill it as a confirmed predecision PDUFA goal.
- Predecision cutoff for evidence used in this reasoning: **June 15, 2026**.
- This is a **manual three-layer research review**, not the operational 12-stage/20-level 800 scientific assessment engine.

## Level 1 — Trial design and efficacy

I CAN (NCT06291376) is an ongoing randomized, placebo-controlled Phase 3 trial of intravenous ravulizumab in adults with IgA nephropathy. The prespecified interim analysis measured 24-hour urinary protein/creatinine ratio (UPCR) at **week 34**. AstraZeneca's June 6 disclosure reported:
- treatment-arm UPCR reduction **46.6%** from baseline;
- placebo arm reduction **5.6%**;
- relative placebo-adjusted difference **43.4%**, with reported **p below 0.0001**.
- Trial showed statistically convincing reduction in a kidney-disease surrogate endpoint, but not final preservation of renal function; week 106 eGFR data are pending.
- An *October 23, 2026* NEJM paper exists but was **published after the relevant FDA action** and is **not admissible** as predecision evidence for this reconstruction.

## Level 2 — Clinical benefit and safety

IgA nephropathy can progress to chronic kidney disease and kidney failure, with an immunological basis for complement modulation. Proteinuria reduction is clinically important and mechanistically relevant, but **proteinuria is a surrogate outcome**, not proof of fewer kidney failures or an eGFR slope benefit.

AstraZeneca's dated June 6 press disclosure reported **no new safety signals** relative to established Ultomiris risk management; common side effects included upper respiratory infection 11.3%, nasopharyngitis 9.2%, and infusion reactions 8.4%. Ultomiris already carries a **serious encapsulated-bacterial, especially meningococcal, infection risk** from terminal complement blockade, requiring vaccination and risk management. Risk-benefit in a new population remains important.

## Level 3 — FDA regulatory reasoning

Favorable:
1. Randomized positive Phase 3 prespecified interim surrogate endpoint, substantial effect size (43.4% placebo-adjusted).
2. **FDA acceptance and Priority Review** publicly announced June 15, 2026.
3. Drug has prior FDA approvals, safety experience and known complement inhibition; this is an indication extension rather than an untested molecule.
4. Sponsor was explicitly seeking **accelerated approval** while longer-term eGFR confirmation continued.

Unresolved:
1. The **week 106 renal-function endpoint** had not matured.
2. The surrogate may not translate one-to-one to clinical benefit; FDA may restrict label and require confirmatory studies.
3. Serious infection risks and nonpublic CMC / inspection / FDA review feedback. Unknown records are **gaps**, not invented deficiencies.

**Predecision-evidence directional conclusion: APPROVAL LEAN**, most coherently as **accelerated approval conditioned on continued clinical-benefit verification**. No probability or certainty numeric should be assigned until genuine model validation.

## Source list — documents dated no later than cutoff

- April 21, 2026, positive I CAN prespecified interim topline:
  https://www.astrazeneca-us.com/media/press-releases/2026/ULTOMIRIS-ravulizumab-cwvz-demonstrated-statistically-significant-and-clinically-meaningful-reduction-of-proteinuria-in-adults-with-immunoglobulin-A-nephropathy-in-I-CAN-Phase-III-trial.html
- June 6, 2026, quantitative Phase 3 efficacy and safety:
  https://www.astrazeneca-us.com/media/press-releases/2026/ULTOMIRIS-ravulizumab-cwvz-demonstrated-43-point-4-percent-reduction-in-proteinuria-vs-placebo-in-adults-with-immunoglobulin-A-nephropathy-at-34-weeks-in-I-CAN-Phase-III-trial.html
- June 15, 2026, FDA priority review and Q4 date (no exact day):
  https://www.astrazeneca.com/media-centre/press-releases/2026/ultomiris-granted-priority-review-in-the-us-as-treatment-for-adults-with-immunoglobulin-a-nephropathy.html
- Study identity:
  https://clinicaltrials.gov/study/NCT06291376

## Historical comparison rules

The frozen assessment above is not to be modified after opening the FDA approval letter. Store the actual outcome in a **separate comparison file** referencing the frozen commit SHA, with flags outcomeExposedBeforeFreeze=true, blind=false, excludedFromProspectiveAccuracy=true and excludedFromRetrospectiveBlindValidation=true. Keep live FOCUS (29) and all original SMMT/INO/GSK/PHAR/ABBV files unchanged.
