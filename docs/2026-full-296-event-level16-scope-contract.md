# 2026 full-universe Level 1–6 assessment scope contract

Date: 2026-11-19. User requested **all 296 claimed 2026 PDUFA events** evaluated, not a subset of 89. The number 296 is **user-supplied, not yet independently verified**. A PDUFA review event is an application/review-cycle/indication event; it is not interchangeable with a clinical trial. Some events rely on multiple trials, and some are supplements.

## Non-negotiable target
- Build a canonical, deduplicated 2026 PDUFA event manifest. Preserve original applications, efficacy supplements, CBER applications, CRLs, resubmissions and amended dates as distinct where their review cycles genuinely differ. Track source and event eligibility. Do not pad to 296.
- Cover every verified eligible event with L01, L02, L03, L04, L05 and L06: 296 × 6 = 1,776 *only if* 296 distinct events are verified.
- Link every event to its pivotal trial(s), pre-cutoff publications, trial registry versions, sponsor disclosures and material regulatory/CMC evidence. Record `NOT_AVAILABLE` vs `NOT_RETRIEVED` vs `NOT_APPLICABLE` distinctly.
- Require a documented historical cutoff and publication dates. Current trial registry snapshots cannot prove historical availability.
- Require an independently outcome-unexposed reviewer and immutable timestamped prediction lock before opening outcome-only evidence. Observed/potential exposure cannot be counted as genuinely blind.
- Preserve abstentions; report prediction coverage, eligible denominator, accuracy and calibration separately. Never infer accuracy from narrative assessments.
- **Do not merge or deploy** without explicit authorization.

## Verified repository starting point
- 89 provisional candidate rows tracked in the clinical evidence backlog.
- 30 candidates represented in provisional source research ledger; 59 tracked candidates without entries there.
- 22 candidates have preliminary L01–L06 narrative reviews, **not** locked blind predictions.
- 0 independently validated locked directional blind predictions.
- 296 claimed annual events: **not reconciled to a canonical source**.
- No basis to claim 207 distinct verified missing events: `296 - 89 = 207` is an arithmetic gap only until event identity/deduplication is validated.

## External coverage caution
FDA does not publish a complete forward-looking PDUFA calendar. Sponsor-disclosed goal dates, Drugs@FDA, CBER and other source datasets use different event definitions. For example, pdufa.bio's 2026 calendar currently lists 107 dates for June–December, which **cannot** verify or disprove a 296-event full-year count by itself. https://www.pdufa.bio/calendar

## Completion acceptance criteria
1. Canonical full-year event IDs and evidence-backed event definitions; every included/excluded event justified.
2. Six scientifically reviewed levels per eligible event with dated sources and explicit unknowns.
3. Independent outcome-exposure checks and signed/immutable prediction locks; abstentions preserved.
4. Separate outcome reconciliation and reproducible accuracy calculations on genuinely blind cases.
5. Automated audit passes and human reviewer verifies material evidence.
6. Clearly report events lacking public scientific data separately from events not yet researched.

This document records scope and acceptance criteria. It **does not** claim the remaining reviews or blind backtest are complete.
