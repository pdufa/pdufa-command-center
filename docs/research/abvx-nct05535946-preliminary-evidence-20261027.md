# ABVX / NCT05535946 — preliminary source-review worksheet (2026-10-27)

**Research only.** This worksheet is not a reviewed DECISION manifest, validated scientific dossier, GEM JR ranking, prediction, or authorization to trade. Do not load it into the production evidence directory. Original records and protocol/SAP are not yet independently reconciled.

## Identity and trial design

- Sponsor/company: Abivax S.A. (ABVX); SEC CIK 0001956827 according to the frozen 2026-10-26 Phase 3 census.
- Trial: NCT05535946, ABX464-107 / ABTECT-Maintenance; Phase 3; obefazimod (ABX464) 25 mg or 50 mg once daily vs placebo; moderately-to-severely active ulcerative colitis.
- This maintenance trial follows induction trials ABX464-105 and ABX464-106. The trial includes a 44-week double-blind maintenance period followed by a long-term extension. The 580-subject efficacy/safety summary below concerns the randomized maintenance population, **not** the complete longer-term study population.
- Source for design: https://clinicaltrials.gov/study/NCT05535946 ; corroborating registry mirror https://clinicaltrials.ucsd.edu/trial/NCT05535946

## Company-reported efficacy (June 1–2, 2026; NOT independently adjudicated)

The June 2026 company release and 6-K report Week 44 clinical remission: placebo 20/192 (10.4%), 25 mg 98/193 (50.8%), 50 mg 100/195 (51.3%); both active groups p<0.0001 vs placebo. Company-reported secondary measures include endoscopic improvement (12.5%, 54.9%, 64.1%) and endoscopic remission (9.9%, 41.5%, 47.7%) for placebo/25 mg/50 mg respectively. Denominators, estimands, handling of missing data, multiplicity control and prespecified analysis populations must be checked against the original protocol/SAP and registry results before scientific acceptance.

Source: https://www.globenewswire.com/news-release/2026/06/01/3304711/0/en/abivax-announces-landmark-phase-3-abtect-maintenance-trial-results-evaluating-obefazimod-in-moderately-to-severely-active-ulcerative-colitis.html

## Company-reported safety (June 2, 2026 Form 6-K; NOT independently adjudicated)

| Event | Placebo N=192 | 25 mg N=193 | 50 mg N=195 |
| --- | ---: | ---: | ---: |
| Any treatment-emergent adverse event | 96 (50.0%) | 112 (58.0%) | 140 (71.8%) |
| Discontinuation due to TEAE | 13 (6.8%) | 5 (2.6%) | 9 (4.6%) |
| Serious TEAE | 8 (4.2%) | 5 (2.6%) | 11 (5.6%) |
| Death | 0 | 0 | 0 |

The higher overall TEAE rate at 50 mg requires analysis, even though the sponsor describes no new safety signal. The filing also reports malignancies and infections requiring event-level and exposure-adjusted review. These data cannot support a claim of FDA-confirmed safety.

Original issuer-hosted Form 6-K PDF: https://abivax.gcs-web.com/static-files/5e3fe706-25e7-499a-ac3e-78af1274a14b

## Critical outstanding evidence gates

1. Obtain the **exact ABX464-107** registry results, version history, original protocol and statistical analysis plan; do not confuse with the separate ABX464-105/106 induction trial documents.
2. Reconcile primary endpoint definition, randomized/analysis populations, missing data, multiplicity, prespecified estimands, and all subgroup results.
3. Review complete adverse-event tables, exposure, discontinuations, infections, malignancies, and long-term follow-up; distinguish sponsor interpretation from independent assessment.
4. Verify drug/indication/trial ↔ any FDA NDA/application number, review cycle and regulatory status. A planned Q4 2026 NDA is **not** a confirmed filing, accepted application, or PDUFA date.
5. Verify issuer/company mapping, dated financing/runway and exact-program market evidence separately.
6. Complete all 20 scientific levels, 40 assessments, eight subject layers, original-source chronology and independent reviewer attestations. None are certified complete by this worksheet.
7. Confirm actual GEM JR membership/rank separately; frozen Pipeline census inclusion does not imply GEM JR membership.

**Decision state:** NOT_READY. `modelValidated=false`; `probability=null`; `tradeAuthorized=false`. This worksheet is preliminary evidence triage, not an approved reviewed-evidence payload.


## Registry-document discovery (27 October 2026)

An independent registry-index search surfaced the following **document metadata**, which should now be verified against the actual ClinicalTrials.gov document files before asserting that their contents were reviewed:

- Protocol **dated 10 April 2024**, reportedly posted **14 August 2026**.
- Statistical analysis plan **dated 15 July 2025**, reportedly posted **14 August 2026**.
- Results reportedly submitted **3 July 2026** and first posted **10 September 2026**.
- Registry-index population: **636 started, 578 completed, 19 with serious adverse events**. These figures are not interchangeable with the sponsor's **580-person randomized maintenance efficacy/safety analysis**. Differences in enrolled/started/randomized/completed populations, analysis periods and definitions require direct participant-flow and adverse-event-table reconciliation.

Discovery reference: https://ctis.eu/trial/2022-500536-11-01 (third-party index of ClinicalTrials.gov record); authoritative record and version history: https://clinicaltrials.gov/study/NCT05535946 and https://clinicaltrials.gov/study/NCT05535946?tab=history

**Chronology:** The document dates precede the June 2026 topline disclosure, but their public posting dates appear to be after it. A document's internal date alone does not prove public availability at an earlier historical prediction cutoff. The first public availability and actual version/contents must be independently verified before use in point-in-time model validation.

**Unresolved:** Original protocol and SAP bytes have not been downloaded/read in this review. No claims about exact prespecified estimands, multiplicity, imputation, or primary population are yet validated. The registry's aggregate serious-adverse-event count must not be compared directly with the sponsor's arm-level serious TEAE counts until matching populations and periods are established.

**No readiness promotion:** NOT_READY; modelValidated=false; probability=null; tradeAuthorized=false.

## CORRECTION — registry identity mismatch discovered 2026-10-27

**Critical: the EU CTIS index at https://ctis.eu/trial/2022-500536-11-01 explicitly cross-references NCT05507216 (ABTECT-2 induction), NOT NCT05535946 (ABTECT maintenance).** The previous "Registry-document discovery" section inadvertently attributed that index's 636 started / 578 completed / 19 serious-AE and protocol/SAP posting dates to the maintenance trial. **Those figures and dates must be withdrawn from the NCT05535946 evidence inventory and must not be used in its readiness assessment.** They refer to a distinct trial. The 580 maintenance analysis population from the sponsor's June 2026 announcement remains a separate sponsor-reported figure and has not been reconciled against the authoritative maintenance registry record.

Authoritative identity check required: https://clinicaltrials.gov/study/NCT05535946 ; study ID ABX464-107. The registry API could not be accessed in this environment; original maintenance protocol, SAP, participant flow, and results are **NOT YET RETRIEVED**. No conclusions about their dates or counts are justified. Preserve both sections above as a transparent audit trail, but treat the incorrect index attribution as **RETRACTED**. The unrelated induction CTIS index is only an example of the cross-study contamination hazard.

**Disposition:** BLOCKED_SOURCE_IDENTITY / NOT_READY; modelValidated=false; probability=null; tradeAuthorized=false. A source must match exact NCT ID and sponsor protocol ID before any numeric result or document date is attached to a trial dossier.
