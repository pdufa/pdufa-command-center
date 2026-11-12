# All saved PIPELINE / GEM JR / GEM trials — historical backtest readiness

**Audited October 18, 2026 (research branch, not production deployment).**

Scope: read every accessible trial row from repository data files, retain
current exact-program GEM and GEM JR stage links, and attempt the existing
54-scenario 2026 GEM technical-entry and exit replay across every verified
point-in-time PDUFA event. Do not invent historical event or market bars.

## What actually ran

| Source | Rows examined |
|---|---:|
| All-phase trial table | 11,578 |
| PIPELINE trial table | 7,365 |
| Discovery events | 263 |
| PDUFA candidate ledger | 45 |
| Post-Phase-3 discoveries | 3 |
| Extra exact-stage GEM/GEM JR entries not already matched to a PDUFA key | 3 |
| **Total source rows audited (NOT unique trials)** | **19,257** |

The stage membership ledger held 20 entries: 6 currently active GEM,
11 currently active GEM JR, and three nonactive entries.
Sources overlap: neither 19,257 nor 7,365 is a claim of independently
tradable stocks or programs.

## Result

| Finding | Count |
|---|---:|
| No confirmed PDUFA goal or nonapplication Phase-2/3 records | 19,209 |
| PDUFA target later than study cutoff (October 18, 2026) | 41 |
| Historical eligible-looking records lacking audited source-linked event | 7 |
| Audited historical trade-event input rows | **0** |
| Verified split-adjusted historical OHLCV input rows | **0** |
| **Completed real-company GEM entry-to-exit trade replays** | **0** |

The all-year source audit and test workflows completed successfully.
**No strategy win rate, average gain, ideal entry or optimal exit has
been established** from this run. The 54 technical parameter settings
remain a coded experimental grid and cannot be promoted to real trading
thresholds from an empty verified price dataset.

## What is needed to turn this audit into a true backtest

1. Populate original, publicly known Phase-3 efficacy readout and date;
   exact issuer ticker, historical CIK and NCT.
2. Verify two distinct *completed* post-readout financing closings and
   each first SEC-public disclosure date; today's closed status is not enough.
3. Preserve original publicly announced PDUFA target, change notices and
   any early FDA actions (approval, CRL or delay), with source dates.
4. Fetch and audit full historic split-adjusted DAILY open, high, low,
   close and volume for the relevant issuer and window. Current 35-bar
   close-only market snapshots cannot substitute for this.
5. Replay entries strictly after benchmarks and exits with FDA action
   timing; report nonentries, gaps, censoring, slippage and stop gaps.
6. Freeze the chosen parameters and test them on a separate time period
   before describing BUY/WAIT/SELL as validated.

**The requested market capitalization filter remains OFF for 2026.**
No stock orders placed, brokerage account altered, live dashboard changed,
or production daily schedule activated.

## Where to inspect the machine-readable output

The 'GEM Historical Signal Backtest Checks' GitHub Actions workflow uploads
the `gem-all-system-trials-audit` artifact with:

- `every_saved_trial_eligibility.csv` (all 19,257 source rows and blockers)
- `pdufa_historical_backfill_priorities.csv` (7 past-event source backfills followed by 41 future-target rows)
- `qualified_historical_trade_scenarios.csv` (headers only while no verification)
- `entry_exit_returns.csv` (headers only while no verification)
- `strategy_grid_summary.csv` (54 settings, unavailable performance)
- `coverage_and_blockers.json` (exact data coverage and blocking reasons)

Runner: `scripts/run_all_system_trials_backtest.py`.
Research implementation: https://github.com/pdufa/pdufa-command-center/pull/135
