# MAIN R78 — official ClinicalTrials.gov historical registry source-access receipt

**Research observation:** November 9, 2026 Pacific  
**Trial:** NCT06153693 / Mineralys Launch-HTN / MLYS  
**Research objective:** Determine which endpoints were registered before trial completion and before the printed main SAP v3.0 signature imprint dated February 13, 2025, using *historic official* ClinicalTrials.gov version snapshots rather than the potentially updated current record.

## Implemented

The additive source-only probe `new-platform/backend/scripts/verify_r78_launch_htn_official_registry_history.py` accesses only allowlisted original `clinicaltrials.gov` study and history endpoints:

1. Official current record: [ClinicalTrials.gov NCT06153693](https://clinicaltrials.gov/study/NCT06153693) / API v2 `/api/v2/studies/NCT06153693`.
2. Official history index: `/api/int/studies/NCT06153693?history=true`, with a narrowly bounded alternate `/api/int/studies/NCT06153693/history`. These are internal/undocumented web API routes and may change or restrict automated access.
3. Subject to a valid source index, the original version, last version on or before **January 24, 2025**, and last version on or before **February 13, 2025**, each via `/api/int/studies/NCT06153693/history/{version}`. This comparison records exact source version dates, original primary outcome text, SHA-256 over retrieved JSON, and endpoint changes **only when the actual historical source is returned**.

The probe runs with hard-coded exact NCT and original host allowlists, bounded responses, rejected HTML interstitials, source-identity verification, and a never-grade/never-production result object. [Dedicated R78 regression and live-source CI](https://github.com/pdufa/pdufa-command-center/actions/runs/42745873286) returned **SUCCESS** for safe engineering behavior on commit `b137ff8cd42af2cdc771e61ee5f5dc1b296edcb9`.

## Real historical source outcome — **BLOCKED, not verified**

The live official-history check returned:
- **Registry history index versions listed: 0**
- **Historical full protocol versions read: 0**
- **Historical primary-outcome comparison before Feb. 13, 2025: UNKNOWN / null**
- Actual explicit source error: `OFFICIAL_HISTORY_INDEX_NOT_AVAILABLE`
- Research state: `REGISTRY_HISTORY_UNVERIFIED`

This **does not establish that the record had zero amendments**; it means the runner could not obtain trustworthy archived versions using those routes. The source probe was failure-aware, not evidence that historical endpoints never changed. The clinical source-registration/history gate remains **open**.

The separate contemporaneous issuer/SEC and JAMA [R78 public-disclosure timeline](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/frontend/data/focus-r78-launch-htn-public-chronology.json) does establish specific publication events (sponsor's March 10, 2025 public Phase 3 topline report; issuer-reported December 22, 2026 PDUFA goal), but neither it nor a ClinicalTrials.gov registry version proves the precise original confidential SAP approval, database lock or treatment unblinding dates.

## Required original evidence for Step-4 independent expert assessment

- A source-controlled copy of the original signed SAP / protocol amendment chain, signature provenance, change control and authorized effective versions.
- Actual validated clinical database soft/final-lock timestamps, release audit trail and first masked-to-unmasked access approvals.
- Archived official ClinicalTrials.gov historical versions (when legitimately accessible) with original outcomes as publicly posted before the above signing dates, compared with the original SAP text.
- Fully reproducible subject-level H1–H7 analysis, 1,000 multiple-imputation runs, numerical alpha-transfer logic, and safety numerator/denominator reconciliation.
- Independent qualified clinical/statistical expert review and regulatory CMC/label review.

**Scientific status remains:** authenticated pre-unblinding signed plan 0, original PDF byte hashes 0/7, historical registry versions verified 0, independent clinical signoffs 0, outcome-blind historical validations 0, validated FDA application forecasts 0/23. Official approval/CRL forecast **ABSTAIN**, future decision timing **UNKNOWN**, calibrated certainty **unavailable**. No production, training, active FOCUS roster or retired scoring changes.

This note is an evidence-access audit, not a claim that absence of API access negates a trial's validity or drug efficacy.
