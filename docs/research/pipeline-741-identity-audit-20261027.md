# Frozen Pipeline census identity audit — 2026-10-27

Source: `data/snapshots/phase3-census-2026-10-26/phase3_all_years_300m_10b_trials.csv` at development branch, inspected on 2026-10-27.

| Metric | Count |
|---|---:|
| CSV data rows | 741 |
| Unique NCT IDs | 741 |
| Missing / malformed NCT IDs | 0 |
| Repeated NCT IDs | 0 |

Method: read the `nct_id` field of each data row; require exact `^NCT[0-9]{8}$` and count unique values. This is an **identity-format audit**, not a source-authenticity check or a scientific assessment. No protocol identifiers, trial outcomes, or evidence records were validated.

Scope caveat: this CSV is a **frozen, filtered Pipeline snapshot** and is **not the full approximately 11,000-trial original universe**. The full original census file still needs to be identified and audited before any 11k-wide coverage claim.

No trial data, list restrictions, scan schedules, live services, model validation flags, or trading permissions were modified.
