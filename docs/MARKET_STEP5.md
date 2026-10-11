# Step 5 — Market Intelligence and Ranking

Initial working technical research engine, not an FDA approval probability, clinical-outcome model, trading forecast, or buy/sell signal.

## Where it appears

An independent Streamlit page: pages/03_Market_Intelligence.py. PRE PHASE 3 remains intentionally blank. Display there requires separate Step 6 authorization.

## Data capture

Choose a uniquely registered ticker from data/company_registry.csv, PRE_RESULTS or POST_RESULTS, analysis as-of date and an HTTPS documentary evidence source with date for the phase assertion. POST requires an actual Phase 3 results publication date on/before the as-of date. Phase assertions remain researcher-reviewed, not independently verified by software.

On explicit button click, fetch delayed US EOD OHLCV via Stooq, or upload Date,Open,High,Low,Close,Volume CSV and an HTTPS provenance URL. There is no automatic scan at page load, no overnight refresh and no universe backfill. Stooq market symbols and split/adjustment practices need independent issuer and venue verification. Provider data can be absent, rate limited, stale or inaccurate.

A score needs 31 trading sessions, a valid earlier price and nonzero earlier average volume, plus a last bar within 7 calendar days. All inputs are truncated to the as-of date to prevent use of future prices. If phase evidence is missing, score is withheld and the observed indicators remain visible for research.

## Technical-only weighted setup score

| Factor | PRE results | POST results |
|---|---:|---:|
| 30-session price momentum | 25 | 20 |
| Relative volume vs prior 20 sessions | 20 | 25 |
| Price vs 20-session average | 20 | 20 |
| Average dollar liquidity | 15 | 20 |
| Historical realized volatility risk | 20 | 15 |
| **Total** | **100** | **100** |

Scores rely on transparent initial **heuristics**, not historically calibrated or backtested coefficients. PRE/POST models have distinct weights. Rankings never mix pre/post or as-of dates. The score does not estimate returns, FDA approval, trial results, volatility events or short-squeeze probability.

Source-dated manual intelligence fields include short interest % float, days-to-cover, options implied volatility %, institutional holdings change % and borrow fees %. Each entered figure must have an HTTPS source and timely date. Missing/stale inputs remain NOT VERIFIED and are not included in technical score. There is no automatic paid-market-feed connection.

POST stage can optionally show 90–61, 60–31, 30–14 and 13–1 days before a source-dated PDUFA date. This is context only, not an FDA decision prediction.

When Step 4 SEC snapshot history is available in local SQLite, Step 5 may show as-of eligible cash-runway context for the issuer, separate from technical scores.

## Audit history

Backend market_step5.py and page pages/03_Market_Intelligence.py save append-only checksummed records to data/market_step5_history.sqlite3, with as-of, sources, phase, indicators, factor points, source status and last 40 bars. Identical reruns are idempotent. Export complete audit history as JSON from Streamlit. Cloud-local files are ephemeral: use external durable storage for persistence.

Tests: tests/test_market_step5.py and tests/test_market_step5_ui.py. Full regression suite: python -m unittest discover -s tests.

Example explicit single-ticker CLI:

    python market_step5.py --ticker ABCD --phase PRE_RESULTS --phase-url https://clinicaltrials.gov/study/NCT01234567 --phase-date 2026-10-01 --as-of 2026-10-10 --csv verified_eod_bars.csv

## Not yet verified or implemented

No full-universe market backfill, walk-forward return validation, external persistent database, real-time feeds, automated options/short/institutional indicators, automatic trial phase evidence verification, or independently verified cloud deployment of the new page. Step 6 is reserved for PRE PHASE 3 display.