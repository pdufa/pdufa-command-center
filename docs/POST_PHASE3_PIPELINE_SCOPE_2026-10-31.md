# Active research scope: Post–Phase 3 PIPELINE only
Effective: 2026-10-31
Status: USER-DIRECTED SCOPE CHANGE — NOT YET DEPLOYED OR ACCEPTANCE-TESTED

## Decision
Do not use GEM JR, GEM, or WT as qualification gates, progression stages, or destinations in the new research and approval-screening funnel. Future development prioritizes ONE Post–Phase 3 PIPELINE. Preserve historical GEM/GEM JR/WT data, tests, and prior FS/FA configurations for reversibility; do not delete them or represent them as current approval qualifications. Changes to scheduled workflows and production navigation require distinct code changes and verification.

## Hard universe
- U.S.-listed, presently publicly traded issuer; exclude retired/delisted predecessor tickers.
- Current, evidence-dated market cap USD $300,000,000 to $10,000,000,000, inclusive.
- Post–Phase 3 readout evidence: either a completed Phase 3 human interventional study in the source registry OR a verifiable final pivotal Phase 3 readout for the exact program (including ACTIVE_NOT_RECRUITING studies with ongoing follow-up). Link sponsor/rights holder, drug, indication, NCT ID(s), source and timestamps. A merely planned readout is not post–Phase 3.
- Keep all completed or published-final-readout Phase 3 results in the research inventory, including negative or unsuccessful; do NOT confuse trial completion or a posted result with efficacy success.
- Separate CURRENT/FUTURE review candidates from RESOLVED/HISTORICAL, DISCONTINUED and MISSING-EVIDENCE queues. Missing source data is REVIEW, never presumed failure.
- Consolidate multiple NCT records under a canonical drug–indication–FDA application program for candidate counting, preserving trial-level source records.
- No artificial PDUFA-day ceiling; retain candidates awaiting FDA submission/acceptance.

## Starting census, not final approval count
- 11,623 saved trial inventory records in October 31 clinical report (different source scope).
- 741 all-years Phase 3 trial NCTs in $300M–$10B market-cap screen, verified census snapshot dated October 26, 2026.
- 375 of those NCTs marked COMPLETED across 76 tickers, as counted October 31. This is only the registry-completed starting subset; additional trials with verifiable Phase 3 final readouts but non-COMPLETED registry statuses must be found, and the full post-readout count is unverified.
- These are historical-and-current records; no claim that 375 passed efficacy, have FDA acceptance, or are prospective approvals.

## One PIPELINE approval-research funnel
1. Public listing, market cap, exact identity and Phase 3 completion OR independently verified final pivotal readout.
2. Adjudicate Phase 3 primary endpoints, magnitude of efficacy, safety and evidence completeness.
3. Verify current development continuity and NDA/BLA submission/acceptance, FDA dates, CRLs, extensions, withdrawals, or earlier approvals by exact application.
4. Evaluate FDA approval readiness (clinical benefit–risk, statistical robustness, CMC/manufacturing, regulatory concerns). Publish PASS/CRL/EXTENSION/ABSTAIN only with evidence and a clear reason; never present uncalibrated odds as factual probabilities.
5. Evaluate patient population and 20 complementary commercial-benefit angles (unmet need, comparative outcomes, price, reimbursement, access, competition, uptake, peak sales, exclusivity, licensing, financial strength, valuation). Keep commercial and trading scores separate from clinical/regulatory approval readiness.
6. Produce one ranked, auditable Pipeline dossier with collapsible source/reason sections. Distinguish current PDUFA candidates from longer-term post-Phase 3 programs.

## Validation required before claiming operational
- Remove/retire GEM JR and GEM navigation, qualifiers and scan jobs from active production *without* stopping the underlying Phase 3 results collector used by this Pipeline.
- Publish a tested Post–Phase 3-only count and trial/program breakdown. Keep date/market-cap source freshness checks.
- Confirm relevant scheduled workflows are no longer running GEM qualification, and test daily data/website against the new schema.
- Do not claim the change is live, nor that GEM scans were canceled operationally, until the actual production workflow and navigation have been checked.

Source of census: data/phase3_all_years_300m_10b_trials.csv; data/phase3_all_years_300m_10b_status.json; data/nightly_scan_report.json.
