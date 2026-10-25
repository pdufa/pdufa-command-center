# Scientific Assessment: Quantitative registry-result inventory

## Purpose

The isolated review platform now extracts bounded, verbatim **reported** numbers from the previously archived ClinicalTrials.gov API v2 JSON. This complements, but does not change, the 20-stage source-coverage map or six-domain evidence-gated scientific scoring.

The implementation uses the exact NCT identifier, validates decompression and SHA-256, verifies the source NCT identity, and **never** makes a new network request when a user inspects the scientific panel.

## Values exposed

- Outcome type, title, time frame, result group IDs and titles.
- Reported statistical test and parameter type, estimate, p-value **as written**, confidence interval percentage/sides/lower/upper. For example, `<0.001` remains a reported bound, not the exact number `0.001`.
- Serious and other adverse-event term counts, group IDs, reported `numAffected`, `numAtRisk`, and `numEvents`, without deriving risk ratios or merging incomparable arms.
- Exact array-aware JSON provenance paths for each outcome, analysis, and serious adverse-event entry.

### Limits and error handling

A single response shows no more than 30 outcomes (up to five analyses per outcome, 12 groups per outcome), 20 serious-event terms, 20 other-event terms, and 12 statistics rows per event. Responses include original totals, displayed totals, and an explicit truncation flag. Numeric strings must parse to finite numbers; malformed values, infinities and NaNs remain missing instead of being coerced into zero.

Empty/missing results produce an empty list, **not** a negative study result. A corrupt, oversized, or wrong-NCT archive returns no quantitative results. No private API key is included in UI source code or logs.

## Crucial scientific limits

These are claims recorded in a source registry snapshot, not independently adjudicated efficacy and safety. Statistical significance depends on prespecification, multiplicity, populations, the analysis plan, comparator direction, censoring and missing data. Safety proportions require denominator, exposure, attribution and adverse-event ascertainment review. This implementation intentionally does **not** declare positive/negative trial, FDA approval odds, regulatory readiness, a scientific score, or a pass/fail grade.

To reach reliable clinical conclusions for **GEM JR, GEM and WT shortlisted trials**, the next stage must reconcile the archived numerical entries with protocols, statistical analysis plans, peer-reviewed publications, regulatory submissions and FDA review evidence. Any resulting scientific grades must carry explicit source citations, independent validation and uncertainty. Screening classifications and original GEM JR/GEM FS/FA preset associations remain untouched.

## Review

Open `/scientific-assessment/batches`, enter the isolated internal API key, and inspect an exact archived NCT ID. Expand the "Reported outcomes and safety — not independently verified" section after inspection. The posted values are a snapshot: inspect the linked ClinicalTrials.gov study for newer revisions before drawing any conclusion.

Everything is **read-only** with respect to the scientific archive. No bulk trials, background scans, trading orders, or production deployments are introduced.
