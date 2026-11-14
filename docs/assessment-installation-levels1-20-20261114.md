# PDUFA installation continuation — PR #1200

Development only: no merge, deployment, production data modification, list membership
change, trading activation, owner acceptance or validated FDA prediction.

## Collection errors and supported regression repairs

All **34 original collection errors** have individual dispositions in
[`test-collection-error-dispositions-20261114.md`](test-collection-error-dispositions-20261114.md).
The original full trace and machine-readable final per-module counts are retained
under `reports/test-verification/`. Missing supported dependencies are declared in
`requirements-test.txt`, separate from production requirements. `pip check` passes.

The original broad root test scope now completes: **2,255 passed, 0 failed,
195 skipped, 0 errors**, plus 1,092 passing subtests. Of the skips, **153** are
explicit retired cases and **42** are other environment/fixture skips. This is
**not** a claim that 195 skipped cases passed or that legacy applications were
restored. Every retired module/function is retained, named, explained, hash-bound
and printed in the test summary. Supported failures remain failures, demonstrated
by two subprocess tests. The removed survey collector and root Streamlit app were
not recreated. Retirement guards remain executable.

Supported repairs include historical source-cohort pinning, immutable timing test
fixtures, current FOCUS cohort compatibility, a corrected endpoint denominator
assertion, current scheduler-input test fixtures, stale PREFLIGHT schedule metadata,
empty-filter behavior and deterministic SEC/FDA controls test data. Exact source,
identity, chronology, authorization, completeness and no-extra-dispatch assertions
remain. No workflow schedule or automation-enablement flag was changed.

A new read-only PR workflow runs the broad root suite with declared dependencies
and retains per-test executed/skipped dispositions. It has no production credentials
or deployment step. Vercel Git deployment remains disabled for this branch.

## Levels 1–6 integration and evidence

The existing scientific numbering is preserved: identity; design; statistics and
efficacy; safety; indication-specific relevance; regulatory readiness. The older
v2 source-audit runtime uses different level meanings and remains versioned and
separate. It is not silently relabeled as the new scientific engines.

| Level | Implemented / tested integration | Available evidence in retained 32-trial manifest | Scientific status / remaining dependency |
|---|---|---|---|
| 1 | Exact ASCII NCT, saved phase/status, provenance, strict UTC retrieval chronology; local persistence/readback | Registry packets for 32 | INTAKE_ONLY, NOT_VERIFIED; original-source discrepancies and actual review conclusions remain |
| 2 | Five design criteria, protocol/API/PDF identity checks, saved eligibility/enrollment, reviewed-source contract | Protocol/SAP originals across 12; registry design metadata across 32 | NOT_VERIFIED; protocol/amendment adjudication, bias and sample-size rationale |
| 3 | Five efficacy/statistical criteria, gated binary event contrasts; immutable output history | Posted registry results 12; indexed journal records across 15; retrieved public full texts across 10 | NOT_VERIFIED; SAP/estimand, missing-data, multiplicity, population and clinical uncertainty review |
| 4 | Five safety criteria, reviewed binary AE/SAE/discontinuation contrasts | 12 results packets; safety completeness has not been separately established | NOT_VERIFIED; reviewed safety counts, exposure/follow-up and benefit-risk interpretation |
| 5 | Indication-specific criteria and exact-trial indication/population inventory | Indication metadata for 32; unreviewed disease-specific research | NOT_VERIFIED; disease/subtype/setting-specific methods, contemporary care comparators and meaningfulness criteria |
| 6 | Regulatory criteria and phase-aware dossier expectations | Two exact-NCT FDA label leads; zero newly verified application-cycle mappings | NOT_VERIFIED; exact trial–indication–application–review-cycle linkage, agency/CMC/labeling evidence |

The full backend suite includes saved-record execution, exact identity, phase/status,
source verification, cutoff isolation, authorization, immutable append/readback and
version-change regressions. POOL, FOCUS and PAST use the existing authenticated
exact-program loader and retain mismatched/ambiguous identity rejection. All 162
frontend test files pass, including those cohort bindings, historical separation,
and the new scientific evidence displays. Typechecking and the build pass.

The candidate service currently assesses current saved source data. Its scientific
contracts do **not** yet have a unified historical execution API with the old
runtime's point-in-time source freezing. No change here claims production or
scientific historical activation. Supplied review publication/retrieval/verification
and review dates must precede the cutoff. Future, conflicting and wrong-trial
records do not reach new calculations. Outcome-exposed reconstruction remains
ineligible for blind accuracy; no calibrated FDA model is supplied.

## New Level 7 method, then Level 8 method

Implemented and tested Level 7's method and saved-record/UI integration before
adding Level 8's method. Neither whole level is scientifically complete.

### Level 7 — population and subgroup validity

Engine `scientific-population-v1` has five criteria: population definition,
eligibility applicability, baseline balance, subgroup prespecification and
interaction. It requires the verified phase-first contract and the same strict
source/review identity and chronology as Levels 2–6. Collection never creates a
review. Early-phase subgroup results and unavailable precompletion baseline data
are NOT_YET_EXPECTED where appropriate, rather than adverse missing evidence.

The implemented calculation is a ratio of subgroup risk ratios and a nominal
95% Wald interval on the log scale, using reviewed binary-event counts from
explicitly mutually exclusive groups with common endpoint, population and time
window. It rejects invalid/Boolean/oversized counts, duplicate subgroup labels,
overlapping groups, zero-event and degenerate-variance precision claims.
It never treats one significant and one nonsignificant within-group result as
proof of interaction. The interval is unadjusted for multiplicity and conditional
on independent binomial/asymptotic assumptions. It establishes neither
prespecification nor clinical relevance or generalizability.

Acceptance demonstrated: known arithmetic, group-swap reciprocal invariance,
invalid/sparse inputs, strict source identity/cutoff/conflict rejection, early-phase
expectations, exact saved-record integration, append-only versions and rendered
output safeguards. Remaining: actual reviewed source counts/population definitions,
prespecification and multiplicity adjudication, and real-trial scientific review.

### Level 8 — safety and tolerability

Engine `scientific-safety-exposure-v1` separately evaluates ascertainment,
denominators, exposure-adjusted rates, discontinuations and serious-event patterns.
It computes events per 100 person-years or person-months from explicit reviewed
person-time, with a comparative incidence-rate ratio when estimable. A nominal
Poisson log-rate-ratio interval is produced only when the reviewed record explicitly
states that count model. No model assertion means no invented interval.
Single-arm studies can report descriptive rates; zero comparator events produce
an undefined ratio. Zero/NaN/invalid exposure or Boolean event counts are rejected.
Enrollment is never substituted for person-time, and event rates are never labeled
percentages of patients. Pre-recruitment outcome data are NOT_YET_EXPECTED.

Acceptance demonstrated: point-rate/ratio arithmetic, explicit uncertainty gating,
single-arm and zero-event behavior, invalid-exposure rejection, phase-aware
expectations, source/cutoff/conflict rejection, versioned save/readback and UI
rendering. Remaining: actual reviewed exposure/event data, ascertainment/censoring
comparability, count-model justification and clinical safety interpretation.

Both methods cite the Cochrane Handbook chapter on effect measures as a method
reference, not as trial evidence. Outputs preserve source URL, publication and
retrieval dates, verification actor/method/date, reviewer, rationale and excerpt.
They remain NOT_VERIFIED, null scientific score, ABSTAIN. Nominal statistical
intervals are not FDA-model calibration or owner acceptance.

## Levels 1–20 completion table and dependency order

No level is labeled scientifically ACTIVE. Implemented arithmetic or passing tests
alone cannot complete a scientific assessment.

| Level | Purpose | Implementation status | Exact next dependency/action |
|---|---|---|---|
| 1 | Identity, phase/status, provenance | Intake implemented; science NOT_VERIFIED | Review original-source discrepancies and record actual findings |
| 2 | Protocol and design | Evidence contract/inventory; partial | Adjudicate original protocol, amendments, conduct and sample-size rationale |
| 3 | Statistics and efficacy | Binary contrasts; partial | Review SAP/estimand, missingness, multiplicity, uncertainty and actual counts |
| 4 | Safety and benefit-risk | Binary safety contrasts; partial | Review harms, population, exposure, follow-up and clinical interpretation |
| 5 | Indication-specific relevance | Evidence contract; partial | Implement source-grounded disease/setting-specific clinical-meaningfulness methods |
| 6 | Regulatory readiness | Evidence contract; partial | Verify exact application, indication and review-cycle linkage and available dossier sources |
| 7 | Population/subgroup validity | Interaction method, history/UI integrated; partial | Real reviewed subgroup data, population validity and prespecification/multiplicity review |
| 8 | Safety/tolerability | Exposure-rate method, history/UI integrated; partial | Real reviewed event/person-time records and justified ascertainment/count assumptions |
| 9 | Benefit-risk integration | NOT_IMPLEMENTED; dependency blocked | Valid indication-specific benefit/harms interpretation from 3–5/7–8; no arbitrary weighted substitute |
| 10 | Disease/standard-of-care dossier | NOT_IMPLEMENTED | Dated disease/subtype/setting guidelines and comparator dossier; clinical source adjudication |
| 11 | Unmet need/therapeutic context | NOT_IMPLEMENTED | Level 10 plus population-specific disease burden and treatment alternatives |
| 12 | Reproducibility/independent studies | NOT_IMPLEMENTED | Distinct comparable studies, nonduplicate cohorts and prespecified synthesis/heterogeneity method |
| 13 | Application/filing readiness | NOT_IMPLEMENTED | Verified Level 6 application-cycle identity and source-supported filing evidence |
| 14 | FDA pathways/designations | NOT_IMPLEMENTED | Exact indication/application-linked official pathway/designation sources, with cutoff versions |
| 15 | FDA precedent/advisory evidence | NOT_IMPLEMENTED | Comparable, source-reviewed precedent criteria and official advisory/review records; exclude target outcome leakage |
| 16 | Manufacturing/inspection uncertainty | NOT_IMPLEMENTED | Application/facility-specific available CMC/inspection evidence; nonpublic facts remain unknown, not deficiencies |
| 17 | Sponsor disclosure consistency | NOT_IMPLEMENTED | Dated original disclosure versions and an exact-program contradiction ledger |
| 18 | Scientific challenge | NOT_IMPLEMENTED | Owner counterargument/alternative-explanation record tied to accepted sources; no outside reviewer required |
| 19 | Prospective decisions/calibration eligibility | NOT_IMPLEMENTED | Truly prospective frozen inputs and model artifacts, outcome-exposure eligibility and measured out-of-sample calibration; ABSTAIN until supported |
| 20 | Outcome/timing monitoring | NOT_IMPLEMENTED | Exact official action linkage after prediction persistence; separate goal date, action date and timing outcomes |

Level 9 is the first unresolved scientific dependency. Later capabilities are
specified, not represented by decorative buttons or fabricated reports. New
Levels 7/8 outputs are visible through the exact-trial interface; the old runtime
level selector remains 1–6 until unified semantic execution is implemented.
No 9–20 engine is claimed by a generic readiness inventory. Owner-only governance
applies throughout; missing outside people is not a blocker and no owner signoff
was fabricated.

## Actual counts, local real-source execution and limits

- Real trials with documentary evidence in the preserved research manifest: **32**.
- Demonstrated completed scientific evidence reviews: **0**.
- Completed scientifically validated whole-level/six-level assessments: **0**.
- Genuine calibrated FDA predictive models supplied: **0**, predictions **ABSTAIN**.
- Newly fetched real trial: **NCT04576949**, through the existing official collector.
  All Level 1–8 contracts saved/retrieved unchanged in an isolated in-memory
  database; receipt `reports/test-verification/level1-8-real-source-persistence-20261114.json`.
  No reviewed subgroup/exposure calculation was invented for that trial.

Final local validation: root 2,255 passed / 195 skipped / zero failures or errors;
backend **1,358 passed / 2 skipped / zero failures or errors**, plus 28 passing
subtests; frontend **162 test files passed**, zero failed/skipped; TypeScript and
production build passed locally; retirement guard passed with zero active retired
analysis dependencies. Read-only PR CI verifies the delivered commit separately.

Remaining release boundary is explicit: no merge or deployment is authorized by
this task. Existing histories, scores, source versions, source rosters, scheduler
workflows and production records are preserved. Test-only dependencies do not
activate the removed app, survey model, trading or scientific prediction systems.
