# PDUFA Prediction — Missing Evidence & Decision Requirements (verbatim UI contract)

Display immediately below MAIN prediction for each NCT/application. Default collapsed under a caret: "▼ MISSING EVIDENCE & DECISION REQUIREMENTS (N critical · N high · N medium)". Expand to show every item. Highlight CRITICAL red, HIGH amber, MEDIUM yellow. Do not mark a source "missing" merely because it is not public; distinguish NOT_FOUND, NOT_PUBLIC, NOT_YET_PUBLISHED, PENDING_REVIEW, CONFLICTING, and VERIFIED.

## MAIN summary fields
- Predicted decision: PASS / CRL / EXTENSION / ABSTAIN
- Prediction confidence: measured, calibrated probability if available; otherwise "Not established"
- Evidence completeness: verified required items / total applicable required items; no invented percentages
- Decision readiness: READY / RELUCTANT / NOT READY
- Missing critical items: count
- Missing high-priority items: count
- Missing medium-priority items: count

## Per-item expandable card — exact labels
**Missing:** [specific document, result, or data field]
**Evidence sought:** [original source, document title, date, URL when available]
**Why required:** [specific scientific or regulatory question]
**Decision impact:** [PASS/CRL/EXTENSION probabilities affected, or blocks a reliable prediction]
**Current status:** [NOT_FOUND / NOT_PUBLIC / NOT_YET_PUBLISHED / PENDING_REVIEW / CONFLICTING]
**Next action:** [specific source or verification step]
**Last checked:** [timestamp]
**As-of date:** [prediction cutoff; exclude all evidence published later]

## Example (illustrative only; never label as actual finding)
🔴 CRITICAL — Primary Endpoint Results Missing

The system has not verified the primary efficacy endpoint results from the pivotal Phase 3 clinical trial. Without these results, it cannot independently establish whether the trial met its prespecified primary objective.

**Decision impact:** Critical evidence gap. The system must not present a high-confidence approval prediction based solely on secondary findings.

**Required action:** Retrieve and verify the primary endpoint results, statistical significance, effect size, and associated trial documentation.

## Decision rules
1. A critical missing item can force ABSTAIN/NOT READY under defined readiness rules; never imply the model can know confidential FDA inspection or review material.
2. List missing evidence by smallest subordinate assessment first, then roll up to SCIENCE, OUTCOME, and MAIN.
3. Show a spinner only while that item is actively being retrieved, and update items sequentially as verified.
4. For historical backtesting, use only evidence available at the as-of prediction date; lock predictions before outcome comparison.
5. Do not treat illustrative examples as actual trial data. Never synthesize documents, percentages, or verification statuses.
6. Preserve all Pipeline, GEM JR, GEM, WT filters and existing FS/FA preset associations.
7. Add regression tests for missing/not-public distinction, severity highlights, caret expansion, readiness gating, as-of cutoff, and sequential updates.
