# MAIN Revision 81 — full FOCUS 29-trial / 23-application source-readiness scale-up

**Research date:** November 9, 2026 Pacific. **Base:** existing [draft medical Stage-4 PR #965](https://github.com/pdufa/pdufa-command-center/pull/965). **Source identity:** immutable FOCUS 29 exact NCT source records; 23 **provisional** application-cycle group IDs. No changes to existing spreadsheets or production.

## Why this is different from prior Launch-HTN-specific research

Revisions 71–80 established detailed **source-only** research for five exact phase-3 publication candidates and in-depth original publisher supplement/chronology work for one of them (Launch-HTN, NCT06153693). The remainder of the FOCUS roster still needs phase-appropriate original-source authentication and independent scientific adjudication. This revision makes the evidence-readiness stage visible for **every trial**, with application-cycle linkage, instead of letting one deep source case be mistaken for completion across 29.

## Verified machine-source and publication intake scope

The implementation computes from the already independently validated R68 FOCUS source-recovery board (derived from the R60/R64/R65/R67 original source chain), the five original main-report cases validated by R71, and R79's exact-NCT prospective-authenticity gate. All input IDs and source-availability flags are tied back to the canonical R68 dataset, and each NCT is cross-linked to every provisional application-cycle ID. It does not use retired surveys or scoring.

| Source metric | Scope | Interpretation |
| --- | --- | --- |
| Exact FOCUS NCTs | **29/29** identities in display | Membership map, not 29 scientific conclusions |
| Provisional application cycles | **23/23** groups | Each may link to one or several NCTs; not certified individual FDA filings |
| Current original retained registry primary tables | **12/29** | Presence of posted table in retained source, not independent statistical replication |
| Current retained registry arm-specific safety data | **12/29** | Presence only, no causality or benefit-risk review |
| Current retained protocol/SAP machine-indexed page leads | **12/29** | PDF pointers only, not authenticated pre-unblinding locks |
| Original published pivotal main-report leads fully identified by R71 | **5/29** | Source evidence leads, not verified original locked SAP or qualified benefit-risk |
| NCTs not indexed as one of five R71 pivotal cases | **24/29** | Not in this *five-case intake*; not a claim that no original paper exists |
| Launch-HTN original publisher method PDF pages studied | **1 NCT** | R77 published H1–H7, missingness and safety source mapping; not replicated/signoff |
| Full 8-domain source-science review slots for all 29 | **232** | All 232 remain unassessed scientifically |
| Independently authenticated prospective signed SAPs | **0** | Source provenance not complete; not evidence sponsor lacked a plan |
| Independent qualified scientific reviewer signoffs | **0** | No completed medical adjudication |
| Validated FDA application predictions | **0/23** | FDA forecast ABSTAIN, timing UNKNOWN; no accuracy calibration |

**Interpretation discipline:** absence of a posted table from the retained registry source or absence of a publication from R71's small subset is **not evidence of trial failure, lack of publications, or negative regulatory outcome**. Conversely, positive author-reported effect estimates are not signed science or regulator decisions.

## Installed sources, frontend and tests

- `new-platform/frontend/lib/focus-r81-all-focus-source-readiness.ts` builds an exact-NCT research-only census, ensuring all 29 NCTs, all 23 cycle groups and all five cited R71 leads are preserved; fail closed if forged NCT/ticker/cycle IDs, changed source flags or claimed new grades appear.
- `new-platform/frontend/app/predictions/evidence-gaps/FocusSourceReadinessR81.tsx` renders a read-only source readiness summary and **23 expandable cycle cards** with exact NCT links and source-intake status. Integrated above the filters on the existing R68 evidence-recovery board without changing any historical source field or trial list. Responsive source coverage CSS in `EvidenceRecoveryBoardR68.module.css`.
- `new-platform/frontend/tests/focus-r81-all-source-readiness.test.cjs` checks precise 29/23 roster and application links against both frozen original backend snapshots (including multi-linked NCTs), all 12/29 source availability distinctions and five/24 publication leads, no false signoff, and adversarial attacks.
- `.github/workflows/main-r81-full-focus-source-coverage.yml` runs exact source roster blob hash locks, the permanent retirement guard, R81 tests, TypeScript and Next build.
- Original R71 Chromium workflow adds both **desktop 1365px and mobile 390px** UI acceptance for the 23 cycle cards, original linked NCTs, and visible ABSTAIN/no-grade disclosures.

## Stage-4 remaining scientific work

1. Acquire and authenticate the historical original signed protocols and SAP version chains for each relevant application, source-controlled final database lock and actual unblinding audit records. R80 offline owner-pinned cryptographic intake is ready but has **no actual approved source bytes, attestation keys or signoffs**.
2. Independently re-run clinically/materially important pivotal primary and all critical secondary estimands, missing-data/multiplicity and exposures from acceptable source data and the original locked version; do not over-assess incomplete phases.
3. Obtain qualified independent statistical and medical signoff for each of 23 application-cycle dossiers with complete trial-to-application attribution and FDA regulatory/CMC evidence, including independent negative-case challenges.
4. Run **truly pre-outcome-blind** historical backtests before publishing any calibrated accuracy rating. Outcome-aware retrospective chart matching is not a valid prospective backtest.
5. Preserve original audits, decisions, and independent overrides; release approval/CRL and timing judgment only when evidence and calibrated model thresholds justify it. No unsupported '100%' prediction is possible.

**Current source-only result:** 29/23 identifiers mapped, 5 R71 main-report leads, 1 detailed published-method case; **0 original signed prospective SAPs authenticated, 0 independent science signoffs, 0 FDA forecasts validated, 0 genuine prospective-blind backtests, ABSTAIN/UNKNOWN, accuracy unavailable.** No production/model-training writes, no retired system resurrection.
