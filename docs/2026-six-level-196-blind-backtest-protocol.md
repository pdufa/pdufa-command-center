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

## Level definitions and study scope

The [installed scientific contracts](assessment-installation-levels1-20-20261114.md#levels-16-integration-and-evidence) define L01 as trial identity, L02 as design, L03 as statistics and efficacy, L04 as safety, L05 as indication-specific relevance, and L06 as regulatory readiness. Those contracts produce scientific findings. Mapping their findings to APPROVE, CRL, or ABSTAIN requires a specified prediction rule before evaluating the 2026 cohort.

The owner selected the installed scientific contracts for this backtest. The current scientific runtime emits ABSTAIN because it has no validated FDA decision model. The offline research runner below applies a separate, prespecified mapping from reviewed scientific findings to FDA direction. Record canonical abstentions only for eligible cases with completed evidence reviews.

The installed `SCIENTIFIC_1_3` historical runtime requires a verified exact trial–application–decision date association and an original registry or retained source capture available by cutoff. A newly downloaded historical public version can support a retrospective evidence review when its original availability is established. It cannot be represented as a contemporaneously captured runtime record. The installed L02–L06 review contracts require original source and review chronology and do not expose a unified historical execution path for all six scientific levels.

The branch also retains the following separately scoped experimental gate baseline. Its test results do not establish results for the installed scientific levels.

### Experimental prediction gates
L01: Accepted filing; pivotal primary efficacy; major safety signal; documented FDA regulatory deficiency.
L02: Trial-design validity, prespecified multiplicity, effect size, missing data and statistical robustness.
L03: Safety depth, subgroup consistency, clinical meaningfulness and benefit–risk by indication.
L04: FDA precedent, advisory committee and regulatory correspondence known by cutoff.
L05: CMC, manufacturing/inspection, labeling and operational filing risks known by cutoff.
L06: Proposed integrated evidence-weighted synthesis across L01–L05, with calibration from *prior* data only. The existing Boolean gate baseline does not implement that synthesis or calibration.

## Outcome isolation

Stage prediction workers from an allowlist of code and predecision records. The branch checkout and Git history contain outcome data, so a branch or worktree alone is insufficient for staging. The ledger worker supplies a redacted case manifest and freeze dates. FDA action documents and the outcome key stay with the ledger worker until the evaluation worker has verified the prediction lock. A mechanical hash check cannot establish outcome blindness. Record exposure and exclude affected evaluations from blind accuracy.

## Data schema
event_id,application_number,ticker,drug,indication,pdufa_date,actual_action_date,cutoff_date,level,source_publication_date,source_url,source_excerpt,feature_json,prediction,confidence_pct,abstain_reason,lock_hash,actual_outcome,correct

## Offline scientific workflow

1. Stage an outcome-free reconciled case manifest with event ID, application number, review cycle, drug, indication, verified action date and optional ticker. Stage a separately reviewed JSON package for each event. Each package must attest outcome nonexposure, document the linked pivotal trial set, and retain exact registry revisions and criterion receipts. Distinguish original availability from later verification, retrieval, and review dates.
2. Run `python scripts/blind_scientific_2026.py --events CASES.csv --evidence REVIEWS.json --expected-events N --cutoff-days 30 --output LOCK.json` with the verified event count. Keep the printed whole-lock SHA-256 in an independent record before access to outcomes. The lock binds evidence, scientific findings, and one directional record per event and level.
3. In outcome quarantine, run `python scripts/score_scientific_backtest_2026.py --locked LOCK.json --expected-lock-sha256 DIGEST --outcomes VERIFIED.csv --output SUMMARY.json --summary-csv SUMMARY.csv --results-csv DETAILS.csv`. Each outcome requires an official FDA source and reconciled application, review-cycle and action-date identity. An incomplete or duplicated grid, digest mismatch, ineligible outcome, or differing case set blocks scoring.

The canonical workflow uses the installed phase-first L01 intake and L02–L06 scientific review criteria. The separate research rule abstains at L01 and on design-only supportive evidence at L02. For L03–L06 it requires affirmative support for every criterion across the pivotal trial set before predicting approval. A CRL prediction requires a documented material concern in an explicitly listed criterion and sufficient, noncontradictory level evidence. Unresolved or incomplete evidence yields abstention only after a completed review. The rule has no calibration or confidence percentages.

## November 19 execution status

- The [FDA source reconciliation](2026-fda-action-candidate-reconciliation.md) identifies 322 approval candidates and 39 published Complete Response Letter candidates. The sources use different record keys. Across the timing and CBER batches, 53 reviewed records have source corroboration. PDUFA26-TIMING-033 is one parent-application review cycle. The separate starter-pack filings still need independent goal-date corroboration. The eligible denominator and the requested count of 196 remain unverified.
- The [clinical evidence backlog](../data/backtest/2026-clinical-evidence-backlog.csv) records status for each of the 53 reviewed timing, CBER, archive and letter candidates. The [provisional source research](../data/backtest/2026-provisional-source-research.csv) contains 48 leads for 12 candidates. Forty-one have asserted dates satisfying the predecision chronology check. Seven lack original publication and version dates. The registry index adds five provisional records across four cases with pre-cutoff update dates from the current registry endpoint. These still need pinned historical revisions. There are zero completed evidence packages.
- Search results exposed the evidence researcher to outcome-bearing information for `PDUFA26-TIMING-002`, `PDUFA26-TIMING-004`, `PDUFA26-TIMING-006`, and `PDUFA26-TIMING-021`. Those reviews are ineligible for blind scoring. Potential exposure for PDUFA26-TIMING-009 and PDUFA26-TIMING-010 also blocks those drafts. The evidence backlog signposts the affected records without outcome values.
- There are zero finalized assessments or abstentions at each of L01–L06, zero locked historical predictions against the requested 1,176, and no measurable accuracy or coverage. The [dashboard draft](2026-six-level-backtest-dashboard-draft.md) defines a post-lock import contract.
