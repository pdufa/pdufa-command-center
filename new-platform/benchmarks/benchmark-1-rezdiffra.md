# Benchmark 1: Rezdiffra (resmetirom), NDA 217785

Status: SPECIFICATION ONLY — no validated prediction or completed SCIENCE/OUTCOME/MAIN run.

## Historical test
Sponsor: Madrigal Pharmaceuticals. Indication: noncirrhotic NASH with F2–F3 fibrosis.
Historical FDA action: accelerated approval, March 14, 2024. This outcome is **evaluation-only** and must never enter prediction inputs.

## Leakage firewall
- Fix evidence cutoff at **2024-03-13 23:59:59 America/New_York** (or an earlier documented cutoff).
- Each prediction input must carry source URL, publication timestamp, retrieval timestamp, excerpt/hash, and explicit proof it was public by cutoff.
- Reject undated, post-cutoff, retrospectively amended, or ambiguous sources from the prediction side.
- FDA 2024 approval letter, integrated review, labels, approval press releases and later retrospective analyses are **outcome-side only**, never predictor features.
- Freeze and hash the input manifest, assessment outputs, model/rules version, and decision before unsealing the outcome.
- Never present an outcome-aware reconstruction as a blinded prediction.

## Required pipeline
1. SCIENCE: 40 individually numbered assessments, each with evidence, quality, missingness, conflicts, uncertainty and pass/fail/abstain applicability.
2. OUTCOME: regulatory pathway and risk analysis from eligible pre-cutoff evidence only.
3. MAIN: PASS / CRL / EXTENSION / ABSTAIN, with confidence calibration and explicit reasons.
4. Dashboard: 12 headline metrics and 48 expandable supporting metrics, with source provenance.
5. Evaluation: after frozen prediction, unseal outcome, score correctness and explain error.

## Outcome-only ground truth
FDA approval announcement: https://www.fda.gov/news-events/press-announcements/fda-approves-first-treatment-patients-liver-scarring-due-fatty-liver-disease
FDA approval letter: https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2024/217785Orig1s000ltr.pdf
FDA integrated review (post-action document): https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/217785Orig1s000IntegratedR.pdf

## Completion gates
- [ ] Dated pre-cutoff source manifest independently audited.
- [ ] All 40 SCIENCE assessments executed.
- [ ] OUTCOME and MAIN executed without outcome leakage.
- [ ] Frozen decision and source hashes persisted.
- [ ] Historical comparison completed after freeze.
- [ ] UI verified; no trading authorization.

Existing PIPELINE/GEM JR/GEM/WT restrictions and GEM FS/FA memberships must remain unchanged.
