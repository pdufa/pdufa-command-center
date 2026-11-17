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

## Levels 11–20 partial screening methods — November 17

All are **development-only, unvalidated research methods**, not complete
scientific assessments. None produces a score, FDA approval probability,
genuine blind classification, source-attestation claim, or trading instruction.

- **L11 \`scientific-therapeutic-context-v1\`:** computes a descriptive
  cases/declared-population rate with strict integer denominators, and compares
  alternative-treatment evidence for the same declared cohort. Not a population
  prevalence estimate, market-size estimate, or proof of unmet need.
- **L12 \`scientific-replication-candidate-screen-v1\`:** validates distinct
  NCT identifiers, ClinicalTrials.gov URLs, retrieved cutoff dates, stated
  study contexts and repeated cohort labels. Registry identity does not
  establish study independence or replicated efficacy.
- **L13 \`scientific-regulatory-context-v1\`:** reconciles owner-reviewed
  original FDA application type/number/review-cycle and filing acceptance dates.
  Matching documents are not independent agency certification or approval.
- **L14** uses that method's original FDA designation lead and exact indication
  linkage. A designation may precede a filing, and never predicts approval.
- **L15 \`scientific-precedent-cmc-screen-v1\`:** screens dated official
  historical FDA actions for a *different* application. No use of the target
  postdecision outcome to make an apparent predecision prediction.
- **L16** distinguishes a disclosed original public inspection record from
  unavailable/nonpublic records. Unknown facility/CMC facts are not deficiencies.
- **L17 \`scientific-disclosure-challenge-v1\`:** compares two separately
  reviewed dated sponsor claims for the same NCT and statement key. A changed
  text is not proof of wrongdoing or clinical materiality.
- **L18** records two alternative scientific hypotheses with source provenance.
  The owner must still adjudicate which explanations, if any, are supported.
- **L19 \`scientific-forecast-outcome-integrity-v1\`:** crosschecks bounded
  SHA-256 source/model digest references and ordered timezone-aware
  timestamps of *submitted* prediction artifacts. This is not verified
  immutable storage, blind source isolation, a calibrated model or a valid
  prospective result.
- **L20** compares original dated FDA goal with separately sourced official
  action at the same application/review-cycle and calculates calendar-day
  difference. It never merges an outcome into forecast features, validates
  prediction accuracy or counts withdrawal as binary approval-vs-CRL.

The associated tests use **synthetic fixture data** and must pass CI on the
final branch head. Real source review, genuine source authenticity checks,
original application adjudication, owner-level clinical synthesis, model
training/calibration, immutable outcome-isolated persisted forecast history,
production migration/activation and live validation are still outstanding.

## Completion gates

| Level | Research question and method still needed before scientific completion |
|---|---|
| 9 | Partial evidence-context alignment implemented; clinical meaningfulness, contradictory harms/benefits and owner indication-specific synthesis still outstanding |
| 10 | Partial dated guideline/comparator context matching implemented; source completeness, guideline applicability and actual owner clinical adjudication still outstanding |
| 11 | Partial descriptive burden/alternative context method; representative epidemiology, patient relevance and unmet-need conclusions outstanding |
| 12 | Partial exact-NCT/cohort-collision screen; true independence, effect replication and prespecified synthesis outstanding |
| 13 | Partial original FDA application/date reconciliation; authenticated application linkage, filing completeness and agency adjudication outstanding |
| 14 | Partial designation source lead; original indication/pathway verification and meaningful regulatory interpretation outstanding |
| 15 | Partial historical FDA precedent screen; clinical/regulatory comparability and advisory evidence review outstanding |
| 16 | Partial public-record availability screen; original facility-specific CMC/inspection adjudication outstanding |
| 17 | Partial dated disclosure-text comparison; materiality, amendment context and owner reconciliation outstanding |
| 18 | Partial alternative-hypothesis record; owner scientific adjudication outstanding |
| 19 | Partial submitted freeze metadata integrity check; trusted immutable isolation, real prospective forecasting and calibration outstanding |
| 20 | Partial original goal/official action chronology; extensions, trusted prediction linkage, calibrated hit-rate reporting and live integration outstanding |

Tests added for exact identity, cutoff, review provenance, early-phase
missingness, abstention, and integration on synthetic fixtures. CI on this
branch is the only source of delivered-commit test results; **this document
does not claim that CI has passed**. Legacy scores and all historical
versions remain intact.

Production is unchanged. The branch must not be deployed automatically;
its name is disabled in \`new-platform/frontend/vercel.json\`.
