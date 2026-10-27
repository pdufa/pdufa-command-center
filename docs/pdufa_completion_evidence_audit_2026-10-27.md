# PDUFA 100-point scorecard — initial evidence audit (2026-10-27)

**Scope:** Repository research branch `feature/decision-workstream-20261026`; targeted inspection of documented research modules and dedicated GitHub CI. This is **not** an exhaustive audit of SCIENCE/MAIN deployment, database contents, or live operations.

## Verified credit
| Criterion | Awarded | Maximum | Basis |
| --- | ---: | ---: | --- |
| O1: FDA action taxonomy, conservative metadata screen and review queue | **5** | 5 | `scripts/fda_decision_taxonomy.py`, `scripts/screen_fda_evidence.py`, `scripts/build_fda_evidence_review_queue.py`, dedicated pytest workflow passing on 2026-10-27 for queue tests |

**Verified audited subtotal: 5 / 100 points.** This is a **lower bound**, not an estimate that the entire system is 5% complete. The unreviewed criteria cannot yet be assigned scores.

## Implemented components inspected, not yet awardable
| Criterion | Evidence of implementation | Why not credited yet |
| --- | --- | --- |
| S3 (8) | `scripts/historical_parallel_matching.py` (candidate retrieval) | Source snapshots, independent historical parallels and no-leakage review not established |
| O2 (10) | `scripts/audit_fda_decisions.py` (candidate audit) | No authenticated independently adjudicated PASS and FAIL corpus demonstrated |
| O3 (7) | Candidate audit's conflict and exclusion reporting | Cohort denominator and missing-CRL coverage not independently verified |
| O4 (8) | `scripts/evaluate_fda_predictions.py` requires frozen predecision records | Actual time-forward frozen holdout and independent leakage audit not demonstrated |
| O5 (10) | `scripts/compare_fda_prediction_baseline.py` and evaluation metrics | No independently validated real holdout results or uncertainty intervals demonstrated |

## Not assessed in this targeted audit
S1, S2, S4, S5; O6; M1, M2, M3, M4. These are **UNKNOWN / NOT AUDITED**, not necessarily absent or incomplete. The remaining points are **uncredited**, not necessarily unbuilt.

## Next audit steps
1. Inspect SCIENCE 20-level/8-layer/40-assessment implementation, trial dossier lineage, frozen examples, and independent review.
2. Inspect MAIN dashboard UI, unattended scan receipts, deployment and rollback evidence, and mobile acceptance tests.
3. Inspect OUTCOME source hashes, independently adjudicated PASS/FAIL records, missing CRLs, cohort coverage, and frozen real predictions.
4. For each criterion, attach dated acceptance evidence and independent reviewer identity; then award points.

## Readiness
Predictive accuracy is **not validated**. Paper trading and live trading **NOT READY**. No production deployment or trade activation performed by this audit.
