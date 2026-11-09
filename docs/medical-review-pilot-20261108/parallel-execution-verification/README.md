# Parallel prediction-engine installation: recovered push and live execution

The existing draft PR [#965](https://github.com/pdufa/pdufa-command-center/pull/965) and branch `feature/medical-stage4-verified-method-matrix-20261108` were preserved. The stopped push actually succeeded at **`f42605f7228960386e7fce207327c7a996391cb7`**. A fresh fetch confirmed local/remote equality and a clean worktree before receipt collection. No reset, force-push, roster edit, production deployment, database-role change, vault activation or clinical-write activation occurred.

Git confirms three focused commits after the preserved R48 checkpoint `4d75879b7676df2c3947e8d78ea4d179ff48bb33`: original manuscript research `41b8fc6fe780addde11bfc381a1c606f6cd8b723`; validation-only calibration `c55f376e28f40c85e0baa694991a71da2070b7ec`; independent workflows/history `f42605f7228960386e7fce207327c7a996391cb7`. Their combined diff is **26 files, 2,178 insertions, 31 deletions**. The earlier approximate four-file description is not the final committed file inventory. No unfinished implementation files were recovered or discarded.

## Actual concurrent execution

| Measure | Track A — FOCUS scientific prediction research | Track B — historical FDA backtesting/calibration |
| --- | --- | --- |
| Existing workflow completed | Yes | Yes |
| Independent job and concurrency group | Yes; no dependency on B | Yes; no dependency on A |
| Automatic push execution | [42678294690](https://github.com/pdufa/pdufa-command-center/actions/runs/42678294690), SUCCESS | [42678295071](https://github.com/pdufa/pdufa-command-center/actions/runs/42678295071), SUCCESS |
| Manual restoration execution | [42679838862](https://github.com/pdufa/pdufa-command-center/actions/runs/42679838862), SUCCESS | [42679836978](https://github.com/pdufa/pdufa-command-center/actions/runs/42679836978), SUCCESS |
| Actual scope | 29 exact NCTs / 23 existing groups / 23 versioned research records | 412 selected source-action records / 376 identity groups |
| Source availability | 23/24 application source URLs retrieved; all 23 groups have at least one source | Original FDA approved registry and published-CRL exports retained and hash checked |
| Qualified new scientific predictions | 0; 22 ABSTAIN and 1 previously observed, nonforecast case | 0 |
| Independently validated forecasts | 0 | 0 independently verified cycles |
| Real historical backtests / calibration fits | Not represented by current-source research | 0 / 0 |
| Measured accuracy/calibration | Unavailable | Unavailable |
| Saved history restoration | First event preserved exactly; revision 1 → 2 | First event preserved exactly; revision 1 → 2 |
| Recurring cron configured | Yes, feature-branch declaration | Yes, feature-branch declaration |
| Recurring schedule actually operational | **No** | **No** |

Actual job timestamps prove overlap. Initial jobs overlapped **10:54:53–10:55:22 AM Pacific on November 9, 2026 (29 seconds)**. Manual restoration jobs overlapped **11:04:40–11:05:05 AM Pacific (25 seconds)**. These are measured execution intervals, not claimed processing estimates. The workflows did not wait for one another. Separate starts, step progress, completion statuses, failure annotations, artifacts and history chains are retained.

The first executions seeded separate history artifacts. The second executions actually found and downloaded their prior artifacts, passed the restore steps, preserved the complete first event and appended hash-linked revision 2. A downloaded-but-missing history file, corrupted chain, unauthorized numerical prediction or expired prior archive fails closed. A failed delivery run with a valid history artifact remains eligible for restoration; no silent history reset is allowed.

Track A's second run detected 19 changed source-byte versions and four unchanged cases. **Zero material scientific changes were independently adjudicated.** These are review requests, not 19 new findings or predictions. Temporary availability changes have their own classification. Existing unsigned research leans and all authorized scientific histories remain separate and unmodified.

## Verified outputs and limitations

[Track A's receipt and reproducible audit](./track-a/README.md) verify 29 canonical NCTs, the exact 23 application groups, 23 current research records, 12 NCTs with posted primary tables and 12 with SAP attachment metadata. All 29 retain independent-evidence gaps. **112 raw-reference SHA-256/identity checks passed**. Both additional FDA responses are actual PDF bytes, with their historical roles retained: Capricor's pre-amendment staff briefing is not its later final action, and the prior obstructive-HCM approval letter does not verify a current MAPLE review cycle. One ACHV source returned HTTP301; the separately recorded SEC source was available. No redirect restriction was bypassed.

[Track B's first artifact receipt](./track-b/verification-receipt.json) authenticates 29,446 approved-registry rows and 458 published-letter rows as original public-source exports. Their selected 412-action union is not a complete filing cohort. R48 grouping yields 376 identities: 369 standard parent IDs and seven unresolved groups; 33 repeated parents, 15 mixed approval/CRL parents, ten parents with multiple CRL rows and four same-day collision groups. None of those groups is automatically an independently adjudicated review cycle. Candidate hashes, the R48 audit and its quarantined worklist were recomputed from the actual archive bytes.

[The actual calibration checkpoint](./track-b/actual-calibration-checkpoint.json) includes the new validation-only isotonic infrastructure. It separates chronological training, validation-only calibration fitting and an untouched, disjoint-family test set, with frozen original predecision packets and separate approval/CRL/delay targets. That code has **not fitted a real model**: independently eligible cycles, training cases, validation cases, test cases and real calibration fits are all zero. Brier score, log loss and measured accuracy remain null. Synthetic protocol tests never enter the FDA source cohort.

New original ACACIA evidence is documented in the [institutional-manuscript packet](../revision37-source-reconciliation/README.md), with original host, manuscript version, license, dates, hash, page locators and six exact-method handoffs. It supports a distinction between 517 randomized and 516 exposed participants and supplies treatment-period HF/interruption definitions. It does not silently reconcile sponsor 12/3 against treatment-period 11/1, or the secondary 14(2.7%) against the primary manuscript's 7(2.7%). The final locked SAP, complete disposition/analysis populations and authorized independent adjudication remain outstanding. No full licensed manuscript was imported into the product, Git repository or training data.

## Tests, deployment and scheduling

[Full CI 42678295235](https://github.com/pdufa/pdufa-command-center/actions/runs/42678295235), at exact code commit `f42605f7228960386e7fce207327c7a996391cb7`, passed backend, frontend, type checking, production build and retirement policy. Actual CI logs report **1,493 backend passed, 6 skipped, 7 warnings**, and **868 frontend tests passed, 0 failed, 0 skipped**. Local logs separately report **1,491 backend passed, 8 skipped, 6 warnings** and **158 frontend test files passed**; optional environment-dependent fixtures account for the differing pass/skip counts, and no skipped test is clinical acceptance. Twenty retirement unit tests passed; the active dependency audit inspected 262 entrypoints with zero violations. Source-packet integrity passed 21 checks. Track A's live targeted suite passed 58 tests; Track B's passed 78. No outstanding test or workflow failures remain in these verified runs. Failure isolation, history integrity, leakage and unauthorized numerical-release rejection are covered by the tests.

Vercel automatically built development preview `dpl_Bm8zgMKe5CEdD8kcTj9CqjTneWZn` at [the unique feature preview](https://pdufa-new-dashboard-74ctjqkja-pdufa.vercel.app), state READY. This is build evidence, not a new signed-in browser acceptance or a trained predictor deployment. The Render/production deployment and acceptance jobs were skipped in this push CI. No alias was reassigned, production merge performed, restricted vault activated or automatic model deployment enabled.

Both workflow files declare the same daily UTC cron; at the current Pacific offset it corresponds to 02:28 AM Pacific. Their source files **do not exist on the default branch `main`**, independently checked with HTTP404 responses. GitHub schedules execute default-branch definitions, so recurring daily execution is **not operational**. Push and manual triggers have both actually executed on the feature branch. Activating a default-branch schedule still requires explicit approval and a reviewed rollout; PR #965 remains draft.

Artifacts retain their original 90-day expiry (February 7, 2027 for the verified runs); they are not claimed as permanent backups. Each new run carries forward its complete prior research chain. An expired required archive is an explicit restore dependency, not permission to reset history.

## Remaining blockers and next action

1. **Historical training denominator:** no complete consecutive filing roster including negative, pending and withdrawn cases is independently verified. More selected approval/CRL rows do not establish that denominator.
2. **Exact cases and temporal truth:** application, indication, supplement/resubmission cycle, pivotal-readout first-publication time, as-published evidence versions and independently adjudicated outcomes remain unverified for model eligibility.
3. **Real holdout/calibration:** sealed outcome custody and enough qualified, family-disjoint training/validation/test cases have not been established. No real error rate, discrimination, calibration or improvement claim is available.
4. **Current scientific review:** original locked SAP, disposition/safety reconciliation and qualified independent phase/method review remain required. Documentary source retrievals and method slots are not scientific grades.
5. **Recurring operation:** approved default-branch installation and durable archive planning remain dependencies; no production action was authorized or performed here.

The next specific model-development action is to construct and independently verify a denominator-complete historical filing cohort and its exact-cycle/predecision-source crosswalk. Only after that evidence exists can real blinded predictions be sealed, outcomes released separately and calibration evaluated on untouched cases. Current FDA APPROVAL, CRL and REVIEW_DELAY remain **ABSTAIN**, certainty **NOT_VALIDATED**, accuracy **NOT_CALIBRATED**.

[Combined machine-readable recovery and concurrency receipt](./recovery-and-parallel-execution-receipt.json) binds the four actual runs and per-track receipt hashes. Closing repository changes contain verification documentation/receipts only.
