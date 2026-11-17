# Three primary efficacy endpoints: external statistical evidence cross-check
**Source cutoff:** 2026-11-17. **Scope:** two ABVX Phase 3 ABTECT induction trials and the VERA Phase 3 ORIGIN 3 interim primary endpoint. **Development research only.**

The captured ClinicalTrials.gov source packets have no posted statistical-comparison block for these primary endpoints. This does **not** mean significance is unknown across all sources: the original Abivax sponsor release and the published ORIGIN 3 abstract report comparisons. They must remain separately sourced and must not be labeled as analyses posted in ClinicalTrials.gov.

| Exact trial | Clinical endpoint | Source-reported comparison | Caution |
|---|---|---|---|
| ABVX NCT05507203 ABTECT-1 | Week-8 clinical remission | 50 mg: 69/318 (21.7%) vs placebo 4/158 (2.5%), adjusted delta 19.3 percentage points, P<0.0001; 25 mg: 38/160 (23.8%) vs placebo 4/158, delta 21.4 percentage points, P<0.0001 | Source-reported sponsor Mantel-Haenszel adjusted results, not independent reanalysis |
| ABVX NCT05507216 ABTECT-2 | Week-8 clinical remission | 50 mg: 63/318 (19.8%) vs placebo 10/159 (6.3%), delta 13.4 percentage points, P=0.0001 | 25 mg (18/159; 11.3%) vs placebo 10/159 did **not** reach significance: delta 5.1 points, P=0.1034 |
| VERA NCT04716231 ORIGIN 3 | Week-36 UPCR percentage change | Atacicept 45.7% reduction vs placebo 6.8%, between-arm geometric-mean difference 41.8 percentage points (95% CI 28.9–52.3), P<0.001 | NCT is a **multi-part Phase 2b/3** program; this is the ORIGIN 3 Phase 3 primary, not the earlier ORIGIN 2b week-24 readout |

## Explicit source provenance and blind-historical safeguards
Abivax original results release, July 22, 2025: https://ir.abivax.com/news-releases/news-release-details/abivax-announces-positive-phase-3-results-both-abtect-8-week

Abivax corporate annual filing with model/data handling details:
https://ir.abivax.com/node/12081/html

Vera original NEJM published abstract, November 6, 2025 (DOI 10.1056/NEJMoa2510198):
https://www.nejm.org/doi/full/10.1056/NEJMoa2510198
Original Vera sponsor paper announcement:
https://ir.veratx.com/news-releases/news-release-details/vera-therapeutics-announces-positive-origin-phase-3-data/

**VERA already had an FDA outcome by 2026-11-17.** FDA Purple Book confirms BLA 761486, TRUTAKNA (atacicept-vymj), original approval on **July 7, 2026**, via accelerated approval. This historical outcome must be stored only in a separate outcome/label field, not supplied as a model feature for pre-decision or blind backtests:
https://www.accessdata.fda.gov/scripts/purplebooksearch/index.cfm?blaNo=761486&event=productdetails

**Critical distinction:** accelerated approval for reduction of proteinuria is *not* an FDA determination that long-term kidney-function decline was already proven at the initial approval. The clinical impact and confirmatory evidence require separate review.

The archived study packets' NCT and source receipt SHA-256 are recorded in `research/source-links/FOCUS-ABVX-VERA-external-primary-stats-2026-11-17.json`. Publication timing, comparator, analysis populations, protocol/SAP, multiplicity and safety require review; no scientific score, probability, prospectively blinded prediction, or production write is generated.
