# MAIN exact-NCT evidence pilot — NCT06081894

Pilot ID: `MAIN-MEDICAL-PILOT-NCT06081894-20261108`. First capture revision: 1.
Source inspection date: November 8, 2026 UTC. **No scientific grade, independent
clinical adjudication, completed scientific test or FDA prediction is recorded.**

This additive packet continues the existing ACACIA-HCM source canary. It does not
rerun the installation source worker, change POOL/FOCUS, insert database events,
or certify the live 29-trial queue gate. The isolated database and its current
reviewer state were not accessible to this source-inspection task. A source
retrieval is not an independently reviewed scientific investigation.

## Identity, phase and source reconciliation

The original ClinicalTrials.gov API response (`CTG-1` in `receipts.json`) returns
exact NCT **NCT06081894**, sponsor Cytokinetics, protocol identifier **CY 6033**,
ACACIA-HCM, aficamten versus placebo in symptomatic **nonobstructive** hypertrophic
cardiomyopathy. The current record reports **PHASE3**, randomized, parallel,
double masked, and **ACTIVE_NOT_RECRUITING**. The record was last posted on
**September 22, 2026**, with primary completion reported as actual August 31,
2026 and overall study completion estimated November 2026.

This is a sponsor-submitted registry report, not a new reviewer-verified phase
event. The record does not establish that this same trial previously completed
Phase 1 or Phase 2. Prior completed candidate phases and their distinct exact
NCT links still require reconciliation; Phase 3 is not proof of their completion.
The existing November 8 source scan in
`new-platform/frontend/data/focus-29-registry-source-scan-20261108.json` already
identifies this trial. No earlier collected evidence has been replaced.

The registry has **no resultsSection and no documentSection** in this response,
and `hasResults` is false. It nevertheless links three dated publications.
Therefore “no registry-posted primary results” must not become “no public
readout,” a failed clinical assessment, or a score of zero. A registry completion
date is not an efficacy result. The 500 estimated enrollment in the registry
differs from the 517 randomized participants in the publication; the latter
requires an original protocol/amendment reconciliation rather than silently
overwriting the registry snapshot.

## Phase-first questions examined

The installed catalog makes trial design/statistical integrity (4.1–4.5),
efficacy/safety (5.1–5.4), and integrated challenge (8.1–8.2) critical Phase 3
questions. The first source inspection addresses endpoint identity, effect
size/precision, multiplicity claims, safety imbalance, and missing-data limits.
Its order follows this catalog; it does not claim a verified live queue rank.

| Finding ID | Classification | Source-linked observation | Limitation / next review |
| --- | --- | --- | --- |
| PILOT-IDENTITY-01 | SOURCE_FACT | Registry dual primary outcomes are KCCQ-CSS and peak oxygen uptake, both baseline to week 36. The NEJM abstract identifies the same two outcomes, exact NCT, Phase 3 trial and 258/259 randomized arms. | Original protocol/SAP version and amendment chronology remain unavailable. |
| PILOT-EFFICACY-01 | FAVORABLE_REPORTED_EVIDENCE | NEJM abstract, electronic publication August 28, 2026 (`PUBMED-1`, PMID 42663312), reports KCCQ-CSS least-squares mean difference 3.0 points (95% CI 0.5–5.5; P=0.02), and peak oxygen uptake difference 0.67 mL/kg/min (95% CI 0.22–1.11; P=0.003), aficamten versus placebo at week 36. | These are reported results, not an independent analysis. Clinical importance, estimand, missing-data assumptions and analysis populations have not been independently adjudicated. Preserve abstract rounding. |
| PILOT-MULTIPLICITY-01 | UNVERIFIED_METHOD_CLAIM | Sponsor release 2347, August 28, 2026 (`SPONSOR-1`), says the two primary endpoints were evaluated in parallel using P≤0.025 each, and reports KCCQ-CSS P=0.021. | The numerical difference from abstract P=0.02 may be rounding; do not label it contradictory without full original analysis. Obtain the prespecified SAP and endpoint hierarchy. |
| PILOT-SAFETY-01 | UNFAVORABLE_REPORTED_EVIDENCE | NEJM abstract reports reversible LVEF <50% in 27/258 (10.5%) versus 2/259 (0.8%); serious adverse events 52/258 (20.2%) versus 38/259 (14.7%), aficamten versus placebo. | Counts alone do not establish causality or an adjudicated net benefit-risk result. Obtain event definitions, timing, adjudication and exposure-adjusted analyses. |
| PILOT-SECONDARY-01 | UNFAVORABLE_OR_INCONCLUSIVE_REPORTED_EVIDENCE | Sponsor release reports no statistically significant difference for left atrial volume index (difference −1.30, 95% CI −2.64 to 0.04; P=0.058) or time to first cardiovascular event (P=0.678). | A nonsignificant comparison is not proof of no effect. Preserve the distinction from favorable co-primary findings. |
| PILOT-ECHO-01 | FAVORABLE_EXPLORATORY_REPORTED_EVIDENCE | Official PMC full text (`PMC-1`, DOI 10.1161/CIRCULATIONAHA.126.082343, electronic August 29, 2026; October 20 issue) reports improved diastolic indices, including lateral and septal e′. | This is the same 517-participant trial, not an independent replication. Its Statistical Analysis section describes a post hoc exploratory analysis with prespecified analyses without all measures specified; no multiple-comparison adjustment. Do not treat nominal P values as confirmatory tests. |
| PILOT-MISSINGNESS-01 | METHODOLOGICAL_LIMITATION | PMC full text, “Study Limitations,” describes end-of-treatment carrying forward of available week 36–72 values, smaller later samples, uncorrected multiple testing, resting echo only, and high tricuspid Doppler missingness without imputation. | Independent reviewer must examine missingness, sensitivity analyses and measurement limitations before any method grade. |
| PILOT-CONTRADICTION-01 | POTENTIALLY_CONTRADICTORY_UNRESOLVED | Sponsor release says “statistically significant improvements across all five efficacy metrics” and 53% versus 13% achieving ≥3 outcomes. The linked responder publication abstract (PMID 42663111) reports peak-oxygen-uptake responder P=0.1, and 53% versus 14% for ≥3 outcomes. | These may reflect differing analyses, rounding or source error; neither source is silently preferred. Original responder analysis definitions and full text are required. The second PMC BioC request returned HTTP 200 with an error body, so no full-text examination is claimed. |

The primary publication, sponsor disclosure and two exploratory papers describe
the **same trial**. Their agreement does not supply independent replication or
independent clinician review. Registry-linked `DERIVED` references are pointers,
not verified evidence merely because the registry lists them.

## Remaining evidence and controlled gate

| Dependency ID | State | Required evidence / action |
| --- | --- | --- |
| PILOT-PROTOCOL-01 | MISSING / ACCESS_BLOCKED | Obtain dated original protocol, amendments and complete SAP. No protocol/SAP was posted in the captured registry. Primary NEJM full-text URL and official AHA supplementary page returned HTTP 403. |
| PILOT-PRIMARY-01 | PARTIAL | Primary publication metadata/abstract captured; full primary report, supplements, participant flow, analysis populations, endpoint hierarchy, sensitivity analyses and complete safety tables remain unexamined. |
| PILOT-HISTORY-01 | NOT_RECONCILED | Compare original registry versions and protocol amendments, including enrollment and date chronology. Link any prior candidate phases by their own exact NCT; do not infer historical completion. |
| PILOT-FDA-01 | NOT_RETRIEVED | Retrieve exact nonobstructive-HCM application/review-cycle FDA documents when publicly available and reconcile the application identity. Sponsor's August 28 Q4 sNDA submission plan is not proof of filing, FDA acceptance or approval for this indication. Obstructive-HCM approval claims do not transfer to this nonobstructive trial. |
| PILOT-INDEPENDENCE-01 | BLOCKED | A separate authorized scientific/clinical reviewer must examine the original evidence, assess contradictory findings and satisfy the existing independent-review gate. No reviewer identity or clinical signoff has been invented. |
| PILOT-LEDGER-01 | NOT_IMPORTED | Validate these receipts, confirm isolated database readiness/current source-run association, and explicitly append any subsequent authorized review using the existing immutable history. Do not auto-import this source-inspection packet as a grade or phase signoff. |

No absent future-phase endpoint is classified as a current-phase failure. No
clinical grade is assigned to a missing, blocked or unexamined source.

Next action: obtain the original primary report/protocol/SAP and independent
review for this exact NCT, resolve the listed discrepancies, then validate a
single append-only method review and its revision history in the isolated
environment before expanding through the existing gates.

## History, counts and verification

This packet contains 4 successful original-source responses: one full registry
record, one NLM response containing 3 publication records/abstracts, one official
PMC full-text representation, and one full sponsor public release feed. The
sponsor API returned 601 records across years despite the requested year filter;
the complete response is preserved losslessly as gzip. Release 2347 is also
extracted verbatim as a derived JSON object for review. Additional failed
retrieval responses and HTTP codes are recorded separately; HTTP 200 alone is
not counted as retrieved full text.

**Independently graded methods: 0/800. Completed scientific assessments: 0/40.
Clinical signoffs: 0.** Source inspections and reported journal results do not
increment those counts. APPROVAL, CRL and REVIEW_DELAY remain **ABSTAIN**;
CERTAINTY remains **NOT_VALIDATED**.

Run `python docs/medical-review-pilot-20261108/verify_receipts.py` from the
repository root to verify preserved byte hashes, lossless decompression,
exact-NCT identity, DOI linkage, original sponsor extraction and absent grades.
`receipts.json` is the first source-capture revision; future corrections must add
a new manifest/review event with an explicit supersedes link rather than replace
this dated source evidence.
