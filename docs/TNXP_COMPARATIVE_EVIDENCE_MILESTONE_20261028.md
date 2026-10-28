# TNXP comparative evidence milestone — October 28, 2026

Continues PR #522 from da935979 without replacing the existing 50-level protocol, research views, restrictions or source records.

## New primary FDA evidence

The [FDA NDA 219428 application index](https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?ApplNo=219428&event=overview.process) records ORIG-1 approval on August 15, 2025, Type 3 New Dosage Form, STANDARD review. The currently displayed documents are the label and approval letter. No clinical/statistical review link was displayed; this does not establish that those records do not exist.

The linked [original FDA label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/219428s000lbl.pdf), section 14, Table 2, printed page 15, identifies RESILIENT as Trial 3, NCT05273749, with efficacy baseline counts of 225 placebo and 231 active participants, total 456. This corroborates the analysis denominator, **not prespecified authority for the one-participant exclusion**. Its subsequent explanation of Trial 2 is postdecision context and is not imported into historical prediction features.

The population audit now preserves this FDA context separately as OUTCOME_ONLY. Original publication time, original bytes and document hash remain unverified. The signed final SAP/amendment history, exclusion/deviation record, pre-unblinding timing and all-457 analysis remain missing. Read-only Drive searches did not find those records; that is not proof they do not exist. RESILIENT compliance stays NOT_ESTABLISHED, not compliant or violating.

## Implemented comparison

A source-bound matrix reuses the existing source-cited research notes:

| Trial | Source-reported primary | Separate sensitivity | Important limit |
| --- | --- | --- | --- |
| RELIEF / F304 | Positive, p=0.010 | No-imputation p=0.004 | Population/site/duration not established from the current matrix sources |
| RALLY / F306 | Failed, MMRM + multiple imputation p=0.115 | No-imputation p=0.014 | Favorable sensitivity does not replace the failed primary analysis |
| RESILIENT / F307 | Positive, p=0.00005 | Not established in current matrix | 457 randomized versus 456 efficacy; exclusion compliance remains open |

Effects, adverse-event discontinuations, safety events and missing information remain distinct by trial and source. Adverse-event withdrawals are not automatically drug-caused events. No p values, effects or safety rates are pooled; cross-trial differences are not interpreted as randomized causal comparisons. Same-program trials are not three independent FDA validation cases.

The TNXP dossier and both existing dashboard research views now expose this matrix and the FDA outcome context behind expandable sections. No source observation, population arithmetic or software test completes an independent assessment or changes the abstaining prediction contract.

## Verification and remaining work

TNXP population/comparison tests: **43 passed**. Frontend: **404 passed**, TypeScript and the standard production build passed. Snapshot drift checks pass. Final combined research/CI results are recorded on PR #522 with the prospective-registration increment.

The unchanged 146-row history is processed; six priority cases remain ineligible for independent chronological validation. No new forecast or real prospective registration was created. Independently certified assessments remain 0/40 per case and completed investigation levels 0/50. Accuracy and calibrated probabilities are unmeasured.

Next evidence priority: signed exclusion authority and all-randomized analysis, followed by independently authenticated FDA review/CSR records. No merge, deployment, production data changes, scanner/schedule changes, list/FS/FA changes, spreadsheet writes or trading.
