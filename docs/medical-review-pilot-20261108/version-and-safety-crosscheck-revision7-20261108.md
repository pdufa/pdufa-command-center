# MAIN scientific source review — revision 7: official endpoint-version chronology and safety reconciliation

**Trial:** ACACIA-HCM / Cytokinetics / aficamten / NCT06081894 / EU CT 2023-505797-15-00 / Protocol CY 6033  
**Research date:** 2026-11-08. **Scope:** Source comparisons and reviewer task preparation. **NOT:** an independently verified protocol-integrity verdict, clinical grade, clinical signoff, FDA probability, or accepted nHCM sNDA.

This is an additive follow-up to [revision 5 original protocol audit](./authenticated-am4-original-protocol-revision5-20261108.md) and [revision 6 public SAP search](./locked-sap-public-audit-revision6-20261108.md). Earlier source receipts and the 29-trial database remain untouched.

## 1. Official ClinicalTrials.gov record-change chronology

The official [NCT06081894 Record History](https://clinicaltrials.gov/study/NCT06081894?tab=history) lists **31 submitted versions**. The relevant dates and changed-field categories are:

| Version | Submission date | Official changed categories | What is and isn't established |
| --- | --- | --- | --- |
| v26 | 2025-01-11 | Study Status; Contacts/Locations | Comparison baseline for v27. This overview alone does not show the historical endpoint text. |
| **v27** | **2025-05-15** | **Study Status; Sponsor/Collaborators; Study Design; Outcome Measures; Eligibility** | **Confirmed that changes in outcomes/study design were registered on this date.** The official history index alone does not identify the exact additions/deletions. |
| v28 | 2025-10-27 | Recruitment Status; Study Status; Contacts/Locations | Near the independently captured CTIS original protocol Amendment 04 dated **2025-10-28**, but a one-day separation in different systems does not prove amendment approval or final analysis lock chronology. |
| v29 | 2026-01-29 | Study Status; Outcome Measures | Another outcome-measure version entry. Need original before/after outcome definitions. |
| v30 | 2026-08-03 | Study Identification; Study Status; Outcome Measures | Another outcome-measure entry before the Aug 28 publication. |
| v31 | 2026-09-21 | Study Status | Latest version in the checked history. |

A **secondary indexed comparison** at [DataLookout's NCT06081894 change log](https://dashboard.datalookout.com/trial/NCT06081894) reports the primary-outcome count moved from **one to two** at v27 and the enrollment target from **420 to 500**. Treat those *specific previous/current values* as **SECONDARY_INDEX_REQUIRES_OFFICIAL_VERSION_DIFF**, rather than as independently recovered official historical fields.

**Scientific interpretation:** Changing outcome descriptions is not automatically post hoc manipulation. Critical questions: original v26/v27 definitions, source timing of protocol/SAP amendments, enrollment/data availability at that date, prespecification prior to any database unblinding and acceptable alpha handling. Do not turn a registry change category into a failure or an FDA prediction.

## 2. Original Phase 3 protocol and statistical plan chronology

The publicly obtained [CTIS Protocol CY 6033, Amendment 04](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398) is dated **2025-10-28** (90 PDF pages, SHA-256 `853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8`). Its section 9.4.1.1 describes controlling familywise two-sided alpha 0.05 with a prespecified graphical procedure. The sponsor's [August 28 efficacy release](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Results-from-ACACIA-HCM-Presented-in-Hot-Line-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026-and-Published-in-The-New-England-Journal-of-Medicine/default.aspx) reports the two primary tests evaluated in parallel at **0.025 per endpoint**. The initial allocation is potentially compatible with the larger graphical family, but the complete graph, recycling weights, prespecified version/date and actual testing implementation remain unverified **because the final locked SAP has not been obtained**.

Published primary effects: KCCQ-CSS +3.0 points, p=0.021; pVO₂ +0.67 mL/kg/min, p=0.003. Both meet the sponsor-reported initial thresholds. Secondary LAVI p=0.058 did not meet nominal significance; cardiovascular-event p=0.678 is descriptive if the formal gate stopped there. *Primary statistical success is not a validated FDA benefit–risk probability or independent clinical signoff.*

## 3. Specific source-identity and safety questions

| ID | Source A | Source B | Unresolved question |
| --- | --- | --- | --- |
| REV7-COUNT | [May 2026 topline release](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx): **516** randomized and treated (outside Japan) | [August 2026 full results](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Results-from-ACACIA-HCM-Presented-in-Hot-Line-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026-and-Published-in-The-New-England-Journal-of-Medicine/default.aspx): **517** randomized and treated (outside Japan) | Sponsor may have reconciled analysis populations/data cutoffs; require dated CONSORT tables, randomized/treated definitions and patient-accounting source. **Not a confirmed error.** |
| REV7-HF-SAE | [Secondary responder paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) lists **11 vs 1** serious heart-failure adverse events | [October 12 safety disclosure](https://www.globenewswire.com/news-release/2026/10/12/3379213/0/en/cytokinetics-announces-additional-data-from-acacia-hcm-presented-at-the-hfsa-annual-scientific-meeting-2026.html) lists **12 vs 3** patients | Reconcile event definition, safety cutoffs, adjudication, coding, arm denominator and cumulative follow-up. The October sponsor disclosure specifies two aficamten HF SAEs with LVEF<50%, ten without. Do not combine all-cause SAE counts with HF-only SAE counts. |
| REV7-DENOM | Responder-paper indexed interruption description previously extracted as **14 (2.7%) and 1 (0.8%)** | Published randomized arms **258 vs 259** | Check original patient table or correction and applicable exposure denominator before any derived percentages. No silent correction. |
| REV7-REGULATORY | Sponsor's November 4, 2026 10-Q describes **planned** Q4 nHCM sNDA | Approved MYQORZO use applies to **obstructive** HCM | No proof from these sources of accepted **nonobstructive** HCM filing, FDA action or PDUFA date. |

## 4. Next independent evidence actions, ranked

1. Download or access official ClinicalTrials.gov **v26 and v27 record texts** and verify exact one-to-two endpoint modification and timing. Follow with v29/v30 original differences and dated protocol amendments.
2. Obtain finalized, versioned and signed **statistical analysis plan** (SAP) from lawful publisher/sponsor access, authenticate file hash and database-lock date. Confirm original hypothesis graph and missing-data sensitivity plan.
3. Obtain complete **CONSORT randomized/treated accounting** (516 vs 517) and independent serious-heart-failure event listings (11/1 vs 12/3) with date/censoring rules.
4. Request authorized **independent phase and clinical evidence review** before creating any graded events in the persisted scientific ledger.

**Strict balance (unchanged):** Source roster 29/29 captured; independent phase verification **0/29**; independently graded methods **0/23,200** (pilot **0/800**); independent clinical signoff **0**. FDA approval/CRL/review-delay `ABSTAIN`, certainty `NOT_VALIDATED`. No direct modification to production, study membership, review history or original source receipts.
