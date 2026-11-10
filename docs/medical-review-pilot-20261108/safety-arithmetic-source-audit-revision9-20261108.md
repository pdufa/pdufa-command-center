# MAIN — ACACIA-HCM numerical safety-source audit, revision 9

**Trial** NCT06081894 (CY 6033; EU CT 2023-505797-15-00). **Checked** 2026-11-08. **Status** Research-only public-document arithmetic check. No clinical verification, grade, FDA recommendation or outcome probability. Source packets and 29-trial roster unchanged.

## Original source comparison: keep endpoint definitions separate

| Report | Original source | Aficamten | Placebo | Arithmetic audit using randomized groups 258 / 259 |
| --- | --- | ---: | ---: | --- |
| Serious **heart-failure** adverse events, secondary published analysis | [Circulation responder paper (PMCID PMC13674601)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) | **11 (4.3%)** | **1 (0.4%)** | 11/258 = 4.3%, 1/259 = 0.4%; internally consistent at 1 decimal. |
| Serious **heart-failure** adverse events, later sponsor disclosure | [2026-11-04 SEC 10-Q](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm), also [2026-08-28 sponsor full-results announcement](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Results-from-ACACIA-HCM-Presented-in-Hot-Line-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026-and-Published-in-The-New-England-Journal-of-Medicine/default.aspx) | **12 (4.7%)** | **3 (1.2%)** | 12/258 = 4.7%, 3/259 = 1.2%; internally consistent at 1 decimal. |
| **All-cause** serious adverse events, published analysis | [Circulation responder paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) | **52 (20.2%)** | **38 (14.7%)** | Not the same event category as heart-failure-only SAEs. |
| LVEF below 50%, published analysis | [Circulation responder paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) | **27 (10.5%)** | **2 (0.8%)** | Numerators agree with their rounded percentages. |
| Per-protocol LVEF-related **treatment interruption**, published narrative | [Circulation responder paper, Safety](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) | **14 (2.7%)** | **1 (0.8%)** | **Numerators do not reconcile using randomized arm denominators:** 14/258 = **5.4%** and 1/259 = **0.4%**. |
| LVEF below 40%-related interruption, sponsor's earlier reporting | [Second-quarter 2026 SEC quarterly filing](https://www.sec.gov/Archives/edgar/data/1061983/000119312526338217/cytk-20260630.htm) | **3%** | Not given | Rounded percentage; do not manufacture a numerator without original tables. |

The 11/1 source and sponsor 12/3 numbers were publicly reported in the same August 28, 2026 publication window (with later repetition), so a simple October update cannot by itself explain the difference. Specific analysis windows and event definitions still need the source tables.\n\nThe published randomized arm denominators are **reference denominators**, not proof that they are the correct population for every safety endpoint. Denominator differences, exposure sets and event definitions require the actual line listings. Nevertheless the interruption-report arithmetic mismatch **cannot be dismissed** by interpreting 14/258 as 2.7% without a different denominator. A separate research commentary reports **7 (2.7%)** [here](https://opensourcecardiology.org/doi/osc.2026.0037); this is a **lead**, not authorization to silently replace the peer-reviewed publication's numerators. Verify journal original PDF, figures, errata and exact per-protocol interruption definition first.

## Which outstanding scientific methods this informs

- **5.3 Integrated safety:** Heart-failure SAE numerator source differences, LVEF event and treatment-interruption definitions, treatment windows, exposure denominators.
- **8.1 Integrated benefit–risk:** Do not use the all-cause SAE numerator to correct HF-only SAE counts, or conflate statistical endpoint success with benefit–risk approval.
- **8.2 Adversarial evidence:** Preserve both publication and sponsor versions, discrepancy alerts, time-point and database-cutoff questions, and the inability to verify an authorized final SAP or actual SAE listings.
- **4.4/4.5 Allocation and conduct:** Topline 516 versus full-results 517 is a different **participant-count reconciliation**; not resolved by checking the safety endpoint denominators alone.

## Original document / SAP search status

An exact-NCT source search of ClinicalTrials.gov v2 and publicly indexed EU CTIS documents still shows **no separately available final signed SAP**. The previously retrieved [Amendment 04 original CTIS protocol](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398) is authenticated and machine-readable, but explicitly delegates some primary missing-data sensitivity analyses to the separate SAP. The [published secondary analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) states that this *secondary responder analysis* was added to the SAP before database lock; this **author claim does not establish the contents or signing date of the locked primary SAP**. Sponsor's participant-level sharing procedure requires qualified-researcher review and generally follows US/EU marketing decisions.

**Review priority:** obtain final locked SAP, its versions and amendment authorization, paired serious-heart-failure event listing and cutoff definitions, and journal-interruption correction/analysis population details.

**Controlled remaining balance:** 29/29 source packets; 0/29 independently certified clinical phases; 0/1,160 independently completed 40-assessment groups; 0/23,200 independently scored 20-method positions; 0/29 final FDA predictions. *All forecast types ABSTAIN / certainty NOT_VALIDATED.* These are research-document issues, not confirmed FDA findings or clinical failures.
