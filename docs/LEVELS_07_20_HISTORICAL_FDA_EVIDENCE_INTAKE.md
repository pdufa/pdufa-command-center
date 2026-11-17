# Historical FDA evidence intake — Levels 7–20 (isolated)

Status: **collection specification only; no real trial data ingested or evaluated**.

## Historical event identity
Each record must be keyed by the complete `(nct_id, application_id, indication)` tuple. A company/ticker is not an event identifier. Multiple indications or submissions require distinct records. Record decision dates from independently verified FDA documents, but **do not expose outcomes to the blind feature or prediction package**.

## Source hierarchy
1. FDA approval letters, complete response letters where publicly available, FDA review packages, advisory committee materials, and FDA regulatory history.
2. ClinicalTrials.gov study record and historical versions; NCT linkage, endpoints, enrollment, and study dates.
3. Sponsor SEC filings and dated press releases; label sponsor assertions separately from regulatory confirmation.
4. Peer-reviewed manuscripts and conference abstracts with publication and retrieval dates.
5. Secondary news only as discovery pointers, never a replacement for primary evidence.

## Per-event required fields
- `nct_id`, `application_id`, `indication`
- `frozen_on`, `cutoff_on`, `decision_on` (ISO dates, `frozen_on < cutoff_on < decision_on`)
- `snapshot_artifact_id`, `snapshot_sha256` (actual frozen bytes must match)
- Source URL, source class, source publication date, retrieval date, source SHA-256, and linkage to NCT/application/indication
- A documented source-access limitation for any missing primary document
- A clearly specified cutoff policy that prevents later evidence entering earlier snapshots

## Prediction record (separate blind ledger)
Each prediction must match event identity, dates, and snapshot SHA-256; include level (7–20), `predicted_on`, `prediction_sha256`, `prediction` (`APPROVE`, `NOT_APPROVE`, `ABSTAIN`), and `scientific_status`. Non-abstention is prohibited until separately verified scientific scoring exists. Never infer approval from the presence of a later FDA label.

## Outcome quarantine
Keep adjudicated FDA outcomes in an independently controlled, non-blind dataset. Do not include `fda_outcome`, `actual_decision`, `approval_status`, `outcome_label`, `fda_decision`, `decision_result`, or `approval_date` in blind features, even in nested metadata. Freeze and hash predictions before independent unblinding. No accuracy statistics until independent outcome adjudication and pre-registered evaluation.

## Gate order
1. Establish eligible cohort and temporal cutoff policy.
2. Collect and verify original dated primary sources.
3. Freeze evidence bytes and manifest; verify SHA-256 against actual bytes.
4. Validate point-in-time evidence and historical linkage.
5. Validate prediction ledger, blind join, and frozen package integrity.
6. Independently review scientific evidence and methodology.
7. Lock predictions; only then unblind independently adjudicated outcomes.
8. Calculate pre-registered accuracy/calibration with uncertainty and missingness.

## Current state and blockers
- Gate software is implemented and isolated; CI passing on last verified commit.
- No historical FDA evidence corpus has been populated by this specification.
- No blind historical predictions, accuracy, calibration, or scientific verification have been produced.
- No production activation, merge, or deployment is authorized.
