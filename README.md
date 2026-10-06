# PDUFA Command Center

Streamlit presentation layer for the PDUFA research, calendar, and prediction system.

## Navigation
1. ALL PDUFA — configurable master event table with direct event detail links
2. MARKET CAP GROUPS — event views grouped through the $300M–$10B range
3. CALENDAR — next-four-week counts plus monthly event calendar
4. PREDICTION ENGINE — historical validation, audit/rescore status, direction testing, and prospective gate view

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

Prediction Engine starts with an assessed-decision table. Every historical event has a recorded PASS (APPROVED) or CRL suggestion. Strict qualification is a separate status; `REVIEW — ANALYZED` means the gate withheld qualification while the broad suggestion remains available.

- `data/historical_assessed_decisions.csv` joins the existing broad directions and strict qualified calls by exact event key, with reasoning, evidence gaps and historical MATCH/MISS.
- `data/historical_assessed_decisions_summary.json` summarizes the same rows.
- `scripts/historical_decisions.py` builds this view without rescoring, changing model versions, or reading outcomes to choose directions. Runtime: under 3 seconds.

The strict-gate refresh regenerates this table during surveillance and manual rechecks. The current 126 broad cases have 96 approval calls, 30 CRL calls and 121 historical matches. These are retrospective development results. Baseline model probabilities remain in the original model table; a risk-rule override is a direction change, not a newly calibrated probability.
