# Levels 9–20 development checkpoint — 2026-11-17

**Status: evidence contracts installed in a development branch; full scientific
engines NOT installed or validated.** No merge, deploy, credential change,
production data update, live forecast or owner-review completion is authorized.

The authoritative numbering comes from
\`docs/assessment-installation-levels1-20-20261114.md\` rather than the
previous Windows orchestration script's proposed fallback names. Existing
Levels 1–8 are preserved, including the partial Level 7 population/subgroup
method and partial Level 8 exposure-rate method.

## What this development slice implements

- Separate, source-bound, phase-aware evidence-review contracts for each
  scientific Level 9 through Level 20, sharing the exact-NCT, cutoff,
  retrieval and owner-source-review checks already used by Levels 2–8.
- Level 9 performs **limited benefit-risk evidence reconciliation**: it
  distinguishes source-reviewed benefit, harm, indication and population
  evidence before an owner synthesis. It never combines them into an arbitrary
  weighted score or declares benefit-risk positive from counts.
- Pre-application and pre-result unknowns are \`NOT_YET_EXPECTED\` where
  appropriate; missing CMC/inspection information is not labeled deficient.
- The candidate research response carries all twenty level IDs, but explicitly
  separates implemented **partial scientific methods (1–8)** from the
  **contract-only levels (9–20)**. All new scores are null and FDA
  predictions ABSTAIN; no prospective accuracy is implied.

## Additional development — November 17

**Level 9 now includes `scientific-benefit-harm-alignment-v1`.** This method
only operates on two separately accepted owner-reviewed benefit/harm source
records with dated retrieval receipts. It checks declared analysis population,
treatment/comparator arm identity, follow-up days and time origin. Discordant
study contexts require explicit review and never get pooled. Identical metadata
do **not** establish comparable clinical effects, efficacy, causality, harm
severity or overall benefit-risk. A positive benefit-risk verdict is never
generated.

**Level 10 now includes `scientific-standard-care-context-v1`.** This method
compares source-reviewed guideline and standard-of-care statements for disease,
subtype, care setting and region, with a strict guideline-effective-date cutoff.
It shows structural mismatch, not whether any therapy is appropriate or any
guideline is current. Source availability and author/reviewer claims must not
be promoted to external verification or a clinical recommendation.

Both Level 9 and 10 produce partial **research methods only**. Scientific scores
stay null, FDA decisions ABSTAIN and whole-level status NOT_VERIFIED. Earlier
Levels 1–8 and all original prediction-history records remain unchanged.
Tests exercise matching and mismatching contexts, invalid booleans/counts,
wrong-trial and post-cutoff evidence, absent retrieval receipt and early-phase
abstention. GitHub CI on the final delivered commit must verify the tests; no
local-only or prior-commit run proves delivery.

## Completion gates

| Level | Research question and method still needed before scientific completion |
|---|---|
| 9 | Partial evidence-context alignment implemented; clinical meaningfulness, contradictory harms/benefits and owner indication-specific synthesis still outstanding |
| 10 | Partial dated guideline/comparator context matching implemented; source completeness, guideline applicability and actual owner clinical adjudication still outstanding |
| 11 | Patient-specific burden, alternatives, unmet need and source-grounded outcome meaningfulness |
| 12 | Independent cohort identity, nonduplicated studies, heterogeneity and prespecified synthesis |
| 13 | Exact application/cycle identity, filing acceptance, dated dossier/agency evidence |
| 14 | Official designation documents linked to exact indication and application |
| 15 | Relevant official review/advisory precedents without leaking the target outcome |
| 16 | Application/facility-specific manufacturing, quality and inspection evidence with nonpublic facts marked UNKNOWN |
| 17 | Versioned sponsor disclosures, exact-program discrepancy and contradiction adjudication |
| 18 | Owner scientific counterargument and alternative explanations tied to accepted citations |
| 19 | Outcome-unexposed prospective frozen model artifacts and genuine out-of-sample calibration |
| 20 | Official application-cycle goal/action dates, extensions and comparison only after prediction persistence |

Tests added for exact identity, cutoff, review provenance, early-phase
missingness, abstention, and integration on synthetic fixtures. CI on this
branch is the only source of delivered-commit test results; **this document
does not claim that CI has passed**. Legacy scores and all historical
versions remain intact.

Production is unchanged. The branch must not be deployed automatically;
its name is disabled in \`new-platform/frontend/vercel.json\`.
