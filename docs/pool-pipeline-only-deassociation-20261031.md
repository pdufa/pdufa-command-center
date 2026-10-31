# Pool → Pipeline only: retire GEM JR and GEM associations

## Decision, October 31, 2026

The **active screening architecture** is now intended to be:

```
POOL (all available restriction definitions; no stage membership)
   |
   +-- assign/reorder/enable rules
   v
PIPELINE (public companies, $300M–$10B, post-Phase-3 evidence, saved restrictions)
   |
   +-- evidence sufficiency / source provenance / analysis
   v
SCIENCE → OUTCOME → MAIN → RESULTS
```

GEM JR, GEM and their FS/FA **are not intermediary qualification stages** for this new Pipeline analysis. There must be no `GEM_JR`/`GEM` priority, `additionalStages` membership or `gem_jr_source` dependency in the active Pool/Pipeline configuration. Generic thresholds previously presented in GEM may remain available as independent Pool options, **not pre-enabled**. The market cap limits of **$300 million to $10 billion** remain unchanged, as do public-company and Phase-3 eligibility criteria. Do **not** change Pipeline restrictions while doing this separation.

## Technical discovery

The existing published Streamlit and new-platform dashboard contain distinct GEM JR/GEM stage-member source ledgers, FS/FA presets, stage scans, React stage tabs, an older 41-rule catalog, and browser-saved values. A bulk deletion of those tables or workflows would destroy historical auditability and could corrupt unrelated dashboards. Thus:

1. Introduce a separate, versioned **active** Pool/Pipeline restriction configuration, loadable from saved legacy settings but never overwriting their browser storage. Strip all GEM JR/GEM associations, priorities, and additional stages; never silently promote a GEM-only rule into the Pipeline. Retain its numerical threshold as an **inactive Pool option**.
2. Hide/retire GEM JR/GEM restriction lists and presets from **active** navigation. Replace the restriction editor with Pool (unassigned) and Pipeline (assigned) only; maintain filterability and per-rule priority. Exclude the old `gem_jr_source` rule because it is intrinsically tied to the retired stage.
3. Ensure user-defined saved Pipeline restrictions, min/max cap, eligibility proof and evidence verdict remain unchanged; an unavailable source continues to be UNKNOWN, not PASS.
4. Remove Pipeline evaluation dependencies on GEM stage membership or FS/FA presets. Existing historical GEM scan outputs must not be ingested into this independent Pipeline candidate universe.
5. Keep read-only old GEM history, original snapshots, and FS/FA preset source files preserved for provenance and rollback; do not run/delete old scanners until a separately reviewed scheduling migration is established. Hiding legacy screens is not sufficient to retire live cron jobs.
6. Exercise frontend state migration, restriction counts, independent screening, persistent settings, disabled GEM routes, and identical Pipeline results on archived fixtures before production deployment.

## Implementation status

- Added and tested a pure `detachGemAssociations` transformation on a feature branch: strips GEM/JR stages, preserves Pipeline priorities and numeric values, marks former GEM-only rules as unassigned/inactive Pool choices, and omits dependent `gem_jr_source`.
- **Not yet connected to live frontend, saved presets, scanner execution or production site** at this phase. As of this document, **GEM JR/GEM tabs and schedules remain in service**; do not call the requested decoupling fully completed.

## Safety / acceptance criteria

- Active Pipeline catalog contains **no** GEM/JR member or FS/FA preset association.
- Pool is a **definition library**, not a list of passed candidates. Pipeline membership requires independently checked eligibility, never an inferred promotion.
- Tests confirm 300/10000 ($M) cap defaults, exact Pipeline values unchanged, 0 GEM/JR stage assignments, original data not overwritten, and no silent GEM-only rule promotion.
- Historical trial counts, stage restrictions, and scan results are not silently rewritten.
- Review changes separately from staging FDA fix and transfer PR #527. No production cutover until all end-to-end and data-migration acceptance tests pass.
