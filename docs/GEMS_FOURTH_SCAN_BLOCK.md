# GEMS — fourth SCANS dashboard block

The SCANS dashboard shows four **blocks**, in order:

1. **#2 PIPELINE** — existing clinical collector
2. **#3 PRE3** — existing clinical collector
3. **#4 POST3** — existing clinical collector
4. **BLOCK 4 — GEMS** — independent GEM research scan (workflow scan ID `GEM`, **not** `4`)

The GEMS panel already contains three independently scored **Phase 3**, **Post-Financing**, and **PDUFA** research stage views. A fourth dashboard block does not add a fourth investment score.

## Run options

The same PIN-gated controls operate on each block:

- **VERIFY SAVED SOURCES / VERIFY ALL**: GEMS recomputes source readiness using saved files, **without fresh collection**. Selecting a clinical target runs the existing three-archive verification bundle; it is not a single-file verification.
- **REVERIFY SELECTED / REVERIFY PARTIAL**: GEMS refreshes recent ClinicalTrials.gov posted results then audits saved sources; clinical collectors use their existing incremental checks.
- **RESCAN SELECTED / RESCAN ALL**: GEMS backfills all accessible registry Phase 3 result pages then audits; clinical 2/3/4 use their existing collector. All requests are asynchronous GitHub Actions jobs; dispatch acceptance is not verified completion.

The dedicated `gem-research-quality.yml` workflow is scheduled daily and may be run manually. The DST-aware **8:30 PM Pacific** nightly launcher now includes a GEMS dispatch after POST3; this handoff is independent of the clinical report publisher. The **6 AM Pacific** snapshot displays a separate GEM status *only if a dated fourth-block result was published since the preceding night*. Otherwise it shows pending/stale, not invented new findings.

## Results and notifications

Each GEMS execution sends Gmail **START** and **END** notifications using the same `PDUFA_GMAIL_USER`, `PDUFA_GMAIL_APP_PASSWORD` and `PDUFA_ALERT_EMAIL` GitHub Actions secrets as the clinical scans. A submission is not proof of inbox delivery; SMTP failure is recorded and the workflow fails closed. A missing START message stops its registry collector. Full audit artifacts (with notice receipts) remain in the GEMS workflow for up to 90 days.

The repository publishes `data/gem_scan_block_report.json`. The fourth row in NIGHTLY SCAN REPORT shows source execution, study/new-result counts where actually reported, errors, run ID, and *PARTIAL* or *FAILED* source status. The details panel shows GEMS stage research ranks, freshness issues, current SEC and quote status, missing prerequisites, and JSON export. Existing detailed GEM stage tabs continue to offer CSV downloads.

## Absolute safety rules

No source label, Phase 3 score, registry posting, or second-financing announcement is a trade signal.

**WATCH ONLY** until two **distinct** financings after the verified successful Phase 3 release have **actually closed**, with exact-program, dated, independently reviewed SEC primary filings. The SEC recheck, dilution, clinical efficacy/safety, market base and volume, and PDUFA date requirements must also pass. If the live SEC source is blocked or stale, the Post-Financing and PDUFA GEM rankings remain withheld. Exit remains planned for **PDUFA minus 3 calendar days**. Nothing in this block places broker orders.

A successful workflow or a complete registry collection does **not** certify all required sources, historical trading alpha, price appreciation, or FDA approval.

## Finding the few fully qualified GEMS

The GEMS detail view defaults to **ALL MANDATORY ENTRY GATES PASSED**. This is
the **intersection** of all three source-verified GEM stage qualifications,
Stage 1 GREEN, two separate post-readout financings that have actually closed,
fresh source/SEC checks, dilution/clinical/market/PDUFA gates, and the entry
window extending beyond PDUFA minus three days. It exports a ranked CSV of only
these fully screened **manual entry-review** candidates.

Other tabs remain available for Phase 3 leads and partially qualified
research candidates. A Phase 3 rank, a quoted score of 100/100, or a second
financing announcement does NOT put a stock into the strict shortlist.
The fourth-block audit displays the exact strict-shortlist count, including 0
when no companies pass. The system does not claim proven return alpha or place
trades.
