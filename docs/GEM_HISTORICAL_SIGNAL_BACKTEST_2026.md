# GEM/JR 2026 historical entry-and-exit research

**Study year: 2026. The 2026 run has NO market-cap restriction.**

This is the same provisional 54-setting signal grid used for 2025:
entry score thresholds 60/70/80, relative-volume thresholds 1.25/1.5/2.0,
base width thresholds 2/3/4 ATR and mandatory pre-PDUFA exits at 14/3 days.
The two Phase-3 and financing evidence benchmarks remain unchanged.

## Run the uncapped 2026 audit

    python gem_historical_signal_backtest.py --year 2026 --as-of 2026-10-17 --output-dir output/gem_backtest_2026

No market-cap argument is needed: the default is **OFF**. Research evidence is
still incomplete: the verified event and adjusted OHLCV templates have headers
but no observations. The 2026 research queue has 23 existing candidate records,
of which 4 carry reported PDUFA targets on or before October 17, 2026 and 19
have later target dates. The queue is incomplete and not sufficient for
performance or win-rate claims. No synthetic test data enters performance CSVs.

Results: per_event_signals.csv, parameter_grid_summary.csv, readiness.json.
readiness.json explicitly reports market_cap_filter_active=false.

## Keep the $300M–$10B range for later

The historical market cap snapshot template is preserved but ignored by this
2026 study. To opt into that separate feature for a future test, add:

    --apply-market-cap-filter --market-caps data/post_phase3_historical_market_caps.csv --min-cap-usd 300000000 --max-cap-usd 10000000000

Only historically available, verified snapshots may satisfy that optional gate.
Today's market-cap value or bucket is not a historical snapshot.

## Study limitations

October 17, 2026 is the study cutoff. Future 2026 targets cannot be treated
as completed events. The earliest entry is the next trading session after all
required public knowledge. Stops, adverse gaps, missing prices, early FDA
decisions and unqualified events remain explicit. The 2025 implementation
was verified on synthetic test fixtures but had zero audited 2025 trades;
there is therefore no verified 2025 performance to claim 2026 beat.

Research-only; no trades or changes to active GEM/GEM JR scores or scan timing.

## Entry-to-exit return report

The 2026 audit also writes `entry_exit_returns.csv` with one row for each
candidate and parameter setting. For completed simulated trades it shows:
entry and exit dates, observed entry OPEN and exit fill, slippage-adjusted
buy/sell prices, gross return %, **net return %**, net profit per share,
number of hypothetical whole shares affordable with $10,000, dollars actually
invested, dollar profit/loss and % return on the original $10,000 allocation.
Change the hypothetical per-trade allocation using `--investment-usd 10000`.
The unused cash earns zero return and no fees/taxes are modelled. The net
return includes 10 basis points of slippage per leg by default. These are
**per-individual-trade illustrations, not simultaneous portfolio totals**.
Returns remain empty for BLOCKED/NO_SIGNAL/CENSORED rows, which must not
be counted as winning trades. Data templates are currently unpopulated, so
no actual 2026 historical returns are established yet.
