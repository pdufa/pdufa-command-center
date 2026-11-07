# BOTTOM post-readout evidence and scoring coverage — 7 November 2026

Scope: exactly the existing 23 post-data BOTTOM NCTs. The system preserves original BOTTOM and TOP data and does not reclassify trials, rewrite old score history, or activate archived commercial/finance/FDA metrics.

## What is available now

- **23/23 trial rows**, each with **190/190 fields accounted for** (4,370 cells). Missing/undisclosed labels are not scientific facts.
- **690/690 metric dispositions**, with **only five active clinical factors** per trial; 25 historical metrics remain archived.
- **25/115 numerical factor reviews** (21.7%); **90 remaining unscored factors**.
- **2/23 complete five-factor research scores** (ENERGIZE NCT04770753 and ACACIA-HCM NCT06081894), not FDA approval probabilities.
- **436/690 source-backed question evidence slots** (63.2%); **254 research gaps**. Some gaps concern pending follow-up or non-public information.
- 11 additional exact-NCT source-reviewed findings and one provisional durability metric review. No missing grade is assigned 0 or default 50.

## How to continue

Read `bottom-missing-clinical-factors.csv` for 90 precise scoring tasks, and `bottom-unreviewed-questions.csv` for missing individual evidence fields. For each exact NCT, retrieve complete Phase 3 results, full clinical safety, clinical comparators, statistical analysis plan, long-term results and prespecified replication/subgroups. Record dated source, benchmark, uncertainty and evidence type before applying the existing rubric; mark undisclosed details clearly. Do not treat endpoint pass as an automatic FDA approval or historical forecast.

## Live BOTTOM-only interfaces

- `/api/bottom-only-completion` for all 23 and summary; append `?nctId=NCT...` for exact evidence and persistent snapshots.
- `?format=csv` — BOTTOM 23×190 preserved/annotated cells.
- `?format=metrics` — 690 individual metric states and ratings.
- `?format=facts` — 11 additional reviewed source statements.
- `/raas-top-bottom` — BOTTOM with horizontally expandable ingredients and history; TOP is unchanged.

Successful software tests show the implementation works, not that publicly undisclosed or future clinical data exist. The active five-factor scores are provisional research ratings, not validated FDA/PDUFA or investment probabilities.
