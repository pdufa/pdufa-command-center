# PDUFA Command Center

## Unified display inside POST PHASE 3 (October 11, 2026)

**PDUFA → POST PHASE 3** contains the combined clinical/pipeline display and
all three trading sections: discovery/qualification, reported-position
monitoring, and historical entry/exit research. **Focus ticker** links the
clinical table, PDUFA timing, candidate queue, position table and historical
research. The default **All tickers** keeps the full workspace available.
The existing columns, source audits, score models, financing colors, sort
controls and CSV exports are retained. Portfolio totals and exit alerts still
cover the complete uploaded journal when its displayed rows are ticker-filtered.

**UNIFIED OVERVIEW** remains in the submenu but has no content. Its former
display and exports are now available inside POST PHASE 3. PIPELINE and
PRE PHASE 3 retain their existing separate workflows.

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


Streamlit presentation layer for the PDUFA research, calendar, and prediction system.

## Navigation
- **PDUFA → PIPELINE:** The single combined research workflow: current-stage and PDUFA-window selectors, stage/date count charts, the matching trial table (both selectors plus SHOW required), PDUFA countdown, ticker Watchlist management, and Watchlist → Analysis → Invest promotion. Technical ENTRY/EXIT indicators, FDA approval evidence, and second-financing fields remain available here. The separate PDUFA WORKBENCH submenu is removed, while all of its useful tools remain in PIPELINE. Data processing and internal source labels are unchanged.
- **PDUFA → POST PHASE 3:** The former TODAY reporting is here. Latest intake status appears immediately; select **SHOW POST PHASE 3 DAILY REPORT** to load yesterday’s source-linked Phase 3 posts, cumulative Phase 3 result records, financing evidence, ticker Watchlist management, and CSV export. Loading the large report on demand keeps the PIPELINE view responsive. Collectors and source-data files run independently of the UI.
- **PDUFA → PRE PHASE 3:** Shows **ALL TRIALS at the very top of the screen**, before the clinical review and evidence uploader, in a visible research table, with optional 90/180/365-day registry primary-completion windows, a separate ticker watchlist and CSV export. Candidate discovery stays visible when the exact-NCT protocol check is older than two days: such leads are labeled **RECHECK REQUIRED** instead of silently disappearing; confirmed stopped trials and posted registry results are excluded when exact-NCT evidence is present. The separate strictly verified pre-readout queue still requires a fresh protocol, and issuer readout status remains unverified. Every candidate row now displays **PRE PHASE 3 Score /100** (Phase 2 clinical evidence /25 plus Phase 3 pre-readout evidence /75), the independent score status, and separate documented-input coverage / design-safeguards figures. A clinical score remains blank/NOT SCORED until the exact-NCT, before-cutoff, issuer-unreleased and six-domain clinical reviews pass; coverage is not a trial-success probability. The registry's primary-completion dates are not confirmed company readout dates. All issuer release timing, financing, liquidity, and entry checks remain unverified.  Submenu immediately beside PIPELINE for linked Phase 2 primary p-values, the combined pre-readout research score, Phase 3 design coverage, missing inputs, evidence import, and CSV exports. It uses only information available before the Phase 3 readout.
- **Additional pages:** Disease & Market Horizon, Strategy, PDUFA Calendar, FDA Decision, Scans, Recheck, Prediction Engine, and Plan.
- **Prediction Engine → PREDICTIONS / HISTORICAL MATCH VALIDATION:** All former Match Optimizer functionality lives inside Prediction Engine as its second nested tab: FDA-V3 strict/directional benchmarks, cohort selection, accuracy/coverage threshold tuning, miss analysis, untouched-year holdout validation, and prospective gate recommendations. Frozen historical predictions and underlying datasets are retained unchanged. Former `10. MATCH OPTIMIZER` sessions redirect to the embedded validation tab.
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

Prediction Engine starts with the fixed 126-case Strict rerun, followed by an assessed-decision table. Every historical event has a recorded PASS (APPROVED) or CRL suggestion. Strict qualification is a separate status; `REVIEW — ANALYZED` means the gate withheld qualification while the broad suggestion remains available.

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
