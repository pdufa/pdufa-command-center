# KEYNOTE-024 trial-to-PDUFA historical provenance audit

**Historical exact-NCT pilot:** NCT02142738 (MK-3475-024, pembrolizumab versus chemotherapy in PD-L1 TPS ≥50% metastatic NSCLC).

**Critical distinction:** This is a reconstruction after learning the actual 2016 clinical and FDA outcome. It is **not** a model that predicted approval prospectively. The dated sources have different knowledge/verification timing and cannot be treated as if all were available before June 2016.

## Verified timeline: ten dated milestones

| Event date | What happened/was planned | Source publication/entry date | Evidence status |
|---|---|---|---|
| 2014-06-19 | Dutch EU trial register first entry and authority authorization | 2014-06-19 | Record date verified; current displayed endpoint-field amendment versions not authenticated |
| 2015-05-20 | ASCO published KEYNOTE-024 study-in-progress design | 2015-05-20 | Contemporaneous public description; not signed SAP |
| 2016-05-09 | Original second interim PFS/OS cutoff | 2016-10-08 | Retrospectively documented in NEJM |
| 2016-06-08 | External DMC reviewed second interim results | 2016-10-08 | NEJM says committee reviewed June 8 and June 14; actual meeting minutes not independently retrieved |
| 2016-06-14 | External DMC reviewed second interim results again | 2016-10-08 | NEJM retrospectively documents date, **not** exact signature/time of DMC recommendation |
| 2016-06-16 | Merck publicly announced DMC recommendation to stop and offer crossover | 2016-06-16 | Contemporaneous corporate release; 5:45 a.m. EDT |
| 2016-09-07 | Merck publicly announced FDA accepted first-line sBLA, granted Priority Review, set Dec 24 PDUFA goal | 2016-09-07 | Contemporaneous announcement, not complete internal FDA correspondence |
| 2016-10-08 | Original NEJM results published online | 2016-10-08 | Retrospective journal report, original randomized clinical efficacy |
| 2016-10-24 | FDA approved first-line pembrolizumab for high-PD-L1 metastatic NSCLC based on KEYNOTE-024 | 2016-11-17 (NCI article) | U.S. government retrospective confirmation; first-line FDA action **before** PDUFA target |
| 2016-12-24 | Previously announced PDUFA goal date for first-line application | announced Sept 7 | **Target only**; not another FDA action, and not a missed deadline |

Original sources:

- [2016 NEJM randomized KEYNOTE-024 article](https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774): DMC reviews June 8 and June 14, second interim cutoff May 9, 189 PFS events, 108 OS deaths, recommendation and multiplicity-adjusted alpha. Full NEJM article/supplement retrieval remains partially access restricted; published text reports dates, but signed DMC minutes are not independently inspected.
- [Merck June 16 contemporaneous release](https://www.merck.com/news/mercks-keytruda-pembrolizumab-demonstrates-superior-progression-free-and-overall-survival-compared-to-chemotherapy-as-first-line-treatment-in-patients-with-advanced-non-small-cel/): DMC stopping recommendation announced (not original minutes).
- [Merck September 7 FDA priority review release](https://www.merck.com/news/fda-accepts-supplemental-biologics-license-application-assigns-priority-review-and-grants-breakthrough-therapy-designation-to-mercks-keytruda-pembrolizumab-for-first-line-treatment-o/): first-line PDUFA goal 2016-12-24.
- [NCI November 17 government approval article](https://www.cancer.gov/news-events/cancer-currents-blog/2016/fda-atezolizumab-pembrolizumab-lung): FDA first-line approval occurred 2016-10-24, same day as separate second-line conversion.
- [2017 FDA-authored efficacy summary](https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/): OS interim p=0.005 against allocated alpha 0.0118; this is not proof we reanalyzed the signed original alpha-spending plan.

## Avoiding false equivalences

1. **Data cutoff vs DMC:** May 9 is the scientific data cutoff; June 8 and June 14 are retrospectively reported DMC review days; June 16 is the *date of public corporate disclosure*. Do not invent a specific signed recommendation date.
2. **Contemporaneous vs retrospective evidence:** A published paper may describe an earlier meeting, but does not establish all committee minutes were independently inspected. Record both event and source-publication dates.
3. **Regulatory goal vs action:** December 24 is an anticipated first-line PDUFA decision goal announced September 7. The observed first-line FDA approval was October 24. One must **never** set a prior probability using the outcome already known in hindsight.
4. **First-line vs second-line:** KEYNOTE-024 supported October 24 **first-line** PD-L1-high NSCLC approval. On the same day FDA also converted an earlier **second-line** NSCLC accelerated indication, supported by KEYNOTE-010. Do not double-count the approval as two KEYNOTE-024 events.
5. **Protocol amendment identity:** The later 2017 Japan-only protocol/SAP does not authenticate the original May 2016 signed version. EU registry field revision dates, complete regulatory dossier and DMC decision minutes remain unverified.

## Software boundary and source controls

- Exact-NCT, read-only `keynote024_historical_pdufa_timeline` produces ten immutable sourced event records plus first-line sBLA 125514/S-12 timeline and explicit uncertainty/anti-forecast indicators.
- Protected `GET /api/scientific-assessment/pilot/keynote024` includes optional `historicalRegulatoryTimeline` after archival source checksum verification and prior scientifically unscored source checks.
- Frontend validator requires ten exact dated events, allowed source URLs, distinct DMC and press-release provenance, actual FDA October 24 action separate from December 24 target, and preserved null scores/FDA probability.
- Responsive visual review panel shows four headline milestones and ten expandable individual dated source records with direct citations.
- No database writes, new external downloads, scanner jobs, trading actions, live-system routing, GEM/WT/PIPELINE ranking changes, FS/FA preset edits, clinical efficacy score or prospective FDA forecast.

**Scientific Input Readiness remains FAIL / Reluctance remains HIGH.**

Next evidence-bearing research: retrieve original 2016-or-earlier signed protocol and SAP amendments; obtain actual DMC minutes/committee stop recommendation, reconstruct interim multiplicity/alpha and exact cutoffs, inspect FDA original sBLA 125514/S-12 clinical/statistical and CMC reviews, and independently reconcile AE denominators, causality and treatment switching.
