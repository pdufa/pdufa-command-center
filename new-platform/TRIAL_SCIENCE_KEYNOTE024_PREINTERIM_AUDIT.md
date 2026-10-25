# KEYNOTE-024 pre-interim evidence audit (historical read-only pilot)

This phase improves provenance without promoting any experimental or regulatory conclusion. The two conservative readiness grades stay **Input Readiness = FAIL (5/12 supported), Reluctance = HIGH** until the pre-interim protocol/SAP and other critical evidence have been independently reviewed. Clinical benefit in the original completed trial is a separate question.

## Dated evidence verified publicly

| Historical date | Source and finding | Evidence category | Remaining limit |
|---|---|---|---|
| 2015-05-20 | ASCO/JCO KEYNOTE-024 trial-in-progress abstract TPS8103 describes blinded central PFS assessment using RECIST 1.1 as primary; ORR/OS/safety secondary; 1:1 randomization and PD-L1 TPS ≥50%. | Public study-design description published **before** original readout | An abstract does not substitute for a signed SAP, amendment history or original alpha-spending plan |
| 2016-05-09 | Original interim PFS/OS data cutoff per 2016 paper. | Later report of analysis date | Not protocol effective-date evidence |
| 2016-10-08 | Original NEJM 2016 KEYNOTE-024 report, PMID 27718847. | Published results | Source-reported, not independent reanalysis |
| 2016-10-08 | NEJM original study report lists supplement `nejmoa1606774_protocol.pdf`. | Document linked in journal **but not content-reviewed** | Do not claim the linked PDF proves when original protocol amendments/SAP were finalized |
| 2017-12-20 | CT.gov linked protocol/SAP 024-11, Japan-only amendment. | Document date available, but **after** original readout | Not contemporaneous 2016 alpha-spending evidence |
| 2020-06-01 | Five-year follow-up data cutoff per 2021 publication. | Later follow-up cutoff | Distinct from 2016 interim analysis |
| 2021-04-19 | Five-year KEYNOTE-024 publication, PMID 33872070. | Long-term secondary follow-up | Effective chemotherapy-arm crossover (66%) complicates OS interpretation |

Sources:
- https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103
- https://doi.org/10.1056/NEJMoa1606774
- https://pubmed.ncbi.nlm.nih.gov/27718847/
- https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf
- https://pubmed.ncbi.nlm.nih.gov/33872070/

**Important:** NEJM provides a 2016 supplementary-protocol download listing. We have not independently read and authenticated that PDF's earlier amendment/SAP chronology; if it can be retrieved, it is the next document to review.

## Registry safety counts and denominators

The new API returns `sourceEvidenceAudit.registrySafety.groups` from the **checksum-verified archived CT.gov trial JSON**. Each group includes its exact JSON field locator, source title, and separate reported *affected/at risk* counts for serious AEs, other AEs and deaths. Missing counts are displayed as **Not reported**, not zero.

Some KEYNOTE-024 registry groupings reflect first-course, treatment switch-over or retreatment periods. The system never aggregates those groups into a randomized two-arm comparison or equates registry *serious* events with the journal's *grade 3–5 treatment-related* AE percentages. Apparent differences between reporting systems need population, duration, event-class and attribution reconciliation.

- Bounds: at most 24 distinct registry groups, with integer-only denominators and numerator ≤ denominator for each class.
- Safeguards: exact NCT identity, archived gzip size and SHA-256 validation, source-specific publication identity, no automatic grade changes, no DB mutations, no new trial downloads and no trading actions.
- Current archived data are historical; a more recent registry update could have a different grouping. A new import must be versioned and independently compared, not silently overwrite this evidence audit.

## Research needed next

1. Obtain and inspect original 2016 NEJM-linked protocol supplement and determine the **effective** 2016 or earlier SAP version, signed dates and amendment history.
2. Compare original and registry posted PFS results, censoring, OS alpha allocation and key subgroups; do not treat p=0.005 and its alpha boundary as inherently prespecified without the contemporaneous plan.
3. Reconcile event-group populations (first course versus crossover) with journal safety denominators, exposure, grade, attribution and immune-related events.
4. Review historical FDA approval, clinical review and CMC documents independently. No pre-approval trading or prospective approval probability claims arise from this historical study.

The new audit is optional in the pilot response and is never used to modify the existing 20-level source-coverage tool, GEM JR / GEM / WT or FS/FA preset assignments.
