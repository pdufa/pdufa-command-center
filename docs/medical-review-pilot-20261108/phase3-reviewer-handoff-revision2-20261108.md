# MAIN — ACACIA-HCM Phase 3 scientific reviewer handoff, revision 2

**Trial:** NCT06081894 / Cytokinetics / aficamten / symptomatic nonobstructive hypertrophic cardiomyopathy (nHCM)  
**Date of this research note:** 2026-11-08 UTC  
**Status:** Source-research addendum; **not** an independently verified clinical phase, graded method, FDA recommendation, or regulatory prediction.  
**Preceding immutable packet:** [Initial source capture and receipt manifest](./README.md) and [receipts.json](./receipts.json). This addendum **does not overwrite** the initial packet or its receipts.

## Primary source crosscheck

| Source / date | Original location | Current claim and audit treatment |
| --- | --- | --- |
| ClinicalTrials.gov exact-NCT sponsor registry record, last posted 2026-09-22 in the preserved capture | https://clinicaltrials.gov/study/NCT06081894 ; API https://clinicaltrials.gov/api/v2/studies/NCT06081894 | Reports PHASE3 and ACTIVE_NOT_RECRUITING, estimated enrollment 500, actual primary completion 2026-08-31 and estimated study completion 2026-11. These are registry *facts*, not independently reviewed phase signoff. The preserved packet already captures the original response. |
| NEJM primary publication, published online 2026-08-28, DOI 10.1056/NEJMoa2603021 | https://www.nejm.org/doi/10.1056/NEJMoa2603021 ; PMID 42663312 | 517 randomized participants, 258 aficamten vs 259 placebo. At week 36 KCCQ-CSS LS mean difference +3.0 points (95% CI 0.5–5.5, P=0.02); peak VO2 +0.67 mL/kg/min (95% CI 0.22–1.11, P=0.003). Full original analysis and SAP are required to review missingness, multiplicity and population definitions. |
| NEJM indexed supplementary material | https://www.nejm.org/doi/10.1056/NEJMoa2603021 | The publisher's current indexed page **lists** a 4.63-MB protocol PDF named `nejmoa2603021_protocol.pdf` and 800-kB supplementary appendix named `nejmoa2603021_appendix.pdf`. This resolves a *discovery lead* only: access/download, revision date, completeness, protocol-to-SAP correspondence and contents **have not been verified**. This note does **not** claim the PDFs were retrieved or analyzed. |
| Sponsor 2026-11-04 10-Q (quarter ended 2026-09-30) | https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm | Reports LVEF <50% in ~10% aficamten and ~1% placebo; specifically, serious adverse events of heart failure in **12/258 (4.7%) vs 3/259 (1.2%)**. This is a sponsor disclosure; these heart-failure events should not be conflated with the NEJM abstract's **all-cause serious adverse events**: 52/258 (20.2%) vs 38/259 (14.7%). Obtain coding, timing, adjudication, drug exposure, and reversible-dysfunction criteria before concluding causality or net benefit–risk. |
| Sponsor 2026-11-04 earnings exhibit, Exhibit 99.1 | https://www.sec.gov/Archives/edgar/data/1061983/000119312526447198/cytk-ex99_1.htm | Says Cytokinetics **expects to submit** a supplemental NDA for nHCM in **Q4 2026**. That is **not proof of submission, FDA acceptance, a PDUFA date, approval, or filing for this specific indication**. Do not transfer MYQORZO's obstructive-HCM authorization into the nHCM application. |
| Sponsor 2026-10-12 HFSA release | https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx | Announces additional CPET, dose-titration and safety analyses. Same trial, therefore not independent replication. Abstracts/poster data need original analytic text before grading. |

## Highest-priority phase-appropriate scientific assessment handoff

The installed phase-first catalog treats these **11** assessment headings as critical investigative prompts for a Phase 3 source review. They are **not eleven completed assessments**. Each contains 20 methods; the current signed-off method count remains zero.

| Assessment ID | What the available sources support | Unresolved data/reviewer action |
| --- | --- | --- |
| 4.1 Randomization, blinding and comparator | Registry and NEJM publication identify randomized, placebo-controlled, double-blind design. | Inspect actual randomization, masking integrity, concealment, deviations and CONSORT flow in primary report/protocol. |
| 4.2 Endpoint selection and clinical meaning | Dual co-primary KCCQ-CSS and peak VO2 at week 36; published placebo-adjusted magnitudes and 95% CIs. | Check endpoint version history, clinically important thresholds, FDA endpoint acceptability and prespecified hierarchy. |
| 4.3 Estimands, intercurrent events and missingness | Preliminary publication supports endpoint timing. | Obtain original and amended SAP, treatment-policy/intercurrent-event definitions, imputation and sensitivity analyses. No completion inferred. |
| 4.4 Population, allocation and power | Published 517 randomized vs source registry estimated 500. | Reconcile amended target vs achieved sample, power assumptions, strata, dropouts and indication-specific enrollment. |
| 4.5 Conduct, deviations and data integrity | Dated registry and publication identities are captured. | Obtain protocol amendments, site/deviation logs, withdrawals, inspections and blinded data-cleaning evidence. |
| 5.1 Pivotal primary efficacy | Published positive placebo-adjusted primary measures (KCCQ-CSS and peak VO2) with nominal statistical results and CIs. | Verify prespecified testing threshold and original analysis sets; do not convert positive P values into approval probabilities. |
| 5.2 Secondary endpoints and multiplicity | Sponsor's earlier release describes parallel alpha allocation, and previously collected exploratory papers contain secondary findings. | Reconcile full SAP testing sequence, numerical rounding, exploratory versus confirmatory claims and unadjusted analyses. |
| 5.3 Integrated safety and competing harms | NEJM all-cause serious AEs plus newly reviewed 10-Q HF-serious-AE counts and LVEF threshold results. | Analyze SAE line listings, time-at-risk, reversibility, titration, censoring, causality and comparative disease severity. |
| 5.4 Subgroup robustness | Sponsor reports consistency; same-trial analysis summaries are available. | Need interaction effects/CIs, multiplicity plans and independent assessment of heterogeneous HCM phenotypes. |
| 8.1 Integrated benefit–risk assessment | Efficacy and safety signals both exist in the published record. | No reconciled benefit–risk grade until the above evidence and clinical reviewer signoff are available. |
| 8.2 Adversarial and contradictory evidence | Preserved initial packet includes exploratory/secondary uncertainties and difference in responder percentages across reports. | Investigate discrepancies using original tables, amendment history and the full primary clinical report. |

## Next evidence retrieval sequence

1. **Protocol/SAP discovery and verification:** attempt publisher-provided protocol and appendix download using a legally authorized route. Record HTTP result, source document identity, bytes/hash, version/date and the distinction between protocol and standalone SAP. A listed file is not a reviewed file.
2. **Phase-review worksheet for NCT06081894:** named independent reviewer checks original registry identity, protocol date, PHASE3 status, single vs multiple phase declarations, and whether any prior completed trial is linked by a distinct exact NCT. The sponsor registry alone cannot attest clinical phase verification.
3. **Full clinical report reconciliation:** co-primary endpoint analysis populations, multiplicity, missing data, adverse events/heart-failure events, and placebo comparison. Preserve favorable and unfavorable findings.
4. **Regulatory cycle audit:** check public FDA or sponsor filing documentation for the **nHCM** sNDA only; as of the cited November 4 disclosure, filing remains planned. No PDUFA date should be inferred.
5. **Only after independent authorization:** append reviewer phase-event and evidence-backed method reviews via existing immutable ledger procedures. No automatic phase events, scores, signed reviews or FDA forecasts from this note.

## Current controlled status

- Exact-NCT source and primary-review queue population: **29/29 saved**.
- Pilot source document discovery updated here; **new authorized medical reviewer phase events: 0**.
- Independently graded pilot positions: **0/800**; completed assessments: **0/40**.
- All 29-trial potential method positions: **23,200**; source collection stages: **348**.
- FDA APPROVAL/CRL/REVIEW_DELAY: **ABSTAIN**; model certainty **NOT_VALIDATED**.
- The 29-trial source roster, original receipts, history, isolated PostgreSQL, production and retired scan rules are unchanged.

**Interpretive constraint:** This is a source-linked research handoff, not an independent clinical adjudication, complete scientific grade, medical advice, regulatory recommendation or calibrated probability.
