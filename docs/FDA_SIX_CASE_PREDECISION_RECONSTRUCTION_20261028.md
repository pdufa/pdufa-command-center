# Six-case pre-decision reconstruction milestone — 2026-10-28

Continues PR #522 from d6cf908. This is research infrastructure and evidence reconstruction, not independent prediction validation or a deployed dashboard change.

## Findings

| Case | Application | Legacy target | FDA action | Conservative research cutoff |
| --- | --- | --- | --- | --- |
| NVAX | BLA125817 | 2025-04-01 | 2025-05-16 | 2025-03-31 |
| UNCY | NDA218607 | 2025-06-28 | 2025-06-27 | 2025-06-26 |
| TNXP | NDA219428 | 2025-08-15 | 2025-08-15 | 2025-08-14 |
| BCRX | NDA219776 | 2025-12-12 | 2025-12-11 | 2025-12-10 |
| CORT | NDA219398 | 2025-12-30 | 2025-12-30 | 2025-12-29 |
| VNDA | NDA220152 | 2025-12-30 | 2025-12-30 | 2025-12-29 |

These cutoffs are conservative reconstruction bounds, not recovered original prediction timestamps. All six original prediction cutoffs remain unverified.

FDA action evidence is identified for six cases. Original action-document content is recorded for four: NVAX, TNXP, BCRX and VNDA. The original UNCY 2025 CRL was located, but partial text extraction leaves first-page visual verification outstanding. CORT has a corrected January 2026 CRL retaining the December 2025 action; the original letter remains unretrieved. No original FDA PDF bytes or document hashes have been retained in this milestone. A directory year or printed action date is not a proven public availability timestamp.

The source packet contains 16 observations: seven pre-cutoff research observations from six distinct SEC filings, seven outcome-only exclusions, one late NVAX source excluded, and one BCRX source quarantined because its filing availability was not verified. SEC filing-index dates are checked against the exact accession directory. None is promoted to a frozen prediction feature or independently certified assessment.

Substantive findings include UNCY's pre-decision manufacturing deficiencies and CORT's distinction between improvement from baseline and a nonsignificant between-group systolic blood-pressure comparison. TNXP's reported RESILIENT efficacy, BCRX's formulation-related review extension, NVAX's development context and VNDA's motion-sickness application are recorded with supporting/opposing factors. Different indications, formulations, EUA/BLA paths and review cycles remain separate. Related historical cases are research leads, not adjudicated matched comparators.

## Recovered archive chronology

Downloaded model and prediction archive bytes were hashed locally. The model digest is `03c1820bd36a096515a974d1b3be9bb3914eaf109529010caa940a02e08178b7`; the two prediction CSV digests are recorded in `research/evidence/2025_holdout_archive_provenance_audit.json`. All six exact event keys and legacy numeric predictions match the appropriate archive within a 1e-12 CSV roundtrip tolerance. The unrelated LEVEL17H six-case lock was not substituted.

The recovered model freeze and both archive locks date to October 4, 2026, after every action above. Prediction generation timestamps and original 2025 feature freezes remain unverified. The model's training filename refers to 2026; the underlying training rows have not been independently audited. Therefore **zero of these six cases currently qualifies for defensible chronological out-of-sample validation**. Archive hashes identify files, not FDA evidence quality or accuracy. Raw private archive files are not published.

## Implementation and verification

The reconstruction auditor rejects malformed dates, duplicate events/JSON keys, unlinked action dates or applications, mismatched lock memberships, unsupported source availability and self-certified scores. A larger lock cohort is permitted only when the exact event occurs once. Post-cutoff model and lock chronology creates explicit blockers. FDA outcomes never enter pre-decision features.

The read-only verification queue joins the existing 146 history records to six reconstructions and the existing 40-question, eight-layer, 20-depth SCIENCE catalog. Independently certified SCIENCE assessments: **0/40**; completed investigation depths: **0/20**. OUTCOME and MAIN research results abstain with `INSUFFICIENT_EVIDENCE`, null probabilities and null prediction/model validation versions. Supporting/opposing factors, uncertainties and missing requirements remain explicit. This does not wire a new live dashboard or certify all requested scientific investigation.

Local relevant research regressions: **79 passed, 20 subtests passed**. Existing backend suite: **994 passed, seven warnings**. Tests verify engineering behavior; synthetic fixtures are not prediction-accuracy evidence. GitHub Actions results are reported on PR #522 after push.

The legacy history file, list memberships, original FS/FA associations, scanners and live schedules are unchanged. No merge, deployment, production data writes, spreadsheet writes or trading occurred.

## Remaining requirements

Retain original FDA document bytes and public availability provenance; visually verify UNCY's first page and retrieve CORT's original CRL. Reconstruct complete protocols, amendments, statistical plans, efficacy and adverse-event tables, manufacturing/inspection evidence, and independently adjudicated historical comparators. Recover genuine pre-action prediction/feature/model freezes or construct an explicitly retrospective, training-chronology-safe experiment; independently verify all training rows and program-disjoint cohort membership before evaluation.

Independently backtested cases: **0**. Accuracy, Brier score, calibration, discrimination, confidence intervals and prediction coverage remain **unmeasured**. Restricted FDA network access and hosted database external-IP access prevent some direct checks; no network or database settings were changed. Deployment metadata inspection found Render live at 2032458f, not this development increment; database readiness is not newly verified.
