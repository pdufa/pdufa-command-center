# PDUFA Command Center

Streamlit presentation layer for the PDUFA research, calendar, and prediction system.

## Navigation
- **PIPELINE → TRIALS & DATES:** Current-stage and PDUFA-window selectors, stage/date count charts, and the matching trials table. Both selectors and an explicit SHOW click are required to populate the table.
- **PIPELINE → PDUFA WORKBENCH:** Preserves the source-enriched master processing and PDUFA countdown, with compact ticker-based Watchlist management followed by Watchlist, Analysis, and Invest tables. The oversized Master Table display and standalone Watchlist page are removed; source data and internal master-transfer labels remain intact.
- **TODAY:** Phase 3 intake, financing and PDUFA update summary.
- **Additional pages:** Disease & Market Horizon, Strategy, PDUFA Calendar, FDA Decision, Scans, Recheck, Prediction Engine, Match Optimizer, and Plan.

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
