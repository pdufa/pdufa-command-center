# ALKS — 34 exact-NCT Phase 3 trial scoring register (2026-11-06)

This is a non-production evidence-scoring and historical-outcome research register for **all 34 Alkermes (ALKS) NCT records** in the 762-trial census. It intentionally does **not** alter existing approved/validated RAAS scores, the live 190-column export, or the five-clinical-factor rating matrix.

## Score definitions

- **Research evidence coverage, 0–100**: 100 × (30 minus unscored questions) / 30, rounded to one decimal. This counts documented facts/observations and recorded predictions as covered slots; *does not* represent drug efficacy, pass probability, clinical trial quality, FDA approval likelihood, or RAAS rating.
- **Existing trial-design diagnostic, 0–100**: existing registry-based diagnostic from the saved `raas-trial-score-ledger.csv`, reproduced without changing its methodology. A 100 can appear for failed or terminated trials. It is not a success prediction.
- **Historical primary outcome**: MET or NOT_MET only where a cited original issuer report or peer-reviewed exact-NCT paper substantiated the result in this research pass. All other exact-NCT records remain NOT_ADJUDICATED_IN_THIS_PASS.
- **Five clinical metrics and full RAAS 30-metric score**: **blank for all 34**, because the stored records do not contain 5/5 or 30/30 defensible reviewed clinical metric assessments for these exact studies. Never interpret blank as zero or assign a neutral 50.

## Results

- 34/34 exact-NCT records present, with numeric **documentary evidence coverage** and **existing design diagnostic**.
- 546/1020 analytical slots unscored; 474/1020 contain a recorded source or observation status; mean documentary coverage ~46.5%.
- Historical observed outcomes added for **7** exact NCTs: **5 met and 2 did not meet** their original primary endpoints. Those are retrospective facts, not pre-readout forecasts or FDA verdicts.
- **0/34 validated overall RAAS research scores.** The file is not a completed efficacy-probability model.

## Input provenance

- Exact 34-NCT census: [Phase 3 $300M–$10B roster](../../data/phase3_all_years_300m_10b_trials.csv).
- Question status audit: [762-trial research gap report](../phase3-missingness-2026-11-06/phase3-trials-ranked-762.csv).
- Design diagnostics: [RAAS trial source score ledger](../../new-platform/frontend/public/raas-trial-score-ledger.csv).
- Drug and indication labels: [ALKS shared enrichment](../../data/shared_enrichment/records/ALKS.json).
- Exact historical primary-outcome source URLs are in the CSV itself. For FORWARD-4, company reports that the originally specified primary endpoint was not met; later reanalysis does not reverse that status.

## Research priority

1. Do not carry observed post-readout outcomes backward into pre-readout forecasts.
2. Analyze and cite the primary endpoint, including original protocol and statistical analysis plan.
3. Retrieve drug-indication-specific prior Phase 2 benchmarks, pharmacology, safety exposure, and missingness analyses.
4. Apply the formal RAAS rubric to each trial and stage only when stage and exact-metric source requirements are met.
5. Attribute any PDUFA application/decision to the exact drug, indication, and FDA application; do not treat an NCT record as a unique approval.
