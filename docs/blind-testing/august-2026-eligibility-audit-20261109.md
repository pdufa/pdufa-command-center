# August 2026 PDUFA: strict blind-accuracy eligibility checkpoint

Prepared 2026-11-09, after August 2026 outcomes were publicly disclosed. **This is an audit status, not a result or forecast**.

## User-mandated method

The user's requirement is to assess each target using only evidence available before its decision, **freeze a directional or abstain forecast first**, and only afterward look up FDA outcomes. A retrospective statement of what the assessor would have predicted, written after observing the FDA decision, does **not** qualify as a genuinely blind forecast.

## What was checked

- GitHub repository historical commit query through 2026-07-31T23:59:59Z did not return an accessible pre-August commit snapshot.
- Connected Google Drive metadata search for PDUFA/FDA-named files created before August 1 returned no matching forecast artifact.
- The present-day published 2026 August calendar has outcomes already attached to the case rows; opening the calendar exposed information the assessor needed to remain ignorant of. **Outcome blinding therefore failed before any new August 2026 prediction freeze.**
- The public August event aggregators disagree on August 2026 target-date cohort membership and exact application identities; 11 current listed rows in each of two separately curated calendars are not proof of an identical, historically pre-registered cohort. Two calendars include events with different listed names and sources.
- No dated, cryptographically or revision-history authenticated August **predecision individual prediction** was established during this checkpoint. If an existing source predated the case decision, it may be recovered later and verified **without backdating or replacing it**.

## Current August blind accuracy

`verified_original_predicted_before_decision=0`; `verified_scored_blind_decisions=0`; `validated_blind_accuracy=null`; `reconstructed_august_2026_leans=NOT_AUTHORIZED_AS_BLIND`.

**No 0% score is claimed**: the result is **NOT MEASURABLE**, not zero correct out of zero. Current November outcome-aware research must not be promoted to a past August blind result.

## Required controls for future real blind tests

1. Predefine a prospective PDUFA goal-date roster based on public notices as of a frozen UTC cutoff, with exact sponsor, application, indication, goal and source publication timestamp. Do not select the cohort from an FDA decisions list.
2. Lock a versioned assessment rubric/model (phase-first efficacy, safety, statistics, CMC/regulatory cycle, counterevidence, probability or ABSTAIN rules) **before any case outcome**. Do not tune it using test-month labels.
3. Record one immutable dated forecast for every eligible application and a disposition for evidence-insufficient cases; retain SHA/commit, signer/session provenance, exact source timestamps and code/config version.
4. Store outcome-free prediction artifact in a write-protected namespace. Make FDA decision fetching an explicit separate subsequent step following a successful durable freeze.
5. Independently verify exact application/action and outcome with FDA primary letters or authoritative records. Record approval, CRL, withdrawal, pending, date-moved and no-decision separately. Do not turn withdrawals or missing labels into simple directional matches/misses.
6. Compute scored coverage, abstention rate, confusion matrix, sensitivity/specificity when applicable, Brier/log loss only for precommitted probabilities, balanced comparison to an always-approval baseline, date-specific confidence intervals, and out-of-sample calibration. Preserve abstentions and unknowns.
7. Preserve original frozen forecasts unchanged. Record later insights as separately timestamped superseding research; never overwrite the scored prediction.
8. Do not describe simulated retrospective **outcome-hidden** or after-the-fact reconstructed Level 3 assessments as genuinely prospective blind accuracy.

For 2026-08 in particular, only pre-existing forecasts verifiably sealed **before the relevant August FDA action** could enter a true blind accuracy denominator. The appropriate forward-looking application is to future still-unresolved PDUFAs, with real predecision freezes created now and results read afterward.

**No production predictions, live accuracy tables, active scans, FOCUS/POOL membership, trading decisions, scheduled automations, or historical September/October research changed by this document.**
