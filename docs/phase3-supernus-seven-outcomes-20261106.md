# Supernus Phase 3 exact-study evidence recovery — 2026-11-06

This batch adds **seven independently linked historical Phase 3 primary outcomes**, sourced to exact sponsor protocol/NCT IDs. It adds **29 question-level factual records** (not predictions), updates the 137-company research queue and partial issuer search log, and preserves the 762 unique trial census and 190-column export.

| NCT | Sponsor protocol | Outcome | Issuer/SEC disclosure |
|---|---|---|---|
| [NCT03247530](https://clinicaltrials.gov/study/NCT03247530) | 812P301 | Primary met | [2018-12-06](https://ir.supernus.com/news-releases/news-release-details/supernus-announces-positive-results-two-phase-iii-studies-spn) |
| [NCT03247517](https://clinicaltrials.gov/study/NCT03247517) | 812P302 | Primary met | [2018-12-20](https://www.sec.gov/Archives/edgar/data/1356576/000110465918074466/a18-41980_1ex99d1.htm) |
| [NCT03247543](https://clinicaltrials.gov/study/NCT03247543) | 812P303 | Primary met | [2018-12-06](https://ir.supernus.com/news-releases/news-release-details/supernus-announces-positive-results-two-phase-iii-studies-spn) |
| [NCT03247556](https://clinicaltrials.gov/study/NCT03247556) | 812P304 | Primary met | [2019-03-28](https://ir.supernus.com/news-releases/news-release-details/supernus-announces-p304-phase-iii-data-confirming-positive) |
| [NCT04016779](https://clinicaltrials.gov/study/NCT04016779) | 812P306 | Primary met | [2020-12-22](https://ir.supernus.com/news-releases/news-release-details/supernus-announces-positive-results-phase-iii-study-spn-812-0) |
| [NCT02618408](https://clinicaltrials.gov/study/NCT02618408) | 810P301 | Primary not met | [2019-11-05](https://supernus.gcs-web.com/news-releases/news-release-details/supernus-announces-third-quarter-2019-financial-results-and) |
| [NCT02618434](https://clinicaltrials.gov/study/NCT02618434) | 810P302 | Primary not met | [2020-02-25](https://ir.supernus.com/node/11506) |

## Critical distinctions

- 812P304: 400 mg met ADHD-RS-5 week-7 primary (p=0.0082); **600 mg did not** (p=0.0712). This is not two separate NCT trials.
- 810P301: interim stage-1 p=0.029 cannot supplant final combined-stage p=0.092. Binary historical endpoint is **NOT MET**.
- 810P302: p=0.961 is **NOT MET**; do not transfer SPN-812 approval facts to SPN-810.
- 812P306: a flexible-dose adult trial, not validation that each fixed adult dose worked.
- P301/P303 2.2%-4.8% adverse-event discontinuation range derives from the two-study disclosure and is not trial-arm exact; preserved as such.
- Trial outcome labels are observed historical results, **not** RAAS prospective scores or current trading recommendations.
- Official source NCT/protocol crosswalk for the four pivotal pediatric studies: [peer-reviewed Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC8563661/). Other exact records crosswalked against ClinicalTrials.gov.
- No FDA application, PDUFA date or approval attribution is inferred from these readouts.

### Follow-on research

Other 12 Supernus census trials remain pending review, including open-label extensions, program-specific terminations and historical formulations. They must not inherit any of these seven outcomes without trial-specific source matching.

## Change integrity
- Study evidence stored in `phase3CompanyWebsiteEvidence20261105.json`.
- Historical primary outcome in `phase3EndpointAdjudications20261105.json`.
- Company research queue/status and issuer audit log updated.
- Regression test protects dose-specific results, final-vs-interim distinctions, unique exact-NCT identity and source provenance.
