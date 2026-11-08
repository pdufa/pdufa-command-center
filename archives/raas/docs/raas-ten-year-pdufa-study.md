# RAAS PDUFA 2016–2025 Alpaca historical-price study

## Status

## Observed first production-branch run — November 2, 2026 Pacific

The Actions run at https://github.com/pdufa/pdufa-command-center/actions/runs/41576836131
successfully pulled **8,719** adjusted SIP daily price rows across **125** archive
candidate events. The original archive contained **126** events: 20 in 2020,
24 in 2021, 22 in 2022, 24 in 2023, 26 in 2024, 10 in 2025, and **zero**
in 2016–2019. There are **zero source-reviewed investment cases** and
**zero eligible PDUFA price-return windows**; no optimum can be declared.

The one venue exception is ZEAL / Zealand Pharma's December 22, 2024
glepaglutide event. The issuer states its US ADR program was delisted in
August 2022 and the stock traded on Nasdaq Copenhagen in 2024. Its FDA
CRL was publicly announced December 19, 2024, before the target date.
See new-platform/frontend/data/raas-alpaca-venue-exceptions.json
for issuer source links and details. This publicly traded issuer remains a
research **coverage gap** requiring a separate non-US price vendor if the
study retains globally traded securities. Do not call it an Alpaca
authentication problem, use a US security's prices as a substitute, or
silently drop it from the required population.

**Research infrastructure only. No 10-year optimized entry/exit claim is authorized yet.**

The historical FDA-decision archive in data/historical_assessed_decisions.csv
provides **discovery candidates**, not verified point-in-time PDUFA event announcements
or verified $300M–$10B market-cap trading opportunities. Its available years may
not cover 2016–2019; year-by-year completeness must be audited independently.
The reviewed-event intake starts empty deliberately. Existing eight retrospective
Alpaca cases in raas_alpaca_historical_price_study.cjs remain separate and may
not be relabeled as an exhaustive ten-year PDUFA study.

## Executing

GitHub Actions > "RAAS Alpaca 2016-2025 source-gated PDUFA price research"
> Run workflow on main. Download artifact "raas-ten-year-pdufa-research".

This workflow only reads secrets from GitHub Actions on dispatch/push, not on PR.
Supported secrets: APCA_API_KEY_ID + APCA_API_SECRET_KEY (or
ALPACA_API_KEY_ID + ALPACA_SECRET_KEY). Never print keys. Data feed:
Alpaca single-symbol historical 1Day SIP bars, adjustment=all, ticker asof
date set to the scheduled event date, historical range scheduled T−100..T.
The output stores price sessions and explicitly labels sources.

A green workflow check proves the code ran, NOT that the PDUFA cohort was
source-verified, that all tickers were retrievable, or that a strategy worked.
Inspect the JSON status, per-year candidate counts, and source failures.

## Inputs to unlock verified trading-window research

File: new-platform/frontend/data/raas-ten-year-pdufa-intake.json

One record per **issuer + drug + indication + PDUFA event**. Required:
- caseId, programId, ticker, and nctIds (one or more exact NCT IDs)
- pdufaDate, pdufaFirstPublicDate, pdufaSourceUrl: issuer/FDA original
  target announcement available by entry. Historical reschedules need
  point-in-time target histories; do not substitute a later-known date.
- phase3ReadoutDate, phase3SourceUrl: first public Phase 3 result.
- actualFDAActionDate, actualFDAActionSourceUrl: actual action used **only**
  for censoring early decisions, never as an entry-time feature.
- reviewStatus = "SOURCE_REVIEWED" after independent evidence audit.
- historicalMarketCaps: an array of exact exchange-session caps. Each object:
  session, usdMillions, sourceUrl, sharesSourcePublishedAt, sharesSourceUrl.
  Shares/ADS conversion must match the security, class, and date. A source
  published after entry cannot establish point-in-time share counts. Caps
  for *another* trading day, current caps, and unsupported share estimates
  are all rejected. Independent corporate-action and execution audits remain.
- yearAudits: one per year 2016...2025. Mark
  status="FULL_EVENT_CENSUS_AUDITED" with a verifiable sourceUrl only when
  **every** relevant listed-company PDUFA event for that year was screened
  for inclusion/exclusion (including delisted/acquired securities, name
  changes, withdrawn applications, CRLs, early actions, and rejected records).
  Otherwise keep NOT_AUDITED. Do not mark a year complete from a partial
  FDA approval list or only today’s surviving listed companies.

These are evidence collection requirements; the engine cannot infer them from
a current Phase 3 census or current market-cap file.

## Predeclared design

- Calendar years: Jan 1, 2016 through Dec 31, 2025 inclusive.
- Universe: US-listed public companies, Phase 3 readout public at historical
  entry, accepted FDA PDUFA target publicly known before entry, historic
  market cap **$300 million to $10 billion at each exact entry session**.
- Entries: calendar-day leads T−90, T−89 ... T−4.
- Exits: calendar-day leads T−3 through T−(entryLead−1).
- Execution approximation: entry = first actual trading session on/after the
  calendar target; exit = last on/before the calendar target. The date
  substitution is constrained to four days; missing bars are not interpolated.
  Reject same-session or reversed entry/exit.
- Censor exit on or after earlier-than-target FDA action. Entry must be
  after both the first public Phase 3 readout and the first publicly known
  PDUFA target.
- Prices: adjusted 1Day close-to-close return, minus assumed **one percentage
  point** round-trip friction. This is a research sensitivity assumption,
  not an estimate of historic actual spread/slippage or trade fills.
- Independency: at most one event per issuer per grid cell/split. Train on
  2016–2022 issuers not present in the 2023–2025 holdout; do not choose
  candidates based on their 2023–2025 returns.
- Require complete audited ten-year event census AND >=30 distinct issuers
  each for train and holdout for **any** winner to be declared. Select entry/
  exit by highest training median net return and evaluate that *fixed* window
  on the issuer-disjoint holdout. The 30-issuer floor is not enough by
  itself to validate predictive performance; report uncertainty and
  additional era/sector bootstrap tests before operational use.

All research remains non-validated for RAAS predictive ratings; the workflow
does not modify RAAS scores, source-grade approval, or user-facing recommendations.

## Interpretation

- discoveryCandidates: archive event dates for screening, may be unverified.
- historicalDailyBarsCollected and historicalPriceRows: Alpaca retrieved
  *observations*, not a verified PDUFA cohort.
- reviewedEvents: source-reviewed intake objects, still subject to market-cap
  and trading-date eligibility at each grid entry.
- eligibleWindowRows: point-in-time arithmetic candidates; not audited fills.
- selectedWindow.status: BLOCKED unless full year census and sample gates pass.
- All sample counts must use issuers/programs, not number of Phase 3 NCT IDs
  or grid rows. Multiple PDUFA targets for the same product must be reviewed
  before considering independent events.

## Remaining substantive work

1. Build and independently review 2016–2025 event universe with original
   date-of-publication evidence. Explicitly include unsuccessful outcomes.
2. Construct historical per-entry market cap series from point-in-time shares,
   pricing and ADS/class conversion; independently audit corporate actions.
3. Cross-check delistings, tickers, early actions, censored cases, price
   anomalies, filings and changes to target dates.
4. Review selection bias, transaction-cost assumptions, time/sector controls,
   uncertainty, walk-forward accuracy and survivorship. Only then consider
   publishing an optimized strategy into RAAS or the production dashboard.
