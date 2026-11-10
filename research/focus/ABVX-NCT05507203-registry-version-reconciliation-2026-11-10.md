# ABVX / NCT05507203 — registry version discrepancy and document retrieval queue

Prepared 2026-11-10. **NOT_ADJUDICATED; no independently verified scientific category; no FDA probability.**

## Conflict discovered during public-source lookup
- ClinicalTrials.gov indexed results page: https://clinicaltrials.gov/study/NCT05507203?tab=results — a search index snapshot labeled last update **2025-10-24** says **No Study Results Posted**.
- A secondary registry mirror (https://spzco.com/biotech/trial/NCT05507203) claims the registry posted results on **2026-09-10** and lists study protocol (2024-04-10) and statistical analysis plan (2025-07-15).
- These are **inconsistent as-of snapshots**, not evidence that the registry currently has or lacks results. Neither claim should be accepted as current without a fresh direct ClinicalTrials.gov API/history retrieval.
- Registry history: https://clinicaltrials.gov/study/NCT05507203?tab=history ; version tracking is required to distinguish pre-readout from post-readout evidence.

## Required resolution before any VERIFIED gate
1. Retrieve https://clinicaltrials.gov/api/v2/studies/NCT05507203 directly, save retrieval timestamp and content hash; if inaccessible, mark `DIRECT_REGISTRY_FETCH_UNAVAILABLE`.
2. Extract `protocolSection.statusModule.studyFirstPostDateStruct`, `protocolSection.statusModule.statusVerifiedDate`, `resultsSection` presence, `documentSection.largeDocumentModule`, `protocolSection.outcomesModule`, and `protocolSection.designModule`. Preserve original field names and raw JSON.
3. Compare the historical registry versions as of induction topline versus the latest; flag endpoint and SAP amendments.
4. Download protocol/SAP from registry source URLs and inspect multiplicity, imputation, estimands, population, and safety analysis.
5. Reconcile primary induction remission counts with Abivax's Form 20-F and any posted registry outcome table; keep maintenance study separate.
6. Have a second reviewer challenge and sign off before any independently adjudicated designation.

## Gate ledger
All eight gates remain `PENDING_INDEPENDENT_REVIEW`. Primary-source version conflict is `OPEN`. Independent reviewer is `UNASSIGNED`. Calibrated FDA probability is `NOT_CALCULATED`.

This note records a source conflict and next evidence actions, **not** a claim that either indexed registry state is current.
