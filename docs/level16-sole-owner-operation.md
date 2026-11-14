# Sole-owner Levels 1–20 assessment operation — owner directive 2026-11-13

**Active policy: one owner, zero external verification requirements, at every Level 1–20.**
This **replaces** all previously drafted mandatory independent source attestations,
five-person clinical review panels, outside statistical/medical qualifications,
challengers, external regulatory signoffs and independent final adjudication.
Do not install, bill for, schedule or require those roles for the owner's
POOL/FOCUS/deep-medical-intelligence assessments.

The owner directs the assessments. AI/software can collect original publicly
available scientific evidence, perform phase-appropriate tests, produce
provisional scores and model predictions when supported, expose contradictions
and missing information, and keep immutable version histories. **Only the
owner** checks, accepts, rejects, annotates and decides whether to publish the
assessment. An outside service may host the software or publish an original
clinical paper, but that is not a third-party human assessment or signoff.

## Authoritative configuration

- `AGENTS.md` current owner directive at the top overrides older
  "independent" and five-person instructions elsewhere in that file.
- `infra/assessment/sole-owner-levels1-20.json` describes the one-owner
  review policy for each of the 20 levels, including a mandatory **zero**
  for all types of external verification/signoff and a declaration that
  Levels 7–20 are **not** yet fully implemented.
- `scripts/medical/level1_20_owner_policy.py` validates that policy and
  returns exact owner-only requirements for any level 1–20.
- `infra/level16-staging/sole-owner-intent.json` records one human
  operator with no outside reviewer accounts, no shared human credentials,
  and no outside-review track active.
- `scripts/medical/level16_sole_owner_work_queue.py` produces the
  current 32-FOCUS-trial / 192-preliminary-worksheet owner-only queue.
  Each task has `externalVerificationRequired=false`,
  `outsideReviewerCountRequired=0`, and
  `ownerCheckCanProceedWithoutIndependentSignoff=true`.
  Its owner check status starts **OWNER_NOT_REVIEWED**, not certified.

The formerly proposed independent-medicine schema, source-attestation
signers, five-person event workflow and A01–A14 **external-review**
approval package are **legacy, inactive engineering**, not requirements
for owner-assessment readiness or scientific scoring. They are retained
solely for history and to avoid forging past reviews. Do not activate or
reuse them unless the owner gives a new explicit directive. The current
owner-only assessment path must never import or call that legacy
multi-person adjudication workflow. Its old status labels do not limit
self-assessments or pretend to certify them.

## Owner-only workflow

1. The engine collects and organizes phase-appropriate original sources,
   including indication, registry status, source citation/date, protocol/SAP,
   reported endpoint definitions, efficacy, safety and regulatory context.
   Missing files are labeled missing, unconfirmed or not yet expected at
   that phase, never invented.
2. AI automatically runs available internal evidence consistency and
   scientific checks for each level. It can expose risks, uncertainties,
   calculations and reasons for proposed scores. The assessment's
   owner-review status remains separate from automated analysis.
3. The owner may inspect the source material personally, correct
   classifications, record reasons and mark the result as
   `OWNER_ACCEPTED_WITH_LIMITATIONS`, `OWNER_NEEDS_EVIDENCE`,
   `OWNER_REJECTED` or not applicable. No external person participates.
4. Revised original sources or a later phase trigger versioned
   reanalysis. Retain old assessments and cutoff timestamps. When
   a new result is outcome-exposed, never describe it as a genuinely
   blind historical prediction.
5. Predictions are clearly presented as estimates made by this
   owner-controlled research model, with evidence cutoff, risks,
   uncertainty and calibration limitations. Do not guarantee 100%
   approval accuracy or claim FDA/independent professional certification.

**For Levels 7–20:** the same no-external-gate policy applies now.
This policy is not evidence that these engineering levels have been
installed, implemented, executed or validated.

## What still needs setup (NOT outside verification)

- The owner may need to select and secure one authenticated account
  (MFA, recovery and permissions) before private site access.
- Choose and authorize a concrete deployment destination, budget,
  backups and security checks before any production release.
- Fill genuine data gaps, complete source collection and run owner
  review; the initial 32 FOCUS trial packets do **not** mean 32
  human-reviewed trial assessments. Scientific uncertainty must stay
  visible.
- Calibration and performance testing can be undertaken internally
  by keeping predecision forecasts frozen and comparing them later
  with observed actions. No outside evaluator is required.
- Existing production merges, live site activation and payments
  remain separately controlled, and this document is **not**
  permission for them.

## Inspect locally without running outside-review services

```powershell
python scripts/medical/level1_20_owner_policy.py
python scripts/medical/level1_20_owner_policy.py --level 20
python scripts/medical/level16_sole_owner_work_queue.py --nct NCT04576949
python -m unittest discover -s tests -p "test_level1_20_owner_policy.py" -v
python -m unittest discover -s tests -p "test_level16_sole_owner_work_queue.py" -v
```

These checks require **no external verification approval**. They also do
not create fake owner review records or turn unfinished source research
into independently validated science.
