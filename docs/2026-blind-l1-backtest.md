# 2026 historical FDA Level-1 backtest — data and execution contract

## Status
The historical cohort is **not loaded**. The earlier reported 183 events is a
provisional source count, not a validated dataset. Reconcile live source totals
with a dated snapshot and keep an explicit inclusion/exclusion ledger.

## Inputs
Use two distinct CSVs. Never give the prediction runner the outcomes CSV.

**blind_events.csv** columns:
`event_id,ticker,drug,indication,decision_date,evidence_asof,submission_accepted,pivotal_primary_endpoint_met,major_safety_signal,documented_regulatory_deficiency`

Flags: `yes`, `no`, or blank (unknown). `evidence_asof` must be at
least 30 days before `decision_date`. The four flags must be documented using
source publications dated on or before the cutoff. Missing information yields
ABSTAIN rather than a fabricated prediction.

**outcomes.csv** columns:
`event_id,actual_outcome`

Allowed outcomes: APPROVE or CRL. Exclude or separately report withdrawals,
delays, and events lacking a verified binary FDA decision.

## Commands
```bash
python scripts/blind_l1_2026_backtest.py prepare \
  --events blind_events.csv --output locked_l1.json --cutoff-days 30
# Commit and timestamp locked_l1.json BEFORE granting the scoring job access
# to the independently verified outcomes file.
python scripts/blind_l1_2026_backtest.py score \
  --locked locked_l1.json --outcomes outcomes.csv --output scored_l1.csv
```

## Anti-leakage and interpretation
- Do not supply outcome-bearing fields, outcome URLs, post-cutoff sources, or
  descriptions that imply the eventual decision to the prediction process.
- Review provenance of every feature; the program checks `evidence_asof` but
  cannot independently verify the publication dates of every underlying claim.
- A source record's decision date may differ from the PDUFA goal date. Keep
  both in the source ledger; the protocol currently uses decision date.
- This gate-based L1 protocol is a **new research baseline**, not proof that
  it matches any previously deployed Level-1 engine. Before comparing L1–L20,
  reconcile its scoring rubric with the dashboard's canonical definitions.
- Report accuracy only on non-abstentions, together with coverage, abstentions,
  confusion matrix, and counts of excluded records.
- For the market-cap subset, specify whether capitalization is measured at
  decision date or at another fixed date. Do not infer it from ticker size.
- No production merge or deployment without explicit approval.

## Remaining work
1. Obtain source archive and snapshot with retrieval timestamp.
2. Reconcile all event IDs, duplicate applications, dates, and source totals.
3. Capture pre-cutoff evidence and primary source URLs per flag.
4. Independently verify actual FDA decisions.
5. Unit-test the runner and validate against a small, manually audited sample.
6. Lock full predictions, unblind, score, and publish the full row-level report.
