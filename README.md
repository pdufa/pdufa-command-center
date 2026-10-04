# PDUFA Command Center

Graphical Streamlit presentation layer for the PDUFA research and prediction system.

## Current front page
- Upcoming PDUFA candidate cards
- 7/30/60/90-day horizon filters
- Ticker/drug/company/indication search
- PASSING / REJECTING / REVIEW signal
- Estimated approval probability and confidence
- Separate Science & Efficacy, Regulatory, Safety and CMC scores
- Expandable candidate intelligence
- Trading intelligence kept separate from FDA probability

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Deploy this repository with Streamlit Community Cloud and set the main file to `app.py`.

## Data
- `data/pdufa_candidates.csv` is the current saved/live PDUFA event feed.
- Prediction Engine history, audit, and rescore files are loaded from `data/`.
- ALL PDUFA combines the saved feed with eligible historical Prediction Engine cases while keeping the record source visible.
- Historical rows excluded by the audit are not silently restored to the master list.
- Missing company/drug/indication details in validation-only historical files are labeled as not captured rather than invented.
