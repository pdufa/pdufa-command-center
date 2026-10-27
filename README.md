# PDUFA Command Center — Next.js / Vercel

The active dashboard is `new-platform/frontend` (Next.js on Vercel), with `new-platform/backend` (Render) and GitHub Actions source scans. **Streamlit is retired from the deployment setup.** Do not deploy `app.py` or create a Streamlit Cloud app. A pre-removal backup of the old implementation exists at branch `archive/streamlit-legacy-20261018`.

The operational scanners and source archives are separate from the dashboard. Do not delete or disable scheduled GitHub Actions while retiring Streamlit.

---

# PDUFA Command Center

## Alpaca Paper Trading connection (read-only)

In Streamlit Community Cloud, open this app's **Settings → Secrets** and
save the following TOML using your **paper** API credentials (never commit
these credentials to GitHub):

```toml
ALPACA_API_KEY = "YOUR_PAPER_API_KEY_ID"
ALPACA_SECRET_KEY = "YOUR_PAPER_SECRET_KEY"
ALPACA_PAPER = true
```

Open **PDUFA → WT**, expand **ALPACA — PAPER CONNECTION STATUS**, then click
**TEST PAPER CONNECTION** and **TEST SPY MARKET DATA (IEX)**. Both checks are
operator-initiated; the first makes a read-only paper-account request, and
the second requests one SPY IEX latest-minute bar. No account number,
balance, position, key, secret, or raw API exception is displayed. A
successful connection requires a live test in the deployed app; code
installation alone does **not** verify valid secrets or network access.

The Market Data test uses **IEX**, not consolidated SIP market data. Neither
test is integrated into GEM scoring, overnight scans, or order placement.
The TradingView watch/trade screen is preserved; no real or paper trades
are submitted by this module. A live-mode flag is explicitly rejected.
If secrets are updated, restarting the Streamlit app may be necessary.
`.streamlit/secrets.toml` is excluded by `.gitignore`. See
[Alpaca SDK](https://alpaca.markets/sdks/python/trading.html) and
[Streamlit Secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management).


## Nightly Scan Report subtab (October 12, 2026)

**PDUFA → NIGHTLY SCAN REPORT**, directly before **WATCHLIST / TRADING**, reads the published `data/nightly_scan_report.json` audit. The 10 PM Pacific scheduler starts `pdufa-overnight-sequential.yml`, which awaits the clinical collectors, both GEM tasks, report publication, source verification, scoring and repair in one run. The publisher downloads the same run’s archived per-scan JSON/status files, checks consistency and writes the displayed report. Standalone manual clinical runs retain their completion-triggered publisher. Prior scan results are revalidated from their own archived run when a targeted collection occurs; missing or expired artifacts remain UNVERIFIED. The UI does not invent missing new-record or changed-trial totals.

**Three controls** are available: **REVERIFY PARTIAL** recollects the clinical scans and publishes a new audit, **VERIFY ALL** rechecks their archived clinical source evidence, and **RESCAN ALL** reruns the three clinical collectors. An additional target selector can recollect only #2, #3 or #4. The buttons dispatch `pdufa-scan-control.yml`. ALL collection requests use the same complete serial workflow, including GEM; targeted requests retain their individual collectors. The report and control buttons are separate from trading tags; no order placement occurs.

**Required activation:** To enable the buttons *inside Streamlit*, configure Streamlit app secrets `PDUFA_GITHUB_TOKEN` (fine-grained GitHub token with Actions read/write permission for this repository; keep server-side) and `PDUFA_SCAN_CONTROL_PIN` (private operator PIN). Users without these secrets can still view published reports, and repository owners can use the **OPEN SCAN CONTROLS IN GITHUB ACTIONS** link to trigger the control workflow manually. The collector itself retains the previously documented GitHub Actions secrets `PDUFA_GMAIL_USER`, `PDUFA_GMAIL_APP_PASSWORD`, and `PDUFA_ALERT_EMAIL`: absent secrets block clinical collection. No passwords or personal tokens should be committed to files.

**Operational boundary:** The new tab and workflows are code-installed, but a successful *live end-to-end scan and email delivery* must still be observed after secrets are configured. Before a first published artifact the page explicitly says that no audited report exists. A clinical `PARTIAL` result means clinical-source collection succeeded, **not** that FDA/SEC/issuer/market data was verified. `VERIFY ALL` revalidates archived clinical JSON, not the missing source families. The automated syntax/unit-test check is in `pdufa-nightly-report-checks.yml`.


## Active daily PM scan survey — 8:00 PM Pacific

**Enabled:** `.github/workflows/pdufa-nightly-pacific-start.yml` starts the
strictly ordered **daily 8:00 PM Pacific** sequence:
**#2 PIPELINE → #3 PRE3 → #4 POST3 → GEM research → GEM financing
full-coverage audit → nightly report → FDA → SEC → FINANCIAL → MARKET →
ISSUER → source reconciliation → source report → PRE3 display refresh →
scoring → error check → guarded repair**.
Each main research step waits for the prior one to finish, even on a
recorded failure. Morning results are a separate read-only report.

GitHub UTC cron uses `0 3 * * *` during PDT (UTC−7) and
`0 4 * * *` during PST (UTC−8), with 8:15/8:30 PM guarded backups.
After-midnight recovery crons can start a missed nightly run until 2:59 AM Pacific.

The executable launcher and `scripts/nightly_start.py` are the clock authority. Saved `config/scan_234.json` timing labels still describe 10 PM and are nonauthoritative metadata. `python scripts/audit_scan_schedule.py` exposes this drift without dispatching scans or changing schedules; see [the read-only schedule audit](docs/scan-schedule-metadata-audit.md). Earlier dated Streamlit notes above describe historical UI behavior and do not override the active launcher.
Duplicate detection checks only the complete workflow, so a targeted manual
clinical scan cannot suppress the full overnight run. An active older full run
also blocks a duplicate. One workflow-wide lock covers the entire sequence.
The chain uses awaited reusable jobs, avoiding lost cross-workflow completion
events. A recorded failed nightly attempt remains visible; backups do not
blindly repeat every source scan.
The GEM workflows are called *inside* the nightly clinical workflow so
the downstream publisher does not start until both GEM tasks finish.
Their former independent daily schedules are disabled; explicit manual
`workflow_dispatch` remains supported. The independent 6 AM
Pacific read-only report checks evidence since the previous night's
10 PM start. GitHub Actions scheduling can be delayed; the configured
clock time is a target, not a guaranteed start or completion time.
No scanner result automatically authorizes trading.

Each collector (#2 all-phase trial inventory and tracked NCT refresh;
#3 Phase 2/3 clinical pipeline + limited market-cap checks; #4 Phase 3
ClinicalTrials.gov posted-results *daily* update) is wrapped by
`scripts/run_scan_with_email.py`. A successful START email submission is
required before collection; the END email is attempted even on failure.
The report explicitly remains **PARTIAL/FAILED** for the *full-source*
baseline; clinical completion is not FDA, SEC, issuer, or full market
verification. Output CSVs, state, and notification audit are archived as
GitHub Actions artifacts (30-day retention). **Completed clinical source snapshots are validated and published before the
next collector starts; incomplete snapshots keep the prior published data.** The config
`clinical_source_schedule.enabled` tracks this *limited* schedule
separately from the unimplemented full-source automation/baseline gate.

## Independent scan completion emails (October 11, 2026)

The original **PDUFA One-Time Clinical Scan** completed #2 PIPELINE, #3 PRE3
and #4 POST3 as separate clinical-source jobs but did not send END emails.
The replacement completion notification lives in
`.github/workflows/pdufa-clinical-scan-end-email.yml`: it listens for
`workflow_run: completed` for that exact collector workflow, so it can
report success, failure, or cancellation independently of the original job.
It does **not** trigger another clinical scan and has no recurring scan schedule.

`scripts/notify_completed_clinical_run.py` reads the three exact scan jobs and
`scan_execution_report.json` audit manifests from the GitHub Actions artifacts,
then submits one email per #2/#3/#4 through `scripts/scan_email.py`.
Collector success without a full all-source coverage audit remains
**PARTIAL/UNVERIFIED**, never full-baseline COMPLETE. Missing manifests, failed
collector jobs and error counts are disclosed rather than invented.
Review `tests/test_pdufa_completion_emails.py` for offline coverage.

**Activation is still blocked until GitHub repository Actions secrets**
`PDUFA_GMAIL_USER`, `PDUFA_GMAIL_APP_PASSWORD` and
`PDUFA_ALERT_EMAIL` are configured and a delivery test succeeds.
The ChatGPT Gmail connector cannot give GitHub Actions its SMTP credentials.
See `docs/GMAIL_SCAN_ALERT_SETUP.md`. To resend the historical completion
email after configuring secrets, manually run
`PDUFA Clinical Scan Completion Email` with run ID `38195214610`.
Manual resends intentionally repeat messages; do not use them blindly.

## Watchlist / Trading subtab (October 11, 2026)

Inside **PDUFA → WATCHLIST / TRADING**, Watchlist is on top and Trading is
below. W and T are two independent browser-saved research tags. Click **W** or
**T** directly before any ticker in **UNIFIED OVERVIEW → #2 PIPELINE, #3 PRE3,
or #4 POST3**. When the Watchlist/Trading subtab opens, the selected ticker
appears with an attached TradingView stock chart, which loads automatically.
Clicking a **Watchlist ticker name** or **MOVE TO TRADE** transfers that
ticker to the Trading section and removes its Watchlist row and chart.
The W tag is cleared and the T tag is added atomically; an existing T tag
is retained instead of being toggled off. The Trading chart starts when the
move happens (or keeps its original Trading tracking date if already tagged).
**REMOVE W** and **REMOVE T** remain independent removal actions.

**Compact + Full Chart upgrade:** Each Watchlist and Trading ticker retains its
lightweight, auto-loading TradingView Symbol Overview chart. The **FULL CHART**
button alongside that ticker opens a larger interactive TradingView Advanced
Chart within the same row. It starts on daily candlesticks with Volume visible
and preloads EMA, RSI and MACD indicators. TradingView's toolbar exposes
additional provider-supported indicators, drawing tools, timeframes and chart
settings. **HIDE FULL CHART** or **CLOSE FULL CHART** collapses the advanced
view while retaining the compact chart and independent W/T selections.
Advanced widgets load only on demand, to avoid launching one heavy chart for
every selected ticker. If TradingView cannot embed a chart for a ticker, its
external TradingView ticker link remains available; no technical data is
invented. These widget settings are not a guaranteed persistent indicator
template or event-anchored price backtest.

New selections capture separate Watch and Trade activation timestamps under
`pdufa_watch_trading_since_v1`; the existing membership store
`pdufa_watch_trading_v1` remains compatible with earlier Watch/Trade buttons.
For older entries without an activation timestamp, tracking begins when the
new screen first observes that entry; no historical entry time is invented.
The embedded chart chooses the closest supported provider time range to the
activation timestamp, not an exact adjusted-price baseline or execution
performance series. Quotes can be delayed or unavailable. Charts are
automatically mounted on new additions or when visible, with the most recent
ticker initialized immediately. Browser storage is local to the device;
no broker orders are sent.

## Unified Overview dashboard and Post Phase 3 workspace (October 11, 2026)

**PDUFA → UNIFIED OVERVIEW** displays **#1-DB** with linked **#2-PIPELINE**,
**#3-PRE3** and **#4-POST3** blocks. One **Focus ticker** selection updates all three
panels; shared phase, stage, search and sort controls narrow the view. The
light-green background, white panels with black borders, and stacked mobile
layout are retained. Expand the detail panels for all score components and
source evidence; CSV exports include every matching record.
**Top Score** sorts **Score /100 descending**, then **Days to PDUFA ascending**
for equal scores. Missing scores come last; missing dates come last within each
score group. This shared order applies to all four PDUFA subtabs and score blocks.
Large, faint background numbers match the exact panel titles: **#1-DB**,
**#2-PIPELINE**, **#3-PRE3**, and **#4-POST3**. PRE3 shows the current validated
pre-readout feed; POST3 shows current post-readout candidates. The expandable
**PDUFA Timeline** and its export remain available within POST3.

**PDUFA → POST PHASE 3** contains the combined clinical/pipeline display and
all three trading sections: discovery/qualification, reported-position
monitoring, and historical entry/exit research. **Focus ticker** links the
clinical table, PDUFA timing, candidate queue, position table and historical
research. The default **All tickers** keeps the full workspace available.
The existing columns, source audits, score models, financing colors, sort
controls and CSV exports are retained. Portfolio totals and exit alerts still
cover the complete uploaded journal when its displayed rows are ticker-filtered.

PIPELINE and PRE PHASE 3 retain their existing separate workflows.

## Stage 3 historical evidence backfill worklist

The Stage 3 workflow now produces `historical_source_backfill_queue.csv` by reviewing the saved `pdufa_candidates.csv`, `second_financing_status.csv` and `company_registry.csv`. It matches exact event keys and issuer SEC CIKs and sorts existing historic financing references into three research priorities: potential two-close funding evidence, incomplete funding evidence and clinical-program discovery. Each row lists outstanding clinical readout/benefit/safety, *first-public* SEC filing dates, original PDUFA date history and historical split-adjusted OHLCV.

This queue is **NOT** new verified trading data. Even a record marked VERIFIED_SECOND_POST_PHASE3_FINANCING in the older *retrospective* financing ledger is only a research candidate: the actual date the filings became publicly available must be independently recorded before historical simulation. All queue entries explicitly have `eligible_for_historical_trade_backtest = NO — RESEARCH QUEUE ONLY`. Phase 3 evidence and FDA outcome remain separate. The Stage 3 workspace displays the research queue, while GitHub Actions also provides downloadable audit artifacts.

## Stage 3 — offline post-Phase-3 stock-trading backtest

Stage 3 now has a read-only research view inside PDUFA → POST PHASE 3, backed by the independent offline Python engine. It is not the retrospective FDA-approval prediction scorecard.

Run locally or in a GitHub Actions workflow:
```sh
python -m unittest discover -s tests -p 'test_post_phase3_trade_backtest.py' -v
python scripts/run_post_phase3_trade_backtest.py --output-dir output/post_phase3_stage3
```
Results and a source-readiness audit appear in `output/post_phase3_stage3/`: `per_event_scenarios.csv` (all valid/blocked/censored cases), `scenario_summary.csv` (four entry methods × exits at PDUFA-30/-14/-7), `matched_event_comparison.csv` (returns compared only for exact programs with all four complete entry methods), and `readiness_and_blockers.json` (data counts, gaps, source caveats). The workflow `stage3-trade-backtest.yml` uploads these outputs as a downloadable Actions artifact without committing private trading data.

### Honest evidence boundary

The checked-in historical trade **event timeline** template (`data/post_phase3_historical_trade_events.csv`) and **split-adjusted OHLCV** template (`data/post_phase3_historical_adjusted_ohlcv.csv`) start with headers only. **Zero audited event rows or missing historical adjusted prices mean no completed backtest and NO WIN-RATE CLAIM.** The older historical FDA decision file and the recent 35-session EOD market snapshot are insufficient to compute post-readout/second-financing trading returns. They are reported solely as source inventory, not silently translated into qualifying trades. Historical funding sources must establish two distinct post-readout closes for the *same SEC CIK issuer* and exact clinical event. Readout, financing and PDUFA **public knowledge dates** are separate from when the underlying clinical/financial event occurred. An offering announcement or ATM authorization is not a closed financing.

Four point-in-time entry variants are compared: **(1) clinical readout benchmark** and **(2) first-financing benchmark** are *conditional on eventual two-financing completion*, so they have serious selection/survivorship bias and are **not** eligible GREEN entries under the user's actual trading rule; **(3) second-financing disclosure**; **(4) 10-session post-second-financing stabilized base** using trailing *observed* close/volume data. Every entry occurs at the next session OPEN after the complete required public disclosure, never the same session closing price. Candidate PDUFA date must also already have been publicly disclosed by the entry. Each 30/14/7-calendar-day pre-PDUFA target exits using the last actual session CLOSE on or before its cutoff. Missing trading sessions, inadequate prior-20-day dollar liquidity, stale/future historical bars, incomplete SEC provenance, or incomplete efficacy/safety evidence keep the scenario BLOCKED. A known *early FDA decision* on or before planned exit marks the case CENSORED; those cases must be reported as risk, not excluded silently from the trade universe. Hypothetical returns apply stated per-leg slippage; real fills, fees, corporate action handling beyond verified split adjustment, halt gaps, taxes and short borrow are NOT simulated. Past gross/adjusted percentages do not imply future performance.

**Do not treat the output as an optimized or validated trading strategy.** If completed samples are under 30, summary cells are marked exploratory, and a larger calendar-time chronological holdout plus separate treatment of early actions, delistings and the entire eligible trial universe are mandatory before claiming that one entry/exit period is better. The first two benchmark strategies must also be rerun on a historically complete readout universe to eliminate conditioning on future financings.

To populate the templates, research issuer press releases and relevant SEC filings for dated publicly observable evidence and retrieve verifiable historical split-adjusted **daily OPEN/HIGH/LOW/CLOSE/VOLUME** with trustworthy source documentation. Audit historical issuer identity, filing availability and incomplete outcomes; do not backfill speculative clinical probabilities. The underlying source collector and files remain preserved. Stage 1 and 2 research/position modules are now accessible through the restored POST PHASE 3 workflow.


## POST PHASE 3 — three-stage trading workspace (reinstalled October 11, 2026)

### Combined GREEN gate + highest-to-lowest evidence rating

### Visible research ranking when verified evidence is incomplete

The POST PHASE 3 candidate table now has **two distinct numerical dimensions** to avoid a previously empty ordinal column. **Research rank** (1, 2, 3...) and **Research priority /100** are populated for every active GREEN or REVIEW candidate, including blocked financing or unadjudicated Phase 3 readouts. The research priority is a *worklist/triage* order, not scientific efficacy, upside, approval probability or proof of financing. Its metadata rubric weights known PDUFA time horizon (30), clinical readout follow-up readiness (20), distinct-program financing-review progress (15), regulatory date/document review (15), recent issuer ticker price/volume observations (15), and exact trial/program identity (5). Reported PDUFA dates may raise research urgency, but do **not** pass the verified PDUFA entry gate; blocked SEC checks do **not** receive financing-closure credit.

**Evidence score /100** and **Evidence rank** remain the existing strict, source-attested dimensions, and may legitimately be blank; no missing gate is converted to PASS. The default sorting orders eligibility first and then research priority high-to-low; alternate selectors compare research priority across statuses, strict source-attested evidence, or soonest PDUFA. A **TOP 10 — RESEARCH PRIORITY (NOT ENTRY SIGNALS)** list is visible ahead of the full table. Resolved companies and RED no-new-entry cases do not receive active research ranks. Current company-product commercial history and unverified short interest/float still earn no verified evidence credit.


The **POST PHASE 3 → 1 · Discover & qualify** view now merges two formerly separate decision dimensions into a single ranked row: hard **Entry qualification** (GREEN / REVIEW / RED / EXCLUDED) and a separate ordinal **Evidence rank** with **Evidence score /100**. The default order places eligible GREEN programs ahead of REVIEW cases and uses descending evidence points within each group. Users may switch to overall highest-score or soonest-PDUFA order. Scores do **not** override mandatory financing/clinical/market hard gates.

This is an **incomplete, evidence-support research rubric**, **not** an independently validated FDA approval probability, expected return, or certified company quality score. Weights are clinical evidence 30, current SEC second-financing/dilution evidence 20, source-linked technical setup 20, verified PDUFA evidence 15, recent provider-labeled price/volume/momentum observations 10, and company track record 5. The last five points stay unawarded until a separately sourced product/revenue/track record audit is available; the market component does not yet independently score short interest/float. Score components require fresh and attributed inputs; stale snapshots and unmatched leads show **NOT RATED** (no invented numeric score). The research rank excludes RED-window and resolved events but can rank REVIEW rows above a GREEN row numerically; **eligibility status remains the controlling entry gate**.


The user subsequently requested reinstatement of POST PHASE 3 after the prior clear. Go to **PDUFA → POST PHASE 3** and choose among three stages from one selector: **1 · Discover & qualify** (Phase 3 readout and second-financing source checks, entry gates, PDUFA countdown, research leads, export), **2 · Monitor & exit** (download/upload a private CSV of user-reported positions, YELLOW hold, RED cutoff due/recorded exit), and **3 · Historical backtest** (historical research worklist, data templates, four entry methods and 30/14/7-day exit scenarios, matched-program comparisons, downloadable audit summaries). Nothing trades automatically. Statuses remain REVIEW when evidence is incomplete; the older FDA-decision scorecard cannot substitute for historical prices. A financing closure and a GREEN clinical/market entry are distinct from the financing-cycle traffic-light colors.

The previous standalone daily report is still not reinstated; the earlier saved collector files and research modules remain in the repository. PIPELINE and PRE PHASE 3 were not modified.


## Stage 2: reported positions and exit monitoring (no trading API)

Under PDUFA → POST PHASE 3, select **2 · Monitor & exit** and download the blank POSITION JOURNAL CSV. Add actual user-reported trade fills (trade_id, exact event_key, ticker, NCT ID, entry date/price/shares, PDUFA date observed at entry). Optional exit date/price/reason must represent an actual completed fill. Upload the CSV in the app for a read-only session report; **the upload is not saved to this public repository**, no brokerage API or trading order is connected, and a Streamlit restart may clear the upload. Do not put private positions into a GitHub issue, commit or PR. Download the monitored CSV and store it privately. Partial lot exits are not supported by this simple journal; use distinct complete trade lots.

The monitor joins positions to clinical programs by **exact event key and NCT ID**, not ticker. Missing or duplicate IDs, conflicts and missing verified PDUFA dates remain REVIEW. GREEN signifies attested prospective research eligibility, not an executed buy. YELLOW represents the user's reported open positions while the pre-PDUFA monitoring window remains open. RED — EXIT DUE is a **notification**, NOT proof of sale; RED — EXIT RECORDED requires a valid user-supplied exit fill. Current resolved FDA events trigger urgent RED review, not an automatic sale. When a historical PDUFA-at-entry date differs from a current verified date, the earlier date determines the conservative PDUFA-minus-seven-calendar-days exit deadline and the difference is flagged. The app does not retroactively certify that entry gates passed when the user bought the stock.

The stock value is marked only when a fresh, source-labeled provider-reported EOD quote exists *on or after the reported entry date*. No marked P/L is calculated from old or missing quotes. The simplified P/L excludes commissions, spread, tax, corporate actions and slippage. Exit reporting uses user-provided fill price. No live quotes, automated broker orders, private account sync or push notifications exist yet.

### SEC second-financing bottleneck

The unified screen surfaces source freshness and the count of blocked SEC events. The first-ten audit workflow is at .github/workflows/first10-financing-audit.yml. Live SEC checks require a valid identifiable SEC_USER_AGENT in the repository's GitHub Actions secret settings and working SEC access; HTTP 403 is a hard blocker. Use the historical filing/exhibit references to guide manual review, but never equate a registration, priced offering or issuance authorization with an actual closed financing. No unavailable SEC evidence is fabricated or silently promoted to a green entry gate.

## Unified POST PHASE 3 trading research — Stage 1

The top of **PDUFA → POST PHASE 3** now shows a searchable, downloadable candidate queue from (1) exact program PDUFA/financing events, (2) Phase 3 issuer/readout or registry-posted research leads from the saved trial pipeline, and (3) optional independently discovered leads. Add discoveries to data/post_phase3_discoveries.csv with exact ticker, drug, indication, NCT ID, a dated release and HTTPS source. A discovery remains REVIEW until independently verified.

post_phase3_unified.py never uses ticker-only matches to validate financing. A registry result is not clinical success. GREEN — GATES ATTESTED requires eight attested Step 7 PASS gates, current SEC recheck, exact-event source-linked clinical results, verified PDUFA date, no conflicts, and more than seven days before PDUFA. It is not a recommendation, independent source-document audit or opened position. Snapshot expiry prevents GREEN. The planned PDUFA-minus-seven-day exit is shown; RED WINDOW — NO NEW ENTRY does not mean a position was sold. FDA-decided events are excluded.

Financing cycle is separate from trading lifecycle: GREEN = financing started, YELLOW = running, RED = completed (historical when dated). Stage 2 monitors user-reported open holdings and actual exits in a session-only trade journal; Stage 1 invents neither orders nor transactions. Collector failures keep events in REVIEW; the PRE PHASE 3 feed is unaffected.


## Review priority across every saved trial

**PDUFA → PRE PHASE 3 → ALL-TRIAL REVIEW PRIORITY** assigns every exact ticker/NCT row a **Review priority /100**. Active review candidates receive a global rank, sorted first by default. Filters preserve those global ranks. The order selector also supports clinical research score or ticker/NCT order; the CSV export includes every filtered row, all point components, source timestamps, evidence gaps and the next review action.

`pre_phase3_priority.py` defines `REVIEW-PRIORITY-V1`: stage /30, saved program identity /15, registry freshness /10, exact-NCT protocol field coverage /15, presence of source-dated linked Phase 2 PRIMARY evidence /15, registry completion timing /10 and recent $300M–$10B market-cap fit /5. A smaller p-value or more analyses adds no extra points. Monthly completion dates use their full month interval. Future, missing or stale timestamps earn no freshness points. These weights rank research work and are not calibrated clinical strength, success or approval probabilities.

Completed/inactive studies, registry-posted results, exact-program issuer-announced readouts, known inactive listings, invalid provenance and known non-pivotal safety/open-label studies receive **priority 0 and no active rank**, with an explicit exclusion reason. Zero is a scope classification, not a clinical failure. Missing data earns no readiness points and generates review actions. Registry activity alone does not confirm issuer-unreleased status. The separate clinical scores remain blank until their existing source-review requirements pass. The next-ten manual scoring worklist uses the same priority score and global rank.

## Phase 2 p-values → Phase 3 pre-readout evidence (not calibrated PoS)

Open **PDUFA → PRE PHASE 3** for the $300M–$10B active standalone Phase 3 candidate screen. The view now lists Phase 2 **PRIMARY** p-value analyses only when the Phase 2 NCT is explicitly linked to that Phase 3 program, the ticker matches, and the p was actually observed no later than the assessment cutoff. It shows the original Phase 2 registry result-posted date, the **first date the system verified that p-value**, days elapsed since that verification, and the original ClinicalTrials.gov study source. The verified-observation date—not the possibly earlier registry post date—is the safe historical cutoff.

The scheduled collector is `scripts/phase2_pre_readout_pvalues_intake.py`, running at **7:00 AM Pacific** via `.github/workflows/phase2-pre-readout-p.yml`. Evidence is append-only by analyzed endpoint/comparison/value so future changes don't overwrite the original first-seen observation. Status is persisted to `data/phase2_p_intake_status.json`; a missing p remains unverified, never interpreted as a failed Phase 2 trial.

**Do not confuse these:** (a) a Phase 2 primary p-value, (b) the separate Phase 3 design metadata/data coverage score, (c) the 100-point analyst-reviewed clinical evidence rubric, and (d) a statistically calibrated Phase 3 probability of success. A significant Phase 2 p-value does not alone establish clinical relevance, endpoint multiplicity, safety, efficacy replication, or Phase 3 success. The Phase 3 success probability stays blank until independent calibration with pre-cutoff snapshots and untouched historical outcomes. The 100-point analyst score remains blank until all six dated evidence areas and an issuer-unreleased confirmation are documented.


Streamlit presentation layer for the PDUFA clinical and trading research, calendar, and GEM survey system.

## GEM — single master stock list (October 13, 2026)

Under **PDUFA → SCANS → GEM**, Phase 3, Post-Financing and PDUFA
are now **one stock-program table** named **GEM**. One row is retained for
each saved exact ticker/drug/event, with a descriptive **GEM Stage**, two
source-verification statuses, and a single **GEM Rank / GEM Score /100**.
Eligible candidates appear first, then Phase 3 watches and unverified research
rows. Filter by eligibility, lifecycle stage or ticker/drug, and export every
matching row through **EXPORT GEM MASTER LIST**.

Only **released, source-verified Phase 3 results** and **an independently verified
second post-readout financing close** unlock the GEM ranking. PDUFA within 90
days determines only the visible PDUFA *stage*, never an eligibility gate; a
PDUFA −3 date triggers an exit-risk warning. Cash runway, dilution, price/volume,
13F holdings, insider transactions, and regulatory timing remain ranking/risk
inputs, not extra entry benchmarks. The old three independent stage research
rubrics remain in the source audit for historical compatibility and diagnostics;
their separate stock lists and stage tabs are no longer rendered. The underlying
nightly scan collection and 11-survey inventory are preserved.


## Navigation
- **PDUFA → PIPELINE:** The single combined research workflow: current-stage and PDUFA-window selectors, stage/date count charts, the matching trial table (both selectors plus SHOW required), PDUFA countdown, ticker Watchlist management, and Watchlist → Analysis → Invest promotion. Technical ENTRY/EXIT indicators, FDA approval evidence, and second-financing fields remain available here. The separate PDUFA WORKBENCH submenu is removed, while all of its useful tools remain in PIPELINE. Data processing and internal source labels are unchanged.
- **PDUFA → POST PHASE 3:** The former TODAY reporting is here. Latest intake status appears immediately; select **SHOW POST PHASE 3 DAILY REPORT** to load yesterday’s source-linked Phase 3 posts, cumulative Phase 3 result records, financing evidence, ticker Watchlist management, and CSV export. Loading the large report on demand keeps the PIPELINE view responsive. Collectors and source-data files run independently of the UI.
- **PDUFA → PRE PHASE 3:** Shows **ALL TRIALS at the very top of the screen**, before the clinical review and evidence uploader, in a visible research table, with optional 90/180/365-day registry primary-completion windows, a separate ticker watchlist and CSV export. Candidate discovery stays visible when the exact-NCT protocol check is older than two days: such leads are labeled **RECHECK REQUIRED** instead of silently disappearing; confirmed stopped trials and posted registry results are excluded when exact-NCT evidence is present. The separate strictly verified pre-readout queue still requires a fresh protocol, and issuer readout status remains unverified. Every candidate row now displays **PRE PHASE 3 Score /100** (Phase 2 clinical evidence /25 plus Phase 3 pre-readout evidence /75), the independent score status, and separate documented-input coverage / design-safeguards figures. A clinical score remains blank/NOT SCORED until the exact-NCT, before-cutoff, issuer-unreleased and six-domain clinical reviews pass; coverage is not a trial-success probability. The registry's primary-completion dates are not confirmed company readout dates. All issuer release timing, financing, liquidity, and entry checks remain unverified.  Submenu immediately beside PIPELINE for linked Phase 2 primary p-values, the combined pre-readout research score, Phase 3 design coverage, missing inputs, evidence import, and CSV exports. It uses only information available before the Phase 3 readout.
- **Top-level navigation:** PDUFA, SCANS (24-hour GitHub scan activity), and 2. PDUFA CALENDAR. The PDUFA subtabs are GEM, PIPELINE, PRE PHASE 3, POST PHASE 3, SCANS (source audits and controls), and WT (Watchlist/Trading).
- **Retired:** The standalone 9. PREDICTION ENGINE page, its Match Optimizer page and the GEM approval-probability survey are no longer displayed. Previous page bookmarks redirect to PDUFA → PIPELINE. Existing model inputs, frozen historical datasets, live PDUFA regulatory fields and historical scripts are preserved for audit/recovery; they are not the GEM trading eligibility gates. GEM SCANS presents 11 numbered surveys, with BiopharmaWatch comparison now #11.
- **Primary landing page:** PDUFA is the first main navigation item and its first/default submenu is PIPELINE. Clicking back into PDUFA from another main page selects PIPELINE, while PRE PHASE 3 and POST PHASE 3 remain accessible.

## Visible approval probabilities
The user-facing probability display is intentionally limited to two columns:

- **Probability of Approval % — Public**: public-evidence-only probability.
- **Probability of Approval % — All Sources**: composite requiring internal/model, public-only, and BiopharmaWatch probability inputs.

Internal component scores may remain in backend validation logic but are not separate user-facing probability columns.

## Data
- `data/pdufa_candidates.csv` — saved/live PDUFA event feed.
- `data/prediction_engine_history.csv` — historical model/validation cohort.
- `data/prediction_engine_audit.csv` — event/date/leakage audit state.
- `data/prediction_engine_rescore_queue.csv` — canonical rebuild/rescore queue.

ALL PDUFA combines the saved feed with audit-eligible historical events while retaining source identity. Missing values display as Not scored/Not available rather than being converted to zero.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment
Streamlit Community Cloud should deploy branch `main` with `app.py` as the main file.

## Important integration note
The Google Drive/Sheets research collectors and this GitHub/Streamlit repository are separate systems. A production sync/handoff is required to keep event identities, evidence, and probability inputs aligned automatically.


## 100-on-100 precision gate

The repository contains a separate precision-first FDA gate:

- `scripts/fda_100_on_100_gate.py` — rebuilds the strict qualified bucket (typical runtime: under 5 seconds).
- `data/fda_100_on_100_historical.csv` — retrospective qualified historical calls.
- `data/fda_100_on_100_live.csv` — currently qualified prospective calls.
- `data/fda_100_on_100_summary.json` — accuracy/coverage summary.

This layer does **not** force every case into APPROVED/CRL. Strict FDA-V3 REVIEW/NO_CALL cases abstain and are excluded from the qualified bucket. Historical 100% accuracy describes the qualified retrospective subset only; prospective accuracy is reported only after frozen qualified cases receive FDA decisions.

## Recorded historical decisions

Archived historical records retain the fixed 126-case Strict rerun and the assessed-decision table, although the retired Prediction Engine UI no longer displays them. Every historical event has a recorded PASS (APPROVED) or CRL suggestion. Strict qualification is a separate status; `REVIEW — ANALYZED` means the gate withheld qualification while the broad suggestion remains available.

- `data/historical_assessed_decisions.csv` joins the existing broad directions and strict qualified calls by exact event key, with reasoning, evidence gaps and historical MATCH/MISS.
- `data/historical_assessed_decisions_summary.json` summarizes the same rows.
- `scripts/historical_decisions.py` joins the recorded directions and qualifications without reading outcomes to choose directions. Runtime: under 3 seconds.

The strict-gate refresh regenerates this table during surveillance and manual rechecks. The remaining 124 broad cases have 96 approval calls, 28 CRL calls and 119 historical matches. These are retrospective development results. Baseline model probabilities remain in the original model table; a risk-rule override is a direction change, not a newly calibrated probability.

## Strict rerun of all 126 original abstentions

Run `python scripts/fda_100_on_100_gate.py` to reproduce the fixed manifest through the unchanged FDA-V3.2 engine and rebuild the joined app views. The October 6, 2026 run evaluated all 126: **0 APPROVED, 2 CRL, 124 REVIEW**. With the original 20 qualifications, the historical Strict bucket now contains 22 calls.

- `data/strict_historical_126_inputs.json` freezes all 126 identities and outcome-free inputs.
- `data/strict_historical_126_review.csv` records every engine result, evidence cutoff, admitted sources, reasons and missing subchecks.
- `data/strict_historical_126_source_candidates.csv` records retrieved primary-source candidates for all 126; these are explicitly unverified and never populate engine gates.
- `data/strict_historical_126_summary.json` reports run coverage separately from qualification.
- `scripts/strict_historical_review.py` admits only dated, verified, cycle-matched evidence before the actual FDA action. Post-decision documents establish action dates only.

The new calls are model inferences: PRVB's original 2021 teplizumab cycle failed the prespecified commercial-versus-trial PK AUC comparability range ([April 27 sponsor SEC exhibit](https://www.sec.gov/Archives/edgar/data/1695357/000149315221009858/ex99-1.htm)); AKBA's original 2022 vadadustat application included non-dialysis patients, whose PRO2TECT primary safety MACE endpoint failed ([September 3, 2020 sponsor results](https://ir.akebia.com/news-releases/news-release-details/akebia-therapeutics-announces-top-line-results-its-pro2tect), [original application population](https://www.sec.gov/Archives/edgar/data/1517022/000119312521177692/d190142dex991.htm)). The failure is not transferred to the later dialysis-only cycle.

This is a full-cohort source screen and engine run, not 126 exhaustively verified regulatory dossiers. The 124 REVIEW results still need verified evidence; retrieved URLs, positive clinical headlines, unspecified deficiency letters, and inspection completion cannot establish affirmative CMC/facility clearance. No scores or passes were invented. Historical matches are retrospective development results. Tests verify exact coverage, outcome independence, date/identity rejection and separation of review cycles; CI measures misses rather than forbidding them.

## Step 7 — PRE PHASE 3 source-dated live integration (current)

The active PRE PHASE 3 screen in app.py uses step7_live.build_snapshot on saved outputs of scheduled collectors.
It shows a source-health table, exact ticker/NCT Phase 1–3 research records, provider market-cap timestamps,
and separate exact-event financing review. The RELOAD button reloads saved files, not live SEC requests.

GitHub Actions workflow .github/workflows/step7-live-feed.yml runs daily and supports manual launch.
It validates source boundaries and writes data/step7_pre_phase3_feed.csv, data/step7_financing_review.csv
and data/step7_live_status.json. Scanner completion does not establish complete source verification.

Provider-labeled market caps are not independently certified price/volume data. SEC 403 access failures
are explicit blockers. Historical financing status alone does not grant ENTRY READY. Registry primary
completion dates and results-posted dates do not establish a successful corporate Phase 3 readout.
The FDA approval prediction model remains independent of the trading/financing research.

Live-source coverage is PARTIAL. ENTRY READY remains NO pending fresh source-dated Phase 3 efficacy
and effect size/CI, safety, ordered second financing closure, dilution clearance, stable trading base,
and normalized volume verification.

The older PRE PHASE 3 descriptions above predate the active Step 7 view.

The Step 7 clinical table shows source-cited provisional six-domain research
assessments first: TRVI OCEAN-1 **80/100** and LBRX NOVA-2 **72/100**, assessed
as of October 10, 2026. Each includes its domain points, dated evidence,
reasoning and caveats in the table and CSV. Exact-study issuer and publication
evidence resolves NOVA-2's dose-name alias to NOVA-1 NCT06179108 for displaying
the original registry primary p-values. NOVA-3 remains a separate safety trial
with no efficacy score. Stale or future protocol snapshots suppress pilot
scores. These assessments never satisfy the independently reviewed score or
trading entry gates; the completion checklist retains any remaining blockers.

`data/phase_pipeline_listing_exclusions.json` records dated exchange notices
for retired listings, matched to the exact registry company and CIK. Nasdaq's
September 23 merger-closure notice for TBPH makes its September 24 suspension
explicit. The active quote collector excludes that listing, retains the
historical trial and leaves market cap blank. The dashboard can resolve only
a complete scan's fully accounted-for quote warning; registry errors, unknown
missing quotes and original collector timestamps are preserved. Listing status
and the exchange source appear in the research table and CSV. This clears the
TBPH quote-coverage blocker without granting a clinical score or trading entry.


## GEM candidate profile entry/exit scoring (October 14, 2026)

The #1-GEM nested stock profile and PDUFA → SCANS → GEM master grid now
show **three distinct values**: the preserved GEM Quality /100 (clinical and
funding research ranking), a **provisional Entry Score /100** (higher is
stronger), and a **provisional Exit Risk /100** (higher is more concerning).
Each trade score has an independent **Coverage /100**, status, and per-factor
breakdown in the profile and CSV. Coverage means the weight supported by
current observations; it is NOT predictive confidence. Points for missing
source inputs stay unearned and unavailable, not treated as negative findings.

Entry rubric: closing-price trend 25; relative-volume and dollar liquidity 20;
closing-price location proxies 20; actual stop/spread/ATR/reward-risk 20
(**unavailable in the current close-only saved market feed**); verified PDUFA
timing 15. Exit risk rubric: closing-support break 15; actual position-specific
stop 15 (**unavailable**); verified FDA deadline 25; source-documented clinical
and financing deterioration 20; weakening trend 15; selling pressure/liquidity
10. Stale saved EOD, partial clinical feed, or non-current SEC source checks
withhold both scores. Less than 50/100 available weight also withholds a
numeric value. Unverified two-benchmark research rows have **no Entry Score**,
though a provisional, no-position-assumed Exit Risk may be visible. The PDUFA
minus-three-days boundary, actual negative FDA news and support breakdown
warnings supersede numeric scores. This is a heuristic research display, not
a validated or backtested trading strategy or permission to buy or sell.

Benchmark 1 is now **source-verified positive Phase 3 results**: negative and
outcome-unknown published readouts do NOT qualify for Verified GEM ranking.
Benchmark 2 remains the distinct SEC-documented second post-readout close.
No third eligibility benchmark was added.

## GEM per-stock entry/exit monitor and site-health audit (October 14, 2026)

The #1-GEM nested master list and PDUFA → SCANS → GEM table display a separate **Trade assessment**, technical summary, and EOD chart per exact program. The master-table CSV includes those columns. This research-only view uses source-labeled saved close/volume data; it does **not** submit broker orders or treat GEM qualification, RSI, volume or a research rank as an approved BUY. Missing or stale daily bars, 50-day history, OHLC-based ATR, intraday VWAP, bid/ask, and position-specific stop/reward-to-risk remain explicitly unavailable. The original two source-verified GEM benchmarks are unchanged. The existing manual PDUFA −3-calendar-day exit warning remains separate from actual trading fills.

`Live Streamlit Cloud Browser Audit` (`.github/workflows/live-streamlit-audit.yml`) opens the deployed app in Chrome and checks all six current PDUFA subtabs, the top-level SCANS activity page, Calendar, and mobile-width navigation. It writes a JSON status and screenshots as workflow artifacts. Checks use the **current** GEM and navigation labels, not retired Prediction Engine or pre-merge labels. A deployed Step 7 cache rejection fails the PRE PHASE 3 check; stale source warnings remain visible but do not become verified trading evidence. CI/unit tests run against repository code, while the live browser workflow is a separate deployment verification. A successful CI run alone is not proof Streamlit Cloud deployed the new revision.
