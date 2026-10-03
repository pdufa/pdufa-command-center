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
The included CSV contains a DEMO row only. The next integration step is to replace it with an automated export from the existing Google/Colab PDUFA research pipeline. Historical research files are not modified by this app.
