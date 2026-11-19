# 2026 Level 1 historical reconstruction — preregistered decision rule v0.1

**Purpose:** Apply one consistent, outcome-independent Level 1 rule to historical packets using only evidence demonstrably public by each packet's cutoff. This is a **retrospective simulation**, never a genuine prospective prediction. This rubric is frozen for the first evaluation batch; changing it after inspecting any held-out outcomes requires a new version and separate reporting.

## Embargo and eligibility

The scorer receives only the sanitized packet, contemporaneous publication dates, content hashes, and application identity. The scorer must not receive the outcome, FDA action date, post-decision FDA correspondence, outcome-aware assessments, or the original reconciled assessments CSV. A reviewer with prior knowledge of a specific outcome is **not blind** for that case; an isolated evaluator without outcome access is required. A valid packet must have verified pre-cutoff dates, immutable source hashes, trial-to-application crosswalk, and enough evidence to assess efficacy, safety, and regulatory readiness. Otherwise output **ABSTAIN**, not an assumed approval or denial.

## Fixed evidence checklist (no hindsight weights)

Record each domain as SUPPORTIVE, CONCERN, or UNKNOWN, with contemporaneous evidence citations:

1. **Efficacy:** prespecified endpoint met with interpretable effect size and uncertainty; single-arm evidence must state whether the proposed external benchmark is independently justified.
2. **Trial integrity:** protocol and analysis plan available; major deviations, missing data, multiplicity, or population inconsistencies identified.
3. **Safety:** adverse events, serious events, withdrawals and exposure adequate for indication; attribution and disease background distinguished.
4. **Regulatory pathway:** application type, resubmission status, priority review, inspection and manufacturing risks from pre-cutoff sources. Designations and acceptance for review are **not** approval evidence.
5. **Evidence sufficiency:** at least one primary clinical source and one primary regulatory/application source, each dated and hashed before cutoff.

## Deterministic qualitative classification

- **APPROVAL_LEAN** only when efficacy and trial integrity are SUPPORTIVE, safety is not CONCERN, regulatory pathway is not CONCERN, and all five domains are known with cited evidence.
- **NONAPPROVAL_LEAN** when at least one **documented, material, unresolved** pre-cutoff concern in efficacy, trial integrity, safety, or regulatory pathway exists. The concern must be independently documented; an unknown field alone does not qualify.
- **ABSTAIN** otherwise, including missing pivotal statistics, absent pre-cutoff inspection data when relevant, or an unresolved ambiguity that prevents distinguishing the first two classes.

**No numeric confidence percentage** is authorized by this rubric. Calibration requires a separate untouched validation set. Historical accuracy denominator includes only independently scored eligible packets and must report abstentions separately. No score is generated in this file.

## Output and audit trail

Store the sanitized packet SHA-256, rubric version, evaluator identity or isolation method, evaluation timestamp, qualitative prediction, supporting contemporaneous sources and per-domain findings **before** a separate outcome-unblinding step. Outcome comparisons and error analysis must live in a different file or process. Do not revise frozen predictions after comparison. Report the share eligible, abstention rate, accuracy among scored cases, and coverage of all verified cycles separately.

**Current checkpoint:** 71 verified review cycles; 2 partial historical evidence packets; 0 eligible frozen historical predictions; accuracy N/A. Do not convert the 69 outcome-aware records into blind predictions.
