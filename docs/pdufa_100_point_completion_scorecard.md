# PDUFA 100-point completion scorecard (research baseline)

**Purpose:** Measure progress toward a scientifically defensible FDA application/review-cycle PASS-versus-FAIL prediction system. This is a **prospective project-management scoring rubric**, not a measurement of predictive accuracy. Scores must be evidence-backed; unverified items earn zero. Never infer completion from passing CI alone.

## SCIENCE — 35 points
| ID | Criterion | Points | Acceptance evidence |
| --- | --- | ---: | --- |
| S1 | Versioned 20-level/8-layer/40-assessment scientific schema with source lineage | 8 | Reviewed schema and traceable assessment definitions |
| S2 | Trial-to-application mapping, dated inputs and missingness flags | 7 | Audited representative trial dossiers |
| S3 | Historical parallel-trial matching without future-data leakage | 8 | Tested retrieval, dated source snapshots and independent reviewer checks |
| S4 | Reproducible scientific scoring with uncertainty and abstention | 7 | Frozen examples, calibration and disagreement analysis |
| S5 | Independent scientific reproducibility audit | 5 | Signed audit and resolved critical findings |

## OUTCOME — 45 points
| ID | Criterion | Points | Acceptance evidence |
| --- | --- | ---: | --- |
| O1 | FDA action taxonomy, conservative metadata screen and review queue | 5 | Code and dedicated passing tests |
| O2 | Authenticated historical PASS and FAIL review-cycle records | 10 | Official original documents, hashes, cycle reconciliation, independent adjudication |
| O3 | Cohort denominator, missing-CRL and selection-bias audit | 7 | Documented population, inclusion/exclusion ledger and coverage |
| O4 | Frozen predecision inputs/predictions and leakage-free time-forward holdout | 8 | Reproducible splits, timestamps and independent audit |
| O5 | Out-of-sample accuracy, calibration and baseline comparison | 10 | Brier/log loss, uncertainty intervals, subgroup performance, predefined acceptance thresholds |
| O6 | Prospective shadow predictions and monitoring | 5 | Pre-registered forward predictions and observed outcomes |

## MAIN — 20 points
| ID | Criterion | Points | Acceptance evidence |
| --- | --- | ---: | --- |
| M1 | Dashboard displays evidence, parallel trials, readiness and abstention | 5 | Mobile/desktop acceptance tests against real representative records |
| M2 | Scheduled collection, source freshness, failure reporting and recovery | 5 | Observed successful unattended runs and alert/recovery checks |
| M3 | Data provenance, access controls, isolation and reproducible deployments | 5 | Operational/security review, deployment receipts and rollback test |
| M4 | End-to-end independent user acceptance and research handoff | 5 | Signed acceptance on real evidence-backed cases |

**Total: 100 points (SCIENCE 35 + OUTCOME 45 + MAIN 20).**

## Scoring rules
- Award criterion points **only** when its acceptance evidence is verified. For partial credit, create a versioned subcriterion breakdown **before** assigning partial points; no subjective percentages.
- Record for every item: points earned, evidence link, reviewer, date, blockers and branch/deployment environment. Unknown evidence = **NOT VERIFIED**, not completed.
- Report three numbers separately: **earned / 100**, **verified points added today**, and **estimated remaining work** (without calling the latter an observed percentage).
- This rubric is established **today**; there is no defensible historical daily percentage delta until a dated baseline audit has been performed.
- Code and CI evidence alone can substantiate **O1 = 5/5**, provided the dedicated tests pass for the reviewed commit. This is **5 verified points on this rubric**, **not** proof that the overall project is only 5% complete; other categories remain **unassessed**.
- Do not present a 100-point total as a model probability of approval or trading readiness. PASS+FAIL probabilities must sum to 100% only for a qualified model output; insufficient evidence requires abstention.
- **Paper trading** requires O2–O6, an independently approved research risk protocol, and simulated execution evaluation. **Live trading consideration** additionally requires prospective paper results, risk/liquidity/slippage controls and explicit separate authorization. Neither follows automatically from a high completion score.
- Preserve GEM JR/GEM original FS/FA preset associations. No production deployments, DB allowlist changes or trading activation by this scorecard.
