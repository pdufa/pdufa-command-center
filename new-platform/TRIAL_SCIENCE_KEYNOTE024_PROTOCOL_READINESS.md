# KEYNOTE-024 protocol evidence: two independent readiness grades

**Scope:** isolated historical Trial Science pilot, exact trial NCT02142738.
**Output:** source-evidence completeness gate and reluctance-to-conclude gate.
These are not clinical efficacy grades, PoA values, PDUFA forecasts, or trade signals.

## The crucial protocol version problem

- Original KEYNOTE-024 randomized interim data cutoff: **May 9, 2016**.
  Original trial: https://pubmed.ncbi.nlm.nih.gov/27718847/
- ClinicalTrials.gov currently links a **protocol and statistical analysis plan
  dated December 20, 2017**, version **024-11**. Its cover states the amendment
  is applicable only to **Japan**.
  https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf
- In the 2017 document, **Section 8.1.1, p. 112** describes randomized ITT
  efficacy analysis and blinded independent radiologic PFS; **Section 8.1.2,
  p. 113** defines safety using all-subjects-as-treated and crossover handling;
  **Sections 8.1.3, p. 113 and 8.2.6, p. 122** describe family-wise Type I
  error control, step-down endpoints, and OS alpha spending.
- FDA-staff-authored published historical approval summary reports PFS
  HR **0.50 (95% CI 0.37–0.68)**, and interim OS HR **0.60 (95% CI 0.41–0.89)**,
  with interim OS p=0.005 compared against allocated alpha 0.0118.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/
- **Critical limitation:** availability of a *later* sponsor-amended SAP
  does **not** independently verify the exact prespecified analysis plan
  effective before the 2016 interim readout. Obtain the earlier version,
  dated amendments, decision boundaries and change history before declaring
  prospective prespecification verified. The 2016 NEJM article lists a
  supplementary protocol, but listing a supplement is not proof that its
  full chronology has been reviewed.

## The two independent grades

The pilot evaluates twelve explicit source-evidence checks:

| Grade | Current output | Meaning |
|---|---|---|
| **Input readiness (pass/fail)** | **FAIL** | Five checks have source support, seven require reconciliation or have missing critical inputs. Full 20-level investigation is not complete. |
| **Reluctance (low/moderate/elevated/high)** | **HIGH** | Contemporaneous protocol/SAP evidence and complete regulatory/CMC package are critical outstanding inputs. Scientific conclusions must remain provisional. |

These are *readiness* and *uncertainty* labels only. **FAIL does not mean
pembrolizumab failed its clinical trial**, nor is HIGH an FDA rejection probability.
The completed historical trial had published positive findings and an FDA
approval. This pilot is about whether the automated appraisal has retrieved
and independently evaluated everything needed for a reliable dossier.

A grade becomes PASS only if every required input is individually
source-supported. Any critical BLOCKED input forces HIGH reluctance.
Even PASS/LOW would authorize **review of evidence**, not automatic confidence,
a numerical efficacy score or a live trading decision.

## Twelve explicit checks

1. Source-verified archived NCT identity.
2. Published original PFS with FDA scientific corroboration.
3. Published original interim OS with FDA corroboration.
4. Published treatment-related grade 3–5 adverse events (not all-cause).
5. **BLOCKED:** Original pre-interim protocol history.
6. **REVIEW_REQUIRED:** Prospectively effective multiplicity and OS boundaries.
7. **REVIEW_REQUIRED:** Complete safety populations, immune AEs and denominators.
8. **REVIEW_REQUIRED:** Crossover effects and long-term OS sensitivity.
9. **REVIEW_REQUIRED:** Missingness, patient flow and population reconciliation.
10. **REVIEW_REQUIRED:** Exploratory patient-reported outcome analysis.
11. Historical FDA efficacy basis (not a current application prediction).
12. **BLOCKED:** Complete regulatory/CMC source review.

The live API response supplies each check's exact source URL and within-source
locator, evidence status, rationale, next research action and critical flag.

## Implementation boundaries

- The existing endpoint `GET /api/scientific-assessment/pilot/keynote024`
  appends a `scientificReadiness` object **after** verifying the stored NCT
  identity and archived JSON SHA-256. It is authenticated, read-only, and
  performs no live source downloads.
- The frontend validates exact NCT ID, protocol version and cutoff, every
  citation allowlist entry, both grade calculations, required unresolved
  items, and the continued absence of scientific scores and approval forecasts.
- Input-readiness and reluctance grades are distinct from the already
  existing trading/research `decision_readiness` gate and do not modify
  existing GEM JR/GEM/WT scoring, FS/FA preset associations, rankings, lists,
  scripts, database records, scans or trade actions.
- The isolated pilot is **historical**. A future use on still-pending PDUFA
  events requires separate regulatory-source date verification and
  prospective validation.

## Next independent appraisal steps

1. Locate and version-check 2016-or-earlier trial protocol, amendments and
   signed SAP; reconcile to prospective enrollment and readout timestamps.
2. Reconcile serious, treatment-related, all-cause, immune-mediated and fatal
   events by denominators and follow-up exposure. Do not compare immune AEs
   against the overall grade 3–5 TRAE category as if equivalent.
3. Compare ClinicalTrials.gov tables against the published reports, including
   all endpoints, censoring, subgroup multiplicity and missingness.
4. Trace the historical FDA review and approval chronology separately from
   manufacturing and CMC evidence. Do not confuse later label table updates
   with original 2016 data cutoffs.
5. Obtain an independently documented critical scientific review before
   permitting any *scientific success* rating or forecast.
