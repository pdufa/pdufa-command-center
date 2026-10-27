# Master trial CSV evidence coverage — 2026-10-27

Source: `data/all_phase_trials.csv` on `main`, Git blob `1036b93f85da056564c91ba48a15eb834754d2ae`.

Scope: **CSV field coverage only**, not live PostgreSQL reconciliation, evidence verification, eligibility determination, or scientific scoring.

| Measure | Count |
|---|---:|
| Rows | 11,601 |
| Unique valid NCT IDs | 11,601 |
| Duplicate NCT IDs | 0 |
| Rows with expected 16 CSV fields | 11,601 |
| Distinct tickers | 448 |
| Phase 3 | 4,316 |
| Phase 2/3 | 291 |
| HTTP(S) source URL present | 11,601 |

## Missing or NA field values

| Field | Missing |
|---|---:|
| phase | 692 |
| drug | 463 |
| intervention_type | 95 |
| route | 5,949 |
| indication | 3 |
| start_date | 62 |
| primary_completion | 242 |
| study_completion | 250 |
| results_posted | 6,685 |

`results_posted` is a CSV field; blank values do **not** prove no results were published. URLs were syntactically checked for HTTP(S), not fetched or authenticated. The archive may be a different snapshot from the Render PostgreSQL master table, which remains unverified.

**Gates:** scientific analysis complete = false; predictive model validated = false; trade authorized = false. Preserve GEM JR/GEM FS/FA associations.
