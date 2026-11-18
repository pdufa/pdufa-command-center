# Six-level blind historical FDA backtest — 2026

Requested universe: 196 FDA PDUFA cases, January 1–November 18, 2026, unrestricted market capitalization.
Status: TARGET COUNT UNVERIFIED. Do not manufacture 196 event rows. Eligibility and deduplication must be reconciled from source evidence before scoring.

## Immutable workflow
1. Build an event ledger with application number, drug, indication, sponsor, original PDUFA date, actual action date, source URLs, and distinct application/action key. Store outcomes in a separate inaccessible file.
2. For each event, freeze a predecision evidence cutoff (default 30 days before actual decision; additionally report 1-day and 7-day sensitivity). Historical document publication date must be <= cutoff. Reject later updates, even if they describe earlier results, unless archived contemporaneous copy exists.
3. Independently score six levels in sequence, recording YES/NO/UNKNOWN evidence flags, provenance URL, source publication timestamp, cutoff, reviewer, and prediction. Missing required evidence => ABSTAIN; never infer NO from missing.
4. Lock each level's predictions, feature snapshot and SHA256 before outcomes are joined. Never retune a level on the same test outcomes and report the result as out-of-sample.
5. Score APPROVE versus CRL only for verified FDA actions; report abstentions, coverage, correct, incorrect, accuracy on answered cases, and confusion matrix separately for each level. Report denominator and 95% Wilson interval. Other outcomes (withdrawn, delayed, pending, tentative) require explicit exclusion/alternate category, not forced into APPROVE/CRL.
6. Preserve L01–L06 independent predictions and source evidence. No production deployment or merge without authorization.

## Level definitions (proposed; require approval if existing repository defines levels differently)
L01: Accepted filing; pivotal primary efficacy; major safety signal; documented FDA regulatory deficiency.
L02: Trial-design validity, prespecified multiplicity, effect size, missing data and statistical robustness.
L03: Safety depth, subgroup consistency, clinical meaningfulness and benefit–risk by indication.
L04: FDA precedent, advisory committee and regulatory correspondence known by cutoff.
L05: CMC, manufacturing/inspection, labeling and operational filing risks known by cutoff.
L06: Integrated evidence-weighted synthesis across L01–L05, with calibration from *prior* data only.

## Data schema
event_id,application_number,ticker,drug,indication,pdufa_date,actual_action_date,cutoff_date,level,source_publication_date,source_url,source_excerpt,feature_json,prediction,confidence_pct,abstain_reason,lock_hash,actual_outcome,correct

## Current honest state
196 requested; 0/196 verified as complete eligible historical event manifest; 0/1176 level-specific blind predictions locked; 0 verified accuracy rates.
FDA 2026 novel approvals are a subset of total FDA actions. A third-party archive reports 178 decided 2026 events on Nov 18; its definition and deduplication need reconciliation. Neither source validates 196.
