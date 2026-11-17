# Levels 7–20 scientific acceptance and prospective validation gate

Status: **NOT ACCEPTED**. This is a review checklist, not evidence that an FDA outcome can be predicted. Applies only to the isolated draft branch; no production integration or changes to Levels 1–6.

## Global prerequisites (all fourteen levels)
- [ ] Freeze a versioned, immutable input snapshot per trial/application and decision cutoff; record retrieval time, source URL, publication time, evidence hash, trial NCT ID, application identifier, indication, and reviewer identity.
- [ ] Verify source authenticity, trial-to-application linkage, indication and population alignment; independently adjudicate conflicts and unavailable documents.
- [ ] Prove no information published after the prediction cutoff enters features, prompts, labels, tuning, or manual adjudication. Include amended, backdated, and late-indexed records in leakage tests.
- [ ] Pre-register scoring rubrics, abstention criteria, model versions, thresholds, outcome definitions, and evaluation periods before looking at held-out FDA decisions.
- [ ] Separate training, model selection, calibration, and final evaluation chronologically, grouping repeated submissions and related sponsors to prevent correlated leakage.
- [ ] Report denominators, missingness, abstentions, Brier score, calibration curves, discrimination, decision-level confusion matrix, uncertainty intervals, and performance by indication, therapeutic area, review pathway, and time period.
- [ ] Independently review clinical and regulatory assumptions, adverse examples, conflicts, and evidence provenance. Never treat a passed schema/contract test as scientific validation.
- [ ] Obtain explicit owner approval for integration; preserve current production behavior, historical versions, and rollback capability.

## Per-level acceptance evidence
| Level | Domain | Evidence and challenge required before scientific signoff |
|---|---|---|
| 7 | Population/subgroups | Pre-specified subgroup definitions, multiplicity, interaction estimates, representativeness, and external validity |
| 8 | Safety | Exposure-adjusted event rates, seriousness, causality, duration, discontinuations, and rare-event uncertainty |
| 9 | Benefit–risk | Clinically meaningful effect sizes, harms, comparators, sensitivity analyses, and explicit tradeoff rationale |
| 10 | Dossier | Source-complete filing dossier, version chronology, missing modules, and reconciliation across source documents |
| 11 | Unmet need | Standard-of-care at cutoff, competing treatments, population burden, and non-circular unmet-need justification |
| 12 | Replication | Independent studies, endpoint consistency, heterogeneity, and reproducibility of effect |
| 13 | Filing | Submission type, acceptance/filing evidence, review clock, and authoritative regulatory dates |
| 14 | Pathway | Correct pathway designation, legal eligibility, evidentiary implications, and contemporaneous FDA guidance |
| 15 | Precedent | Matched FDA precedents, indication comparability, temporal validity, and negative precedents |
| 16 | Manufacturing | Inspection and CMC evidence, site linkage, remediation timing, and unresolved quality risks |
| 17 | Disclosures | Dated company/regulator disclosures, contradictions, source quality, and selective-reporting risk |
| 18 | Challenge | Independent adversarial review, alternative explanations, robustness, and documented disagreements |
| 19 | Prospective | Pre-cutoff frozen predictions, tamper-evident version history, outcome embargo, and blind scoring |
| 20 | Outcome | Official FDA decision source, exact application/indication match, outcome adjudication, and unbiased performance accounting |

## Release decision
A reviewer must record PASS/FAIL/NOT_EVALUATED for each prerequisite and level, evidence references, the date, and unresolved risks. **Any missing or failed scientific gate blocks calibrated scores and approval/rejection predictions.** Isolated validators must continue to return NOT_VERIFIED, null scientific scores, and ABSTAIN until separately approved and engineered. CI success alone does not authorize activation.
