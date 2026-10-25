# KEYNOTE-024 historical safety source reconciliation — two dates, two populations

**Scope:** NCT02142738 historical pilot, isolated read-only scientific review, not a current PDUFA forecast. This does **not** change the eight-domain scores (all null), input readiness FAIL (5/12 source-supported), or reluctance HIGH.

## 2016 original NEJM publication (data cutoff May 9, 2016)

The paper randomized **154 pembrolizumab** and **151 chemotherapy** participants. Its Table 3 describes **as-treated** safety populations of **154 and 150**, because one chemotherapy-assigned participant withdrew before study treatment.

- Source: https://www.nejm.org/doi/full/10.1056/nejmoa1606774 — Table 3 and 'Adverse Events' section
- PubMed: https://pubmed.ncbi.nlm.nih.gov/27718847/

| Treatment-related safety category, original report | Pembrolizumab, n=154 | Chemotherapy, n=150 |
|---|---:|---:|
| Any grade | 113/154 (73.4%) | 135/150 (90.0%) |
| Grade 3–5 | 41/154 (26.6%) | 80/150 (53.3%) |
| Serious treatment-related (any grade) | 33/154 (21.4%) | 31/150 (20.7%) |
| Led to treatment discontinuation (any grade) | 11/154 (7.1%) | 16/150 (10.7%) |
| Led to death | 1/154 (0.6%) | 3/150 (2.0%) |

The original paper separately reports **immune-mediated adverse events regardless of treatment attribution** of 29.2% vs 4.7% (any grade), and 9.7% vs 0.7% (grade 3–4), with no grade 5 immune-mediated event reported. These are **not** equivalent to 'any grade' or 'grade 3–5 treatment-related events'.

The pure adapter checks only one-decimal arithmetic concordance with the original counts/denominators. It is not an independent adjudication of patient-level events, causality, incidence rate, exposure-adjusted effects, grading, or complete safety surveillance.

## Follow-up: published January 8, 2019 (data cutoff July 10, 2017)

- Journal of Clinical Oncology DOI 10.1200/JCO.18.00149; PubMed 30620668: https://pubmed.ncbi.nlm.nih.gov/30620668/
- Grade 3–5 treatment-related AEs: **31.2% pembrolizumab vs 53.3% chemotherapy** in the updated report. The change from 26.6% to 31.2% is a later report with a different data cutoff, **not** a discrepancy to be 'fixed' by overwriting the original 2016 record.
- The later report describes **82 on-study chemotherapy-to-pembrolizumab crossovers**, an observed intention-to-treat OS HR of **0.63 (95% CI 0.47–0.86)** and a **two-stage crossover-adjusted** OS HR of **0.49 (95% CI 0.34–0.69)**. The latter is a **model-based sensitivity estimate**, not a newly randomized arm comparison.
- The publication is **2019**, even though the DOI contains '.18' and related research was presented in 2018. Never label these as 2018 published findings.

## Archived ClinicalTrials.gov group reconciliation remains unresolved

The live audit of the checksum-verified archived record identified **five distinct treatment-course safety groups**. They must stay separate because the registry event groups can reflect first-course, crossover and retreatment populations. Posted registry counts for 'seriousEvents', 'otherEvents' and deaths are not automatically the original publication's **treatment-related and graded** events.

- Cross-system attribution, treatment-relatedness, exposure and risk-period harmonization: **incomplete**.
- Original signed protocol/SAP and prespecified OS alpha boundary effective before May 9, 2016: **not independently verified**.
- The NEJM original article links `nejmoa1606774_protocol.pdf`, but the supplement could not be downloaded in this review. Its signed/amended effective dates are therefore not established. The later December 20, 2017 ClinicalTrials.gov protocol/SAP version cannot retrospectively establish prospective May 2016 prespecification.

## Implementation

The authenticated pilot endpoint `GET /api/scientific-assessment/pilot/keynote024` adds `publishedSafetyReconciliation` alongside existing `scientificReadiness`, `sourceEvidenceAudit` and the eight unscored domains. Safety records carry exact source links, per-class numerator/denominator, the journal study-analysis cutoff, published percentages and explicit review limitations.

The frontend checks exact source IDs/URLs, five original safety rows, the distinct as-treated (154/150) vs randomized (154/151) counts, follow-up cutoff, crossover methods and lack of score/approval forecast. Unsafe responses fail closed. Nothing writes to the database or changes PIPELINE, GEM JR/GEM, WT, FS/FA presets, trading rules or scans.

**Next scientific step:** independently inspect the original NEJM protocol supplement / effective original SAP and reconcile the five archived safety-course groups with original trial population denominators, grades, causality and exposure. The conservative grades remain FAIL / HIGH until those inputs are assessed.
