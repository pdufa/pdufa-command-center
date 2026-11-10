# MAIN Revision 58 — Savara IMPALA-2 regional multiplicity and protocol amendment chronology

**Research observation:** 2026-11-09 (Pacific). **Trial:** NCT04544293 / SAV006-05. **Application group:** `svra-molgramostim`. **Track:** current FOCUS independent medical research; existing draft PR #965 only. This is a source-anchored *research reconciliation*, **not** patient-level statistical reproduction, signed SAP validation, independent clinical adjudication, FDA outcome prediction, or regulator conclusion.

## Original and contemporary cited sources

1. Current registry-attached **SAP v1.0 dated 2024-04-24**, pp. 25–27 (physical PDF pages 25–27): https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf ; R56 originally pinned SHA-256 `2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888`.
2. Current registry-attached **protocol v10 dated 2024-10-09**, Appendix 8, pp. 115–125 (physical PDF pages 116–126): https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf ; R56 originally pinned SHA-256 `0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849`.
3. **Savara original June 26, 2024 IMPALA-2 topline release**, p-values and sponsor's multiplicity labels: https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx
4. **Peer-reviewed Phase 3 report**, published August 20, 2025: https://www.nejm.org/doi/full/10.1056/NEJMoa2410542 (corroborates non-significant hierarchical SGRQ Activity and that subsequent secondary tests do not support confirmatory inferences).
5. Current registry trial results, source of the separate R57 original-record evidence hash: https://clinicaltrials.gov/study/NCT04544293?tab=results
6. A **nonprimary registry mirror** provisionally reports all-subject A-aDO2 Week 24 `p=0.1043`: https://findtrial.co/trial/NCT04544293 . This specific number has NOT been reconciled against R57's original registry JSON and MUST NOT be promoted as independently validated Japan/Korea analysis.

## Regulatory-authority testing strategies specified in current SAP

These are **testing strategies intended for different regulators**, not proof that the statistical analyses are restricted to patients living in those regions. The original SAP calls for the full analysis set (FAS).

**Outside Japan and South Korea:** one Week 24 DLCO primary at two-sided alpha 0.05. Only if passed does Week 48 DLCO receive alpha 0.05. Only if both pass is alpha split into independent **Week 24** and **Week 48** families at **0.025 each**. Each secondary family contains SGRQ Total, SGRQ Activity, and exercise capacity, with a Hochberg step-up procedure (`m=3`). For ascending p-values the candidate thresholds are **0.025/3 = 0.008333…**, **0.025/2 = 0.0125**, and **0.025**, applying Hochberg from largest to smallest.

| Gated family | Outcome | Source-reported two-sided p | Deterministic Hochberg/serial result |
| --- | --- | ---: | --- |
| Primary gate | DLCO Week 24 | 0.0007 | Passes nominal 0.05 gate |
| Sequential gate | DLCO Week 48 | 0.0008 | Passes nominal 0.05 gate |
| Week 24, alpha=0.025 | SGRQ Total | 0.0072 | **Pass:** smallest p <= 0.008333… |
| Week 24, alpha=0.025 | SGRQ Activity | 0.0149 | **Not family-wise significant:** second p > 0.0125 |
| Week 24, alpha=0.025 | Exercise capacity | 0.0845 | Not significant |
| Week 48, alpha=0.025 | SGRQ Total | 0.1046 | Not significant |
| Week 48, alpha=0.025 | SGRQ Activity | 0.1216 | Not significant |
| Week 48, alpha=0.025 | Exercise capacity | 0.0234 | **Nominal p < 0.05 only;** smallest p > 0.008333… |

These mechanical decisions agree with Savara's 2024 disclosure: Week 24 primary DLCO, Week 48 DLCO and Week 24 SGRQ Total significant; Week 24 SGRQ Activity and Week 48 exercise capacity **nominal only**, not multiplicity-qualified. This independently checks the *published p-value/threshold arithmetic*, **not** the p-values' source calculations, prior locked protocol, regulatory interpretation or biological benefit–risk.

**For Japan and South Korea:** SAP §5.3.2 (physical PDF p. 27) specifies a different hierarchy: first Week 24 DLCO at alpha=0.05; then a single **four-endpoint** Hochberg family at alpha=0.05: Week 24 SGRQ Total, SGRQ Activity, exercise capacity, and A-aDO2. The four ascending threshold levels are **0.0125, 0.016666…, 0.025, 0.05**. The released June 2024 sponsor table does not supply a fully authenticated A-aDO2 result, so **do not issue an adjudicated Japan/Korea family conclusion**. If the secondary registry mirror's `0.1043` were genuinely the corresponding prespecified full-FAS A-aDO2 p-value, a *conditional, arithmetic-only* demonstration using `[0.0072, 0.0149, 0.0845, 0.1043]` would pass SGRQ Total and SGRQ Activity. That conditional result is **NOT** evidence of a signed region-specific regulatory finding; it must be withheld from clinical/FDA scoring until original registry statistics and estimands are independently checked. It does not replace the sponsor's global/outside-region labels.

## Self-described original protocol amendment chronology

The current **2024-10-09 v10 document's Appendix 8 change log** supplies the following *retrospective claims about its own versions*. The earlier individual signed PDFs, original issue timestamps, approvals, database lock and treatment unblinding have **not** independently been recovered.

| Version | Date stated in v10 change log | Selected potentially material descriptions |
| --- | --- | --- |
| 1.0 | 2020-06-22 | Original protocol |
| 2.0 | 2020-08-17 | Japan/PMDA request promotes A-aDO2 Week 24 from exploratory to secondary; adds infection exclusion |
| 3.0 | 2020-09-08 | European-authority safety/exclusion/visit amendments |
| 4.0 | 2021-03-25 | Amendment 3, several design and endpoint/assessment updates |
| 5.0 | 2021-06-28 | Screening and exercise eligibility clarifications; removes an exercise test functional-impairment entry condition; log describes decision as before randomization |
| 6.0 | 2021-08-05 | Schedule and French exclusion-criterion edits |
| 7.0 | 2022-10-06 | Rescreening clarification |
| 8.0 | 2023-01-25 | Removes DLCO-stratum randomization/recruitment caps, based on enrollment trends |
| 9.0 | 2023-03-20 | Extends open-label treatment/follow-up duration and long-term safety collection |
| 9.1 | 2023-11-21 | Regulatory and assessment clarifications including French-site criteria |
| SAP 1.0 | 2024-04-24 | SAP as currently attached, **document-heading date only**; includes distinct regional alpha rules and section 11 analysis changes |
| Phase 3 topline | 2024-06-26 | Sponsor publicly discloses IMPALA-2 results |
| 10.0 | 2024-10-09 | **Post-topline protocol version** adds EU trial number and long-term exploratory GGO changes |

**Critical chronological finding:** The presently attached protocol v10 was dated *after* the Phase 3 topline. Therefore it cannot alone establish what the final endpoint/alpha schema was before analysis or unblinding. The SAP's April 24 document date precedes the topline, but **does not establish signature, lock, release or independence from data access**. No later-file discrepancy by itself proves misconduct.

## Source reconciliation conclusions and blockers

- **Resolved at research-arithmetic level:** exact outside-Japan/Korea gate/family configuration, source-reported 8 p-values, two Hochberg families, and sponsor-confirmed 3 multiplicity-qualified efficacy findings.
- **Resolved at current-document chronology level only:** retrospective 2020–2024 change-log dates and exact warning that the currently attached protocol was post-topline.
- **OPEN:** authenticate earlier exact original protocol versions (especially v9.1 before readout), original SAP signatures/versions, investigator review/approval times, treatment unblinding, database lock, and FDA-relevant actual amendment submission dates. Match the SAP Section 11 changed DLCO averaging and alpha schematic to these earlier versions and quantify any endpoint/statistical impact.
- **OPEN:** obtain original-record A-aDO2 Week 24 statistic and its exact full-FAS estimand for Japan/Korea; do not use the third-party mirror value as a verified input.
- **OPEN:** independently reproduce MMRM/multiple-imputation results and check adverse event definitions, time at risk, regulator CMC/inspection, and FDA application review-cycle source evidence.
- **OPEN:** signed independent review and a valid outcome-blind historical Track B denominator/holdout. This research arithmetic is not independent FDA prediction accuracy.

**Release and isolation invariants:** canonical 29 trials / 23 provisional application groups unchanged; no POOL/FOCUS membership edit; no retired-system dependency; no reviewer ledger grade or signoff; no trained model; `officialOutcome=ABSTAIN`, `officialTiming=ABSTAIN`, `numericalFdaProbability=null`, `historicalAccuracy=null`, `independentlyValidatedFDAForecasts=0/23`. Keep PR #965 draft and production/Track B unchanged.
