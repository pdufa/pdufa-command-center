# Outcome-source audit — 2026-11-18

## Critical correction
The earlier file `data/backtest/2026-public-outcomes-quarantine-sample-2026-11-18.csv` is **NOT VERIFIED** and must not be used for scoring, training, or calculating accuracy. It contains an incorrect sponsor/ticker attribution for neladalkib (listed GSK; FDA approval news identifies Nuvalent/NUVL), and action dates differ from current published records for ivonescimab and pimicotinib. Its `OUTCOME_ONLY_NOT_BLIND_READY` status remains applicable. Quarantine it pending record-by-record official FDA confirmation.

## Confirmed FDA scope caveat
FDA's Novel Drug Approvals for 2026 list has 50 entries through November 13, 2026; it is only a *subset* of all CDER approval actions, not the 196-event requested PDUFA universe. See https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026 .
The third-party decision calendar at https://www.pdufa.bio/fda-decisions-today lists November 17 neladalkib and November 15 ivonescimab, but its sponsor mapping for neladalkib appears inconsistent with the Nuvalent approval report. Treat it as a discovery index, not the authoritative FDA outcome source.

## Required actions before backtesting
1. Reconcile 196 target events by application/action ID; distinguish original NDA/BLA, efficacy supplements, and repeat PDUFA dates.
2. Fetch official FDA action letters or Drugs@FDA/openFDA entries for each actual outcome, including date and sponsor.
3. Keep the outcome ledger isolated from the dated predecision evidence ledger; do not derive predecision gates from FDA action reviews or postdecision reporting.
4. Validate level definitions against project requirements before applying generic L02–L06 gate rules.
5. Lock historical predictions in a separate commit before any score joins. Report coverage as well as accuracy.

Current verified scored historical cases: zero. No accuracy claim warranted.
