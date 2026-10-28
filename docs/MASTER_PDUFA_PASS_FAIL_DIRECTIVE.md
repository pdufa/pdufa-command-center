# MASTER DIRECTIVE — PDUFA PASS/FAIL PREDICTION SYSTEM

Status: governing development plan; implementation and predictive accuracy must be verified independently. Adopted 2026-10-27.

## Primary mission
Develop the most accurate scientifically defensible, historically validated, data-driven system possible for predicting FDA approval or nonapproval at the PDUFA decision. Every component must demonstrably contribute to prediction, challenge, validation, or improvement. Do not confuse implementation progress with predictive performance.

## 1. Automatic investigation
For every Pipeline trial, automatically investigate all available evidence from earliest drug development to current regulatory status: efficacy, safety, statistics, design, endpoints, manufacturing, regulatory interactions, special designations, and other relevant factors. Record provenance and as-of dates.

## 2. Historical FDA parallels
Automatically retrieve relevant prior FDA application decisions and compare mechanism, indication, population, trial design, endpoints, efficacy, safety, benefit-risk, pathways, designations, regulatory objections, manufacturing issues, and final outcome. Determine which differences actually predict outcomes; do not rely on superficial similarity. Keep historical parallels collapsed by default, with a verified count/availability indicator and on-demand expansion. Deduplicate overlapping evidence and FDA applications.

## 3. Comprehensive SCIENCE
Apply the 20 depth levels, scientific subject layers, and assessment matrices. For each assessment explicitly state whether evidence raises, lowers, or leaves unchanged approval probability, with quality, uncertainty, missingness, contradictions, and rationale. Depth/assessment count is not a success metric.

## 4. Probability calculation
Define the exact binary target event and decision horizon before training. For binary eligible outcomes: P(PASS)+P(FAIL)=100%. Display separately predicted outcome, approval probability, prediction confidence, evidence completeness, historical precedent strength, scientific/regulatory risk, and readiness. Do not fabricate percentages or conflate these measures.

## 5. Adversarial challenge
For every prediction seek contrary evidence: historical failure patterns, inconsistent efficacy, safety, weak statistics/design, FDA objections, CMC/manufacturing deficiencies, and missing or contradictory evidence. Record strongest pro and con cases and any resulting probability revision.

## 6. Historical backtesting
Build verified application-level historical FDA decision corpus. Reconstruct only predecision information at each historical cutoff. Predict blinded to actual outcomes, then compare with verified decision. Track errors, calibration (including Brier score and reliability), discrimination, uncertainty, baseline comparisons, temporal independent holdouts, subgroup performance, and leakage/overlap controls. Never claim gains without independent test evidence.

## 7. Continuous improvement
Add verified historical decisions and new evidence; version data, model, feature definitions, cutoff, predictions, and evaluations. Evaluate upgrades on unchanged holdouts before claiming improvement.

## 8. Final decision
For each eligible application output PASS (approval predicted), FAIL (nonapproval predicted), or INSUFFICIENT EVIDENCE (abstention, not third FDA outcome). Include probability, confidence, evidence readiness, supporting/opposing factors, and historical validation context. CRL is nonapproval at that decision, not permanent rejection. Predefine withdrawn, delayed, rescinded, resubmitted, and other nonbinary/censored events before model fitting and scoring. Never force an unreliable binary prediction.

## 9. System-wide integration
- PIPELINE: discovery and automatic initiation.
- GEM JR / GEM / WT: retain existing selection/ranking rules; share prediction framework.
- SCIENCE: scientific and regulatory evidence assessment.
- OUTCOME: historical outcomes, validation, calibrated probabilities.
- MAIN: integrate evidence, challenge, and present PASS/FAIL.
- SCAN: detect changes, refresh evidence and versioned predictions.
Preserve GEM JR/GEM FS/FA restriction associations without explicit approval to change them.

## 10. Governing principle
Every operation must contribute to accurate future FDA decision predictions. The ultimate measure is out-of-sample, independently validated accuracy and reliability on genuinely unseen applications.

## Delivery gates
G1: verified master trial/application IDs, provenance, and outcome taxonomy.
G2: historical FDA corpus with approvals, CRLs, withdrawals, dates and predecision evidence.
G3: background parallel retrieval, citation audit, and collapsed on-demand detail.
G4: 20-level SCIENCE assessments with evidence-direction and adversarial review.
G5: binary outcome definition, abstention policy, probability model and calibration.
G6: blinded temporal holdout evaluation against baselines; publish metrics and uncertainty.
G7: integrate PIPELINE/GEM JR/GEM/WT/SCIENCE/OUTCOME/MAIN/SCAN in review.
G8: production release only after data integrity, safety, and validation gates pass.

## Explicit nonclaims
This directive is a committed plan, not proof that the historical dataset, parallel engine, prediction model, calibration, dashboards, or production integration are complete. No trading authorization follows from this document.
