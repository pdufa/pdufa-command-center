# 2026 real-company PDUFA price pilot (through October 17, 2026)

**Not the 54-scenario GEM backtest. No validated GEM BUY signals or strategy win rate are claimed.**

This report uses *actual historical stock closing prices* to illustrate how a
simple, **calendar-based hypothetical entry** 30 calendar days before the
originally published PDUFA target would fare with a 14-day versus 3-day
pre-deadline exit. For each boundary, use the last regular-session close
on/before the target calendar date. Model 10 basis points of slippage on
both entry and exit: net return = (exit close * 0.999 /
(entry close * 1.001) - 1) * 100. Fees, taxes, borrowing and halts are excluded.
No amounts below represent a trade that the actual GEM entry scanner emitted.

## Three real stocks, original PDUFA goals

| Symbol | Original goal (source) | T-30 entry close | T-14 exit close | Net return | T-3 exit close | Net return | Finding |
|---|---|---|---|---:|---|---:|---|
| CING | 2026-05-31 | 2026-05-01 $5.37 | 2026-05-15 $4.57 | -15.07% | 2026-05-28 $4.34 | -19.34% | Earlier was less costly |
| ACHV | 2026-06-20 | 2026-05-21 $4.60 | 2026-06-05 $5.13 | +11.30% | 2026-06-17 $5.36 | +16.29% | Later earned more |
| UNCY | 2026-06-29 (company May 2026 update) | 2026-05-29 $7.38 | 2026-06-15 $7.12 | -3.72% | 2026-06-26 $7.13 | -3.58% | Roughly equivalent losses |

Sources for original goal/action dates:
- CING original target May 31: https://www.sec.gov/Archives/edgar/data/1862150/000149315225017931/ex99-1.htm
- CING CRL issued June 1, announced June 2: https://www.cingulate.com/news-releases/news-release-details/cingulate-receives-complete-response-letter-fda-ctx-1301
- ACHV June 20 PDUFA, company confirmed CRL June 22:
  https://ir.achievelifesciences.com/news-events/press-releases/detail/264/achieve-life-sciences-receives-complete-response-letter-from-fda-for-cytisinicline-nda
- UNCY company May 12 confirmation of June 29 PDUFA:
  https://ir.unicycive.com/news/detail/122/unicycive-therapeutics-announces-first-quarter-2026
- UNCY CRL reported June 30:
  https://www.globenewswire.com/news-release/2026/06/30/3319541/0/en/unicycive-therapeutics-receives-complete-response-letter-from-fda-regarding-resubmitted-oxylanthanum-carbonate-olc-new-drug-application-nda.html

Historical adjusted prices with dated closes:
- https://www.quiverquant.com/stock/CING/historical-prices/
- https://www.quiverquant.com/stock/ACHV/historical-prices/
- https://www.quiverquant.com/stock/UNCY/historical-prices/

**Source date correction:** June 2 for CING is its press-announcement date,
NOT the original May 31 PDUFA target. An early exploratory calculation
incorrectly used June 2 and has been superseded here. Every future event
should retain original public-goal date, modifications and the separate
actual FDA action date.

## SRRK: a real 20-day SMA exit-signal replay

SRRK original goal **September 30, 2026**, FDA approved **September 11**,
so T-14 and T-3 scheduled exits would be **AFTER FDA action** and cannot
be counted as valid predecision trading outcomes.

Using actual continuous daily closes July 20–September 10, 2026:
- August 26 closing-price peak $60.04.
- September 9 close $54.62, SMA20 about $56.00 (first below).
- September 10 close $55.67, SMA20 about $56.10 (second below).
- The current code's **two closes below SMA20** warning appeared after the
  September 10 close, implying a hypothetical next-open exit **September 11
  at $55.67**, assuming FDA news had not already been made public before
  that fill.
- The hypothetical September 11 open is **7.28% below the August 26 peak**
  *before trading frictions*. A percentage below the maximum is an
  after-the-fact price capture diagnostic, not a tradable high exit.
- The full 2026 GEM buy signal was **NOT reproduced**: entry eligibility,
  financing as-of disclosures and earlier daily-bar history are not yet
  fully audited.
- The August 26 late breakout would also FAIL the experimental 8% stop-risk
  check if executed at August 27 open: previous 10-day low $51.50,
  ATR14 ≈ $2.45, initial stop ≈ $50.89 versus next open $60.00,
  **15.19% downside stop distance**, even before 50-day trend warmup.

Sources:
- https://www.quiverquant.com/stock/SRRK/historical-prices/
- https://investors.scholarrock.com/news-releases/news-release-details/scholar-rock-reports-first-quarter-2026-financial-results-and
- https://www.pdufa.bio/fda-decision/SRRK-2026-09-11

## BFRI: early FDA action

BFRI goal Sep 28, FDA approval Sep 14, 2026. The calendar exit at T-14
**coincides with the action announcement** and T-3 would be **too late**:
neither can be counted as a clean pre-FDA exit. BFRI actual close was
$1.59 Aug 28 and $1.55 Sep 11 (~-2.71% including per-leg slippage),
but this is descriptive only, not a GEM trade.
- https://stockanalysis.com/stocks/bfri/history/
- https://www.globenewswire.com/news-release/2026/09/14/3361199/0/en/biofrontera-announces-fda-approval-of-ameluz-red-light-pdt-for-the-treatment-of-superficial-basal-cell-carcinoma.html

## What we can and cannot conclude

**Observed:** Exit timing interacts with the price path; a fixed late exit
can produce larger losses or greater gains, depending on the stock.
Actual FDA action dates can preempt a scheduled cutoff. The SMA20
warning did not identify the maximum SRRK close, but would have
responded to subsequent deterioration.

**Not observed:** No actual audited GEM full-grid entry-to-exit trades,
GEM win rate, ideal entry-score threshold, optimal plateau rule, or
2026-vs-2025 validation. Entries above are chosen calendar anchors,
not our coded breakout/bottom signals. This is a tiny convenience sample
of companies and prices, not a complete 2026 trading universe.
Unknown clinical and two-completed-financing benchmarks disqualify
any stock from a verified GEM buy simulation until first-public filings
are checked. Keep the $300M–$10B cap **OFF** in this 2026 run.

**Next necessary data:** point-in-time first and second financing source
filings, full verified split-adjusted OHLCV series, PDUFA original goal and
all changes, clinical program/NCT and early FDA action timestamps.

## Expanded June-August 2026 study: seven more real stocks

Underlying per-stock dates, observed close prices, return calculations,
historical price sources, original PDUFA sources and exclusion flags are
in data/2026_real_company_calendar_price_pilot_additional.csv.

| Stock | Original goal | Entry close | T-14 net return | T-3 descriptive return | Late-exit status |
|---|---|---:|---:|---:|---|
| ARQT | June 29 | $21.46 | +18.96% | +25.56% | clean |
| VRDN | June 30 | $17.62 | -9.49% | +1.39% | FDA approval June 26: same-day action, exclude T-3 |
| LNTH | June 29 | $99.30 | +5.20% | +10.35% | CRL announced June 26 at 4:01 PM ET; review timing |
| VERA | July 7 | $32.29 | +18.07% | +27.34% | clean |
| CELC | July 17 | $88.05 | +22.36% | +25.87% | early FDA approval July 14, exclude T-3 |
| REPL | August 2 | $11.58 | -11.83% | -53.37% | July 30 had no trading-bar row; fallback July 29 before AdCom |
| MRNA | August 5 | $81.80 | -29.15% | -33.12% | clean |

All comparisons: buy at last available close on/before T-30, sell at
last available close on/before T-14/T-3, 0.1% hypothetical price
slippage per leg. There are no actual GEM historical-score buy fills.

With three earlier calendar cases (CING, ACHV, UNCY), four clean new
cases (ARQT, VERA, REPL, MRNA) form a seven-stock **convenience** cohort
where both scheduled exits precede the known FDA action date. Their
mean T-14 return is -1.63% versus -5.75% T-3, with 3 winners out
of 7 under each exit choice. This is NOT an optimized policy: much
of the mean gap is caused by REPL's very large late-window loss.
VRDN, LNTH, CELC need separate early-action or same-day time review.
These rows do not yet establish Phase3/two-financing source verification,
fully adjusted historical OHLCV from Alpaca, or tradable GEM entries.

Important original-goal corrections: VRDN was June 30 (not June 26
FDA approval), and REPL was August 2 (not August 6 FDA approval).
Market-cap requirement remains OFF for the 2026 study.

## Two additional issuer-date corrections and stock comparisons

| Stock | Original FDA goal | Entry close T-30 | T-14 net return | T-3 descriptive net return | Treatment |
|---|---|---:|---:|---:|---|
| OTLK | July 29 | $1.69 (June 29) | -7.88% (July 15) | -16.73% (July 24) | FDA approval July 24 on T-3 closing date: exclude as unverified pre-action |
| TLX | Sept 11 | $11.97 (Aug 12) | -5.87% (Aug 28) | -0.12% (Sep 8) | Clean both, FDA approval announced Sep 14 |

Original sponsor dates: OTLK June 16 2026 release states July 29 goal
(https://ir.oncobiologics.com/news-releases/news-release-details/outlook-therapeutics-announces-fda-acceptance-resubmitted).
TLX April 10 2026 release states September 11 goal
(https://telixpharma.com/news-views/fda-accepts-nda-for-tlx101-px-pixclara/).
Actual price-source links are in the companion CSV.

**Updated**: combining the prior CING/ACHV/UNCY with the new clean
ARQT/VERA/REPL/MRNA/TLX examples yields eight calendar-price cases with
both late and early scheduled exits preceding documented FDA action.
Average T-14 return -2.16%, T-3 -5.04%; wins 3/8 for each.
These are descriptive tiny-sample statistics with major selection bias
and depend strongly on the REPL drawdown. The other four calendar cases
VRDN/LNTH/CELC/OTLK have late-window FDA same-day/censor caveats.
**No fully qualified GEM two-financing entry has been backtested.**
