# Historical FDA decision evidence: adjudication contract (research only)

## Purpose
Produce an independently reviewable record of **one FDA action per application/submission/review cycle**. Do not treat a PDUFA target date, trial outcome, press release, URL, or manually set `verified=true` as an authenticated FDA decision. Until documentary adjudication and cohort coverage are independently checked, all records remain **candidate observations** and cannot train or validate PASS/FAIL models.

## Required fields per candidate
- `application_id`: normalized NDA/BLA/ANDA identifier; `submission_id`: exact original or supplement identifier; `review_cycle`: positive integer; `action_date`: date of actual FDA action.
- `action_type`: APPROVAL, COMPLETE_RESPONSE, or OTHER/UNRESOLVED. A Complete Response Letter (CRL) is a **nonapproval at that review cycle**, not a permanent product failure.
- `official_source_url`, `document_title`, `retrieved_at`, `source_published_at` (when available), `document_sha256` (only when bytes actually retrieved), and `evidence_locator` (page/section).
- `source_observation`: what the document explicitly states, with exact application, submission, cycle, and action date reconciled.
- `adjudication_status`: UNREVIEWED, CONFLICT, DOCUMENT_VERIFIED, or INDEPENDENTLY_ADJUDICATED. The last status requires separate review of original evidence and identity/cycle mapping, with reviewer, timestamp, and evidence trail.
- `predecision_evidence_cutoff`: timestamp before the FDA action. Model inputs must have availability dates at or before this cutoff. Never retroactively use the final decision, later FDA reviews, postdecision publications, or corrected historical records as model inputs.

## Source and denominator discipline
1. Start with official FDA action documents, approval letters, review files, and publicly accessible FDA records. Preserve source-document hashes and provenance; links alone are not verification.
2. Reconcile NDA/BLA, submission number, review cycle, indication, sponsor, and action date; flag discrepancies instead of silently joining.
3. Build an explicit cohort inclusion/exclusion ledger. Approval-only datasets **cannot** establish the PASS/FAIL denominator. Missing or undisclosed CRLs are a selection-bias risk.
4. Separate original CRL and subsequent resubmission approval into distinct dated review cycles. Track withdrawals, extensions, advisory committee votes, and unresolved actions separately, not as fabricated FAIL labels.
5. Deduplicate review cycles and group related submissions/applications when splitting train/test to avoid contamination. Use time-forward evaluation with frozen predictions.
6. Keep source accessibility, document verification, independent adjudication, model eligibility, and trading readiness as **different fields**. No synthetic tests or GitHub checks can set the last three automatically.

## Minimum acceptance criteria before model claims
- Reproducible count of independently adjudicated PASS and FAIL review cycles with a documented denominator and missingness audit.
- Time-stamped, frozen predecision predictions; independently audited absence of future information.
- Time-forward holdout performance, calibration, uncertainty intervals, comparisons with prior approval-rate baseline, and clinically relevant subgroup checks.
- Prospective paper-trading evaluation that also measures market expectations, slippage, liquidity, and downside risk before live-trading consideration.

**Current position:** Historical evidence verification and independent predictive performance are unestablished. Research documentation only; no deployment, trading authorization, or claims of accuracy.
