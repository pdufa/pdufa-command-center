# MAIN Revision 57 — Savara IMPALA-2 actual source-reported primary efficacy and adverse-event readout

Date: 2026-11-09. Draft PR #965, `feature/medical-stage4-verified-method-matrix-20261108`.

## Verified implementation and original-source evidence

[Exact R57 GitHub Actions run #42701020773](https://github.com/pdufa/pdufa-command-center/actions/runs/42701020773) **SUCCESS**: **25** targeted tests passed, permanent retired-RAAS guard passed. Original R53/R54/R55 29 NCT / 23 application research archived source pack and separate actual [R56 Savara 10-item protocol/SAP review](https://github.com/pdufa/pdufa-command-center/actions/runs/42698835077) were restored independently from previous immutable GitHub Actions artifacts. The exact NCT04544293 current registry source record was SHA-256 checked against the original R55 trial packet, while both public PDF originals were SHA-matched against the R56 verified protocol/SAP receipts.

R57 original research output: [artifact #13711382273](https://github.com/pdufa/pdufa-command-center/actions/runs/42701020773/artifacts/13711382273), expiring 2027-02-07. Derived research JSON `SVRA_PRIMARY_SAFETY_SAP_ORIGINAL_SOURCE_FACTS_R57.json`, SHA-256 `50434f69fa47b2afd15eab7f3891fcb502200021b784b8ff4ab9b6e07d795e5b`. **Not** a scientific signoff, prespecification adjudication, original efficacy reanalysis, or FDA prediction.

## Source-reported trial results (ClinicalTrials.gov current record)

- Trial: **NCT04544293**, molgramostim versus placebo, Savara `svra-molgramostim` original application cycle.
- Primary reported endpoint: **change from baseline in percent predicted hemoglobin-adjusted DLCO at Week 24**.
- Registry-posted treatment difference: **+6.0** percentage points versus placebo; reported **two-sided 95% confidence interval +2.5 to +9.4**, and reported **p-value 0.0007**. Registry's reported statistical method: mixed models analysis; MMRM covariates reported as baseline DLCO, treatment, visit, region, severity stratification and treatment–visit interaction. This is source-reported, not an independently reconstructed analysis or proof of multiplicity-validated efficacy.
- Current registry reports **eight** secondary statistical-analysis rows. Each row is kept with its original reported p-value, effect/CI literals, and endpoint title. No family-wise adjustment or secondary testing claim is inferred.
- Original current adverse-event source arm counts: **molgramostim 14/81** people affected by serious adverse events; **placebo 20/83**. Other adverse events: molgramostim **69/81**, placebo **71/83**. No patient-level causal inference or combined-arm safety scoring is made.

Original official registry link: [ClinicalTrials.gov NCT04544293 results](https://clinicaltrials.gov/study/NCT04544293?tab=results).

## Source-pinned statistical analysis plan and protocol

- **Current attached SAP**: [NCT04544293 `SAP_001.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf), exact original SHA-256 `2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888`, document-heading date 2024-04-24. Physical PDF page **25** describes one primary endpoint and seven secondary endpoints for authorities outside Japan/Korea; page **26** describes sequential Week 24 and Week 48 DLCO gating, alpha splitting and Hochberg secondary-family testing; page **27** describes control-based missing-data imputation and the primary MMRM.
- **Current attached protocol**: [NCT04544293 `Prot_000.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf), exact original SHA-256 `0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849`, version heading dated 2024-10-09. PDF page **51** references the average-of-two-best DLCO maneuver rule while the SAP contains an all-acceptable-efforts method on page 12; page **70** references multiplicity-related alpha splitting.
- **R56** preserves ten review leads, including six explicit method reconciliation items, such as DLCO averaging, testing schematic, adverse reaction terminology, EQ-5D reporting, exploratory hospitalization and oxygen-rest derivation. These are source-authenticated observations, **not confirmed post-unblinding changes**. The SAP's header date predates the current protocol header date; the actual amendment history, first-public availability, sign-off, lock/unblinding clocks and region-specific multiplicity remain unverified.

## Protected interpretation and remaining work

- The primary **p-value 0.0007** and positive reported effect are important evidence, but a nominal positive result does not alone certify a locked prespecified endpoint, family-wise alpha control, trial data integrity, validated clinical benefit–risk, original NDA/BLA CMC readiness or FDA outcome.
- No independent historical FDA prediction backtests, verified prospective model accuracy or approved probability has been established; **0 validated FDA forecasts**. All official FDA outcome and delay predictions remain **ABSTAIN**.
- The remaining scientific task is independent reconciliation of original protocol amendments, SAP approval prior to unblinding, the seven secondary hypotheses against the exact regional hierarchy, original case-level safety denominators, and regulator CMC/inspection findings. The parallel historical FDA cohort must independently verify consecutive filing cycles and original predecision inputs before calibration.
- Development workflow is read-only with exact archival SHA-256 checks, source-time provenance, 25 tests and no clinical ledger, model training, release or production writes. The scheduled daily background workflow remains unavailable on default branch while PR #965 is still draft/unmerged.

Source files: `new-platform/backend/scripts/build_svra_primary_safety_sap_evidence_r57.py`, `tests/test_svra_primary_safety_sap_evidence_r57.py`, `.github/workflows/main-r57-svra-primary-safety-sap-evidence.yml`.
