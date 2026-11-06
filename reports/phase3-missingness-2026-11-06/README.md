# Phase 3 missingness priority report — November 6, 2026

Source: [Latest verified live production trial audit](https://pdufa-new-dashboard-iwky8fplq-pdufa.vercel.app/api/phase3-missing-data-audit) and its [per-trial status CSV](https://pdufa-new-dashboard-iwky8fplq-pdufa.vercel.app/api/phase3-missing-data-audit?format=csv). Snapshot generated from 762 unique NCT trials, 137 companies, 190 production export columns, 30 question-level assessments per trial.

- **[All 762 trials ranked, highest missing first](phase3-trials-ranked-762.csv)** — 762 data rows, individual question statuses Q01–Q30 and contextual document/registry gaps.
- **[All 137 companies ranked by combined outstanding assessments](phase3-companies-ranked-137.csv)** — 137 data rows, per-company average and the trial most in need of research.

## Ranking criteria

The first sheet is ranked by **number of currently UNSCORED assessment questions**, descending; tie-breakers are lack of primary-endpoint adjudication, absent detailed research, absent stored protocol, ticker and exact NCT ID. Ties represent equal missing-question counts, not evidence of different clinical risk. The company sheet ranks by **sum of unscored assessments** across the company's trials, not mean per trial. A company with more trials may rank higher simply due to cohort size; compare the average column for intensity.

## Verified counts

| Metric | Value |
|---|---:|
| Total distinct NCT trials | 762 |
| Companies | 137 |
| Total question slots | 22860 |
| Unscored question slots | 13144 |
| Question slots with documented source facts | 9541 |
| Prediction slots | 61 |
| Observed readout slots | 114 |
| Documented design interpretations still pending | 1477 |
| Research/interpretation tasks including design documents | 14621 |
| Trials without adjudicated endpoint | 705 |
| Unverified FDA application entries | 742 |
| Unverified PDUFA date entries | 753 |

**Important:** The 1,477 documented Q06 and Q26 interpretation tasks are not counted as UNSCORED when the trial has source facts; therefore the trial ranking captures **missing question-level scoring**, not a perfect count of every future scientific interpretation task. This is a research-priority report, not a clinical assessment or investment forecast. FDA and PDUFA statuses are trial-to-application links and not a PASS/FAIL efficacy score. The user's planned 192 columns have not been confirmed in production; the live export reports 190.

Top individual trial: Ionis Pharmaceuticals, Inc. / IONS / NCT00017407 — 27 of 30 unscored.

Top aggregate company: Alkermes, Inc. (ALKS) — 546 unanswered slots across 34 trials.
