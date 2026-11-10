# MAIN Revision 51 — Source-reported Phase 3 efficacy and adverse-event dossiers / parallel historical review

_Date: 2026-11-09. Feature branch `feature/medical-stage4-verified-method-matrix-20261108`, draft PR #965. Development/research only._

## Verified concurrent progress

### Track A — current 29 NCT / 23 application evidence dossiers

[Exact independent GitHub run 42688300979](https://github.com/pdufa/pdufa-command-center/actions/runs/42688300979) **SUCCESS**: 96 targeted tests PASS, original canonical FOCUS 29-NCT and 23-application SHA lockdown preserved, permanent retirement audit PASS, no clinical/production writes. Full archived registry raw bytes and output [artifact 13704538380](https://github.com/pdufa/pdufa-command-center/actions/runs/42688300979/artifacts/13704538380), append-only [research history revision 7 artifact 13704944004](https://github.com/pdufa/pdufa-command-center/actions/runs/42688300979/artifacts/13704944004).

Implemented:
- `new-platform/backend/scripts/build_focus_application_efficacy_safety_r51.py` — writes original-current-registry `application-efficacy-safety-research.json` with **23 evidence-indexed application records and 29 unique linked NCT records**.
- `new-platform/backend/tests/test_focus_application_efficacy_safety_r51.py` — full 29/23 crosswalk, preserve SRPT NCT02500381 linking to both application research groups without creating duplicate unique trials, original registry SHA reconstruction, independently replay exact primary and AE source-extract outputs, detect falsified statistical entries or safety-group counts, preserve ABSTAIN and unavailable result status.
- Existing `.github/workflows/main-r47-parallel-focus-historical-research.yml` generates and checks 23 read-only dossiers, retains full original current registry source bytes under per-run artifact; existing immutable research chain appends separately without resetting historical revisions.

### Actual source dataset counts

| Source-reported current public registry evidence | Count |
| --- | ---: |
| Exact FOCUS NCT records | 29 |
| Original provisional application groups | 23 |
| Unique NCTs with current posted primary outcome tables | 12 |
| Unique NCTs with current adverse-event modules | 12 |
| Application groups with at least one posted primary table | 8 |
| Application groups with at least one adverse-event module | 8 |
| Posted primary outcome tables | 16 |
| Reported primary statistical analysis rows (p-values/methods **as published**) | 20 |
| Reported serious AE term rows, **not** patients or pooled risk | 244 |
| Reported other AE term rows, **not** patients or pooled risk | 202 |
| Independent scientific grade authorizations or validated FDA forecasts | **0** |

The **8 current source-posted application groups** are ABVX-UC, ACHV-cytisinicline, APMD-AD109, CORT-relacorilant, CYTK-aficamten-ohcm, SVRA-molgramostim, URGN-UGN103, and VERA-trutakna. The other application records are **not** concluded to have failed trials or no publications; they lack posted primary results in these currently captured ClinicalTrials.gov records. Sponsor/journal publications, original locked SAP versions, updated registry histories, submitted FDA dossiers, safety clinical study reports and CMC reviews must be sought independently.

Each NCT research record retains the as-reported endpoint names/timeframes, registered primary endpoint metadata, primary group measurements, source statistical-analysis rows including unverified p-values, separate adverse-event group denominators and terms, present protocol/SAP attachment metadata, source SHA-256, and current-registered versus posted title/timeframe exact-match flags.

**Do not interpret the 20 source-reported analysis rows as scientifically multiplicity-controlled success, the AE term rows as incident patient counts or causal safety effects, or posted data as the original unblinded readout evidence.** Efficacy, CMC, regulatory status and benefit-risk require independently timed original publications and signed assessments. No approval probabilities are emitted. All currently pending official FDA outcome and timing forecasts remain ABSTAIN; historically observed approvals are not forecasts.

### Track B — historical source action integrity and original FDA FY2024 cycle actions

[Verified parallel GitHub run 42689302249](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249) **SUCCESS**, after strengthening original archived parsed-source identity checks and updating intentional-source-mutation regression fixtures. The repaired workflow matches the parsed published FDA records to immutable raw bytes. It cross-reconciles **412/412** selected FDA outcome-side records: 292 original approval registry action rows, 10 tentative approvals, and 110 selected published CRL rows. Audit maintains 376 provisional parent source groups and prevents duplicate action rows from masquerading as independent forecast cases.

The same research run included the official FY2024 FDA approved-only review-history appendix: **186 source-cycle action rows** (126 approval, 43 complete response, 17 tentative approval). These are real FDA source **action-table entries**, not an unbiased NDA/BLA filing population or 186 qualified predecision blind-prediction cases. History **revision 4** preserved in [artifact 13705952530](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249/artifacts/13705952530); [raw and derived sources 13705922988](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249/artifacts/13705922988).

**0 verified independent original clinical historical prediction cases, 0 source-timed out-of-time calibration grades, and no measured/100% accuracy.** The outcome-side historical corpus must never be directly fed as predictor inputs. The FY2024 appendix is approved-only and cannot establish a complete consecutive filing cohort or estimate approval probabilities.

## Remaining release gates

1. For each of the 8 application groups with currently posted registry outcomes, reconcile the **original dated protocol and pre-readout SAP**, primary and key secondary hierarchy, clinically relevant effect estimates, discontinuations, denominator populations, and original independent analysis.
2. For the other 15 application groups, find relevant **primary original sponsor/journal trial readout sources** without incorrectly treating missing current registry tables as trial failure.
3. Independently review all 23 applications' indication-specific benefit-risk, external efficacy consistency, FDA acceptance/review cycle, CMC/inspection gaps (unknown is not a failure), and unresolved regulatory concerns.
4. Build a **consecutive historical original NDA/BLA filing cohort** including pending, withdrawn, CRL and approved decisions, link exact program/NCT/review cycle and freeze predecision publicly available evidence BEFORE opening outcome labels.
5. Generate outcome-blind research predictions and later independently adjudicate labels, holdout forecasts and empirical calibration. Do not treat synthetic calibration tests or current source-action counts as actual FDA prediction accuracy.

## Operational caution

Track A and Track B run independently on the feature branch, each with its own history and artifacts; **GitHub cron schedules only activate from the default branch** after separately reviewed merge. Draft PR #965 remains unmerged and production has not changed. RAAS/GEM/TOP/BOTTOM and retired P3 workspaces remain inactive and must not be restored.
