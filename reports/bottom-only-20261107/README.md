# BOTTOM Phase 3 post-data clinical evidence audit — 2026-11-07

## Scope and recomputed starting point

The requested saved BOTTOM research cohort contains **23 exact NCTs**. The current canonical Google Sheet and website roster contain **29 active NCTs**; only **5** overlap. These are different populations. No company/drug-name score transfer, trial deletion, active-roster expansion, TOP/Pipeline mutation, or workflow reactivation was performed. See `roster-parity-audit.json`.

The saved coverage snapshot (25 grades, 2 complete trials, 247 question gaps) was stale. Before editing, the engine yielded **36/115 grades, 5 complete trials, 449/690 source-backed question slots and 241 gaps**. `starting-engine-coverage.json` records that calculation; the original report and task CSVs remain under `baseline-*`.

## Current results

- Processed: 23/23 saved research NCTs; all have exact-NCT registry records and Phase 3 identity checks.
- Numerical factors: **98/115** (62 additional supported grades); missing: **17**.
- Complete five-factor research scores: **14/23**, at the existing equal 20% weights.
- Source-backed question coverage: **487/690 (70.6%)**; 203 question gaps remain.
- Field-level traceable evidence: **1622/2990 (54.2%)**. The 1,380 archived forecast/subjective-score cells are retained and excluded from this denominator. Nonmissing population of all 4,370 historical cells is separately 2566/4,370 (58.7%).
- Fully populated research: 0; partial: 23; no available research: 0.
- Full historical 30-metric scorecards: 0. They remain archived and do not contribute to clinical scores. No FDA prediction is inferred.

| Factor | Numerical | Pending / insufficient evidence | Blocked rule |
|---|---:|---:|---:|
| Actual Phase 3 efficacy | 21 | 1 | 1 |
| Clinical importance and patient benefit | 21 | 2 | 0 |
| Statistical reliability | 20 | 3 | 0 |
| Replication and durability | 21 | 2 | 0 |
| Safety and tolerability | 15 | 8 | 0 |

## Exact remaining grade blockers

| NCT | Factor | State | Required evidence or rule |
|---|---|---|---|
| NCT05144256 | post-1-5 | NOT_REPORTED | Exact pediatric arm-level all-cause AE/SAE and exposure-adjusted safety tables are not in the retrieved topline. No AE withdrawals is insufficient for a complete safety assessment. |
| NCT05175105 | post-1-2 | NOT_REPORTED | Hb response is quantified but pediatric fatigue, function or QoL magnitude and validated patient-benefit benchmark are not reported. |
| NCT05175105 | post-1-5 | NOT_REPORTED | Topline says similar AEs and no withdrawals; full pediatric arm-level AE/SAE counts and severity tables are not reported. |
| NCT06747468 | post-1-3 | MISSING_EVIDENCE | Full effect CIs, absolute arm event rates, multiplicity and missing-data sensitivity results are absent from retrieved issuer topline; publication search did not establish these. |
| NCT06747468 | post-1-4 | PENDING | Only 16-week controlled results reported; 32-week open-label extension remains ongoing and no published longer follow-up was located. |
| NCT06747468 | post-1-5 | NOT_REPORTED | No drug-related SAE statement does not supply all-cause SAE rates, denominators or discontinuation table by arm. |
| NCT05453968 | post-1-1 | BLOCKED_RULE | Exact Phase 3 primary outcomes are pediatric pharmacokinetics. No approved conversion from PK exposure matching to the active primary clinical efficacy grade exists. Required rule: how to grade a PK-primary pediatric bridging study under post-1-1 without presenting secondary uncontrolled attack reduction as randomized primary efficacy. |
| NCT06445023 | post-1-5 | NOT_REPORTED | Retrieved Phase 3 issuer readout and 2026 Q3 SEC filing provide qualitative tolerability but no exact-study arm-level all-cause SAE and discontinuation tables. Do not substitute Phase 2 data. |
| NCT06455202 | post-1-5 | NOT_REPORTED | Retrieved Phase 3 issuer readout and 2026 Q3 SEC filing provide qualitative tolerability but no exact-study arm-level all-cause SAE and discontinuation tables. Do not substitute CSU1 or Phase 2 data. |
| NCT05711940 | post-1-5 | NOT_REPORTED | COMP006 25 mg six SAEs in six people (2%) reported, but matching 1 mg/10 mg all-cause SAE and withdrawal tables are not supplied in the retrieved release. COMP005 safety is not this NCT. |
| NCT04768972 | post-1-1 | PENDING | FUSION issuer reports p=0.0005 for joint rank, n73 primary population, without arm-level joint-rank effect or confidence interval. Detailed congress/publication results promised later. |
| NCT04768972 | post-1-2 | PENDING | No quantitative ALSFRS-R, survival, rescue or QoL arm effects supplied in topline; composite p-value cannot establish magnitude of patient benefit. |
| NCT04768972 | post-1-3 | PENDING | Only primary p-value; no effect CI, full multiplicity or missing-data sensitivity results. Complete statistical results promised later. |
| NCT04768972 | post-1-4 | PENDING | 72-week design and extension plans are documented but actual longitudinal effects, attrition and independent confirmatory results are not disclosed. |
| NCT04768972 | post-1-5 | PENDING | Most AEs mild/moderate is qualitative; all-cause AE/SAE, attribution and discontinuation counts by arm not disclosed; full results forthcoming. |
| NCT06641076 | post-1-3 | PENDING | Week 16 issuer release explicitly withholds placebo comparisons and full arm data to maintain blinding through Week 52; numerical CIs, multiplicity and sensitivity results await H1 2027 readout. |
| NCT06641076 | post-1-5 | PENDING | Blinded safety and no-new-signal statement lacks arm-level SAE/discontinuation tables. Full study readout expected H1 2027. |

Every missing factor was given a specific review disposition. Pending readouts and explicitly unreported tables are distinguished from an unsuccessful clinical result. The 203 remaining question gaps mean no sufficient question-specific observation was established in the retrieved source packet. They are **not** asserted to be unavailable everywhere: further targeted publication/SAP/prior-study research may resolve some. No claim of 100% research completeness is made.

## Evidence, discrepancies and retained history

ClinicalTrials.gov API v2 records were retrieved for all 23 NCTs, including all posted arms, denominators, endpoints, analysis details, participant flow, baseline characteristics and adverse-event modules. Registry results exist for 10; absence of registry results does not negate issuer or publication readouts. The original registry and issuer/SEC/FDA retrieval receipts and indexed publication abstracts are in `sources/` and `source-retrieval-audit.json`. HTTP 203 PubMed interstitials and HTTP 403 publisher access are recorded as access limitations, not verified articles. Europe PMC indexed exact-NCT abstracts supplied available published results. The FDA-linked Zanvastro label provided five previously missing assessments.

Material distinctions retained: RISE UP split co-primary/fatigue results; ACTIVATE-KidsT failed borrowing-sensitive primary criterion; APeX-P PK-primary bridging; OASISplus open-label extension versus its distinct parent NCT; IMerge Phase 3 versus Phase 2/QT substudies; COMP006 versus COMP005 follow-up; ENVISION registry CR 76.7% versus publication 191/240; TRANSCEND pivotal/expanded safety denominators; ORIGIN 3 interim/final and registry safety cutoffs. Discrepancies are not silently reconciled.

Original baseline rows, all existing facts and grades, and all original research and score-history events remain. Recalculation appends content-addressed exact-NCT score snapshots with observations, benchmark, uncertainty, source and reason. A registry source revision invalidates current grading readiness until adjudicated; the old grade survives in history.

## Spreadsheet and website

The existing canonical `BOTTOM — ACTIVE` tab was updated in place through connected Google Sheets authorization using the same exact-NCT update plan as `scripts/sync_bottom_clinical_ratings.py`. Local `GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON` was absent. No replacement sheet or tab was created. Eighteen value cells across NCT06081894, NCT04544293, NCT04716231, NCT06445023 and NCT06455202 were updated in M/Q/R/S. A full 843-cell readback confirmed expected values and no unrelated changes. Previous values and all score sources/uncertainties are retained in cell notes; validated-overall column P and archived /30 columns are unchanged. Wrapping was enabled only for the edited cells. `sheets-sync-receipt.json` records the writes. Native visual fit is not claimed solely from API readback.

The existing `/p3-post-data` table retains all 29 canonical active rows, and attaches rating expansion only for an exact-NCT reviewed match. Horizontal five-factor evidence and expandable source/score history are available for those five matches. `/api/p3-post-data-research` filters all public JSON and CSV responses to the active roster. The deliberately retired `/api/bottom-only-completion` and TOP/BOTTOM listing routes remain retired. All 23 research records and exports remain preserved in the repository.

## Repeatable pipeline

```bash
python scripts/bottom_only_evidence_backfill.py --fetch
node new-platform/frontend/scripts/bottom-only-recalculate.cjs
python scripts/sync_bottom_clinical_ratings.py
```

The backfill has no trial-count cap. It validates exact NCT and Phase 3 identity, archives registry revisions and preserves old facts. Numerical ratings use explicit documented reviews and existing anchors; source discovery never auto-assigns a grade. Recalculation exports the original 190-column data, active clinical scorecards, archived metric dispositions, source facts and exact blockers. The Sheets updater uses existing auth and header validation, refuses mismatched NCTs/invalid composites/constrained cells, preserves prior values and notes, and verifies readback. No cancelled workflow was enabled or dispatched.

## Validation and release

See `verification.json` for final test, browser, commit and deployment evidence. A build or screenshot verifies software behavior, not the completeness or truth of a clinical claim.
