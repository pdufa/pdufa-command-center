# ATSMS — automatic FOCUS market-monitoring installation

## Current phase: read-only scheduled scanner

Workflow: `.github/workflows/atsms-focus-market-monitor.yml`.
Script: `scripts/atsms_focus_monitor.py`.
Current FOCUS source: `new-platform/frontend/data/p3PostDataActive.json`.

The nightly POOL workflow is followed by the existing **FOCUS Google Sheets → Website source snapshot** workflow. ATSMS reads the current, verified FOCUS snapshot at each market session tick, and also wakes following a successful FOCUS synchronization workflow. It automatically includes newly verified NCT/ticker records and drops removed NCTs; no hardcoded two-ticker roster.

ATSMS is scheduled every five minutes in the US market window **04:00–20:00 America/New_York** (01:00–17:00 Pacific), including premarket and postmarket. NYSE sessions, holidays, DST and early regular closes are determined from `exchange_calendars`. GitHub Actions cron is best-effort, not a guaranteed continuously running process; delayed or skipped checks are possible.

The EOD eight-check BUY setup uses the existing WT thresholds: base width, stabilizing lows, breakout, SMA20/SMA50, RVOL20, RSI14, average dollar liquidity and ATR14/close. **Unbacktested**. Completed daily bars and the latest available one-minute bar are distinct. Intraday status is only issued for a timestamped bar no older than ten minutes in the present exchange-local date. A latest bar may be unavailable in the free IEX feed, especially pre- and postmarket. A technical setup is neither an executable quote nor an order.

ENTRY alerts require outside the **14-day pre-PDUFA no-new-buy blackout**, a fresh intraday bar and the full eight-check daily technical setup. Missing/invalid PDUFA target = ENTRY BLOCKED. STAY is only a price/trend observation; no holdings or broker fills are inferred. EXIT is a **risk warning**, not a verified position-based sell instruction. Stops can gap or slip and do not guarantee fills.

## Credentials required in GitHub Actions

Add **repository secrets**, not plain repository variables:
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

These are separate from the same-named variables already used on Render; they do not migrate automatically. **Do not paste keys into ChatGPT or commit them to Git.** ATSMS defaults to `feed=iex`, which is single-exchange market data, not SIP consolidated data. The historical and latest Alpaca endpoints are read-only `data.alpaca.markets`. SIP must not be enabled without verified entitlements.

Optional existing alert secrets:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Telegram sends only new entry-watch/exit-warning transitions from previously saved valid evaluations. An initial check does not trigger a flood. The cache is best effort, so it is **not** a durable exactly-once notification service. Missing Telegram credentials or failed delivery must be surfaced in the report.

## Where results go

Every ATSMS workflow run uploads a **seven-day JSON artifact** named `atsms-focus-scan-<run>` and prints a summary in GitHub Actions. Last-signal state is held in the GitHub Actions cache. **These artifacts do not yet populate the live WT Status page.** The next independent stage will add a secure durable results store, authenticated API, per-ticker historical display, reliable deduplication and retrying delivery. Do not repeatedly commit minute-by-minute JSON to main (it would cause unnecessary Vercel deployments).

Workflow will show `ALPACA_CREDENTIALS_NOT_CONFIGURED` if the GitHub secrets are absent, or `ALPACA_DATA_UNAVAILABLE` if data is missing. Neither means successful price monitoring.

## Safe launch checklist

1. CI validates the scanner and source contracts.
2. Merge the workflow and verify the first push-triggered GitHub Actions run.
3. Review its JSON `status`: only `EVALUATED` and nonzero `availableIntraday` establish working market observation.
4. If missing, configure the Alpaca market-data GitHub repository secrets securely and rerun via workflow dispatch.
5. Verify at least two market-hour timestamps and an off-hours/holiday skip.
6. Add the authenticated WT reporting/durable alert stage separately; keep E*TRADE brokerage execution disabled.

No actual trading, order routing, preview, cash movement or broker connection is implemented by ATSMS.
