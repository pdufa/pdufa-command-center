# Historical trial source recovery — Acadia and Alkermes (2026-11-06)

Scope: six exact-NCT records, 35 documented/interpretation assessment slots, **five endpoint classifications** (one met, one not met, three nonbinary safety extensions) and three historical FDA/NDA trial links to a **single** application program. One trial (ACP-103-014/NCT00658567) remains **unadjudicated** because the FDA lists its formal hypothesis test as N/A following early stopping. Historical observations are not RAAS predictions.

| NCT | Protocol | Outcome | Grounding |
|---|---|---|---|
| NCT00477672 | ACP-103-012 | NOT MET | [Sponsor September 2009 release](https://acadia.com/en-us/media/news-releases/acadia-pharmaceuticals-announces-results-phase-iii-trial); [registry](https://clinicaltrials.gov/study/NCT00477672) |
| NCT00658567 | ACP-103-014 | EARLY-STOPPED, NO FORMAL BINARY VERDICT | [Sponsor October 2009 update](https://acadia.com/en-us/media/news-releases/acadia-pharmaceuticals-provides-update-pimavanserin); [registry](https://clinicaltrials.gov/study/NCT00658567); FDA [statistical review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2016/207318Orig1s000StatR.pdf) |
| NCT01174004 | ACP-103-020 | MET | [Sponsor November 2012](https://acadia.com/en-us/media/news-releases/acadia-announces-pimavanserin-meets-primary-and-key-secondary); [peer-reviewed exact-NCT study](https://pubmed.ncbi.nlm.nih.gov/24183563/) |
| NCT00550238 | ACP-103-015 | NONBINARY SAFETY EXTENSION | [European trial results/crosswalk](https://www.clinicaltrialsregister.eu/ctr-search/trial/2007-003035-22/results) |
| NCT00156923 | ALK21-010 | NONBINARY SAFETY EXTENSION | [Exact NCT results](https://clinicaltrials.gov/study/NCT00156923) |
| NCT00156936 | ALK21-006EXT | NONBINARY SAFETY EXTENSION, BUSINESS-TERMINATED | [Exact NCT results](https://clinicaltrials.gov/study/NCT00156936) |

## FDA review distinction

The FDA's [2016 NDA 207318 statistical review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2016/207318Orig1s000StatR.pdf) lists ACP-103-020 as the single pivotal positive efficacy study, ACP-103-012 as a failed supportive study and ACP-103-014 as an early terminated supportive study with no formal primary hypothesis test. The FDA application was [approved April 29, 2016](https://acadia.com/en-us/media/news-releases/fda-approves-acadia-pharmaceuticals-nuplazidtm-pimavanserin) with a [May 1, 2016 historical PDUFA target](https://acadia.com/en-us/media/news-releases/acadia-pharmaceuticals-announces-fda-priority-review-nuplazidtm). The target is **not** entered into future PDUFA fields. One approved application is not six separate regulatory decisions.

## Data-integrity constraints

All six NCT IDs are existing members of the 762-trial census. The 190-column export schema and numerical RAAS predictions are unchanged. The three open-label safety studies have no binary comparator efficacy threshold. Endpoints must not be inferred from subsequent FDA approval. The primary/secondary hierarchy for ACP-103-012 is conservatively flagged because the sponsor's motoric-tolerability statement and FDA hypothesis-test hierarchy differ.

Follow-up research: collect full trial-specific safety tables, original SAP and subgroup controls for ACP-103-020, and extend issuer evidence work to the remaining 21 Acadia and 32 Alkermes trials, then Ionis, Sinovac and Axsome according to missing-data priority.
