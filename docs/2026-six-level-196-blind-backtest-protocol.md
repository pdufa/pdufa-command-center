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

The owner selected the installed scientific contracts for this backtest. The current scientific runtime emits ABSTAIN because it has no validated FDA decision model. A directional backtest requires a prespecified mapping from scientific findings to FDA decisions. Record canonical abstentions only for eligible cases with completed evidence reviews.

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

## November 19 execution status

- The [FDA source reconciliation](2026-fda-action-candidate-reconciliation.md) identifies 322 approval candidates and 39 published Complete Response Letter candidates. The sources use different record keys. Across the timing and CBER batches, 43 of 44 reviewed records have source corroboration. PDUFA26-TIMING-033 still needs review-cycle reconciliation. The eligible denominator and the requested count of 196 remain unverified.
- The [clinical evidence backlog](../data/backtest/2026-clinical-evidence-backlog.csv) records status for each of the 44 reviewed timing and CBER candidates. The [provisional source research](../data/backtest/2026-provisional-source-research.csv) contains 48 leads for 12 candidates. Forty-one have asserted dates satisfying the predecision chronology check. Seven lack original publication and version dates. These are leads for source review, with no completed evidence packages.
- Search results exposed the evidence researcher to outcome-bearing information for `PDUFA26-TIMING-002`, `PDUFA26-TIMING-004`, and `PDUFA26-TIMING-006`. Those reviews are ineligible for blind scoring. The evidence backlog signposts the affected records without outcome values.
- There are zero finalized assessments or abstentions at each of L01–L06, zero locked historical predictions against the requested 1,176, and no measurable accuracy or coverage. The [dashboard draft](2026-six-level-backtest-dashboard-draft.md) defines a post-lock import contract.
