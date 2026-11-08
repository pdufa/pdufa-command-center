# RAAS active two-year PDUFA validation: 2024–2025

## Active research policy (effective November 3, 2026)

**Study years:** January 1, 2024–December 31, 2025 inclusive, using the publicly announced original/revised **PDUFA target year**, not the retrospective FDA action year. These are the two most recent *completed calendar years* as of the policy change.

**2024 = training; 2025 = untouched, issuer-disjoint holdout.**
The earlier ten-year 2016–2025 study is now an **archived, manual-only research workflow**; historical FDA and SEC filings already sourced in 2017–2022 remain saved. They do **not** count as cases, holdout issuers, active-year audited outcomes, or RAAS metric calibrations for 2024–2025. Preserve the original 2016–2025 archive for audit/reproducibility.

Active configuration: `new-platform/frontend/data/raas-active-study-config.json`.
Active intake: `new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json`.
Research: `scripts/raas_active_two_year_study.cjs`.
Workflow: **RAAS ACTIVE 2024–2025 two-year PDUFA historical study** in GitHub Actions.
User-facing acceptance gates: `/raas-scan` (2 census years required, instead of 10).
Prior research documentation: `docs/raas-ten-year-pdufa-study.md`.

## Rules retained, not relaxed

- US-listed publicly traded biotech issuer on **each historical entry session**; $300 million–$10 billion **point-in-time** market capitalization in corresponding USD security/common/ADS units. Require SEC shares known by that day, separate raw versus corporate-action-adjusted prices, and independently reconcile splits/dilution.
- Original PDUFA target and Phase 3 readout **publicly known before the entry**. Track every extension/reschedule and FDA actual action (including early approval or early CRL). No lookahead.
- Entries T−90..T−4 calendar days; exits T−3..T−(entry lead−1), 3,828 planned entry/exit combinations per case. Find actual exchange sessions; no fictional weekend closes, no FDA action at/after exit.
- Archived dates in `data/historical_assessed_decisions.csv` are **unverified research leads**, not eligible trades. FDA retrospective decision databases alone omit many CRLs, withdrawn cases, extensions, private updates and delisted issuers. Construct an independently audited outcome denominator for **both** 2024 and 2025.
- 30 distinct issuer training observations (2024) **and 30 distinct nonoverlapping issuer holdout observations (2025)** per candidate window, not 3,828 grid rows mistaken for independent samples. Avoid same-issuer leakage across years.
- Continue preserving uncertainty, liquidity, transaction-cost assumptions, delistings, missing prices, non-US venues, IPO/split rights and prospectively recorded metric inputs. Do not approve a winner solely because source-code tests or Alpaca calls succeeded.

The active 2024–2025 reviewed intake deliberately starts **empty** with both census year audits `NOT_AUDITED`. Existing 2024/2025 retrospective candidate leads can be downloaded via Alpaca SIP as price *research*, but are not point-in-time source-reviewed trading cases. The job publishes adjusted-price research and auditable blockers, not numeric RAAS grades or claimed best window.

## Why this reduces workload, and statistical limitations

This change restricts the date cohort from **10 to 2 calendar years**, reducing scope for original FDA/SEC event auditing and historical price downloads. It does not necessarily reduce collection time by 80% or guarantee statistically significant results. A two-year period is sensitive to 2024–2025 market conditions, unusually scarce outcome categories, FDA policy and issuer financing cycles; 2025 holdout may have fewer than 30 independently eligible issuers. In that case, the correct result is **insufficient evidence**, not reduced statistical controls or invented +10% returns.

## Completing requirements 2 and 3

1. Obtain original 2024 and 2025 FDA/issuer PDUFA announcement snapshots, Phase 3 disclosures, and all approval, CRL, withdrawal and extension outcomes, including moved/deferred targets.
2. Independently audit both yearly event denominators before setting any `FULL_EVENT_CENSUS_AUDITED` status.
3. For each eligible entry session, reconcile original SEC cover shares, offerings, common/ADR share units, corporate actions and **raw historical exchange price**, separately reconcile adjusted return prices against an independent market data source, and censor early decisions.
4. Carry out issuer-disjoint 2024 training vs 2025 holdout comparisons, cost/volatility sensitivity analysis, confidence intervals and no-ahead-of-time-leakage checks.
5. Only after independent validation consider calibrating 30 TOP + 30 BOTTOM metrics. Missing inputs stay missing, never `0` or arbitrary scores.

**All six RAAS installation acceptance gates remain in force.** Reducing the study period changes the historical census requirement to two years; it does not declare any new gate complete.
