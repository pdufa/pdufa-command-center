# KEYNOTE-024 (NCT02142738) — historical Phase 3 scientific pilot

**Status:** source-attributed pilot; **not a completed, independently
adjudicated eight-domain scientific assessment**. This record is for validating
the research workflow, **not a present-day PDUFA forecast or trade signal**.

## Clinical question and trial identity

KEYNOTE-024 randomized 305 previously untreated patients with metastatic
non-small-cell lung cancer (NSCLC), PD-L1 tumor proportion score (TPS) >=50%,
and no sensitizing EGFR alteration or ALK translocation. Pembrolizumab
200 mg every three weeks (n=154) was compared with investigator-selected
platinum-based chemotherapy (n=151). The study was open-label; the primary
progression-free survival (PFS) endpoint used blinded independent central
radiologic review. Post-progression crossover was permitted. The published
analysis had a sponsor-funding relationship.

- Registry: https://clinicaltrials.gov/study/NCT02142738
- Original peer-reviewed report (Reck et al., NEJM, 2016):
  https://pubmed.ncbi.nlm.nih.gov/27718847/
- FDA-staff-authored approval summary: https://academic.oup.com/oncolo/article/22/11/1392/6444702

## Published endpoint results — keep analyses separate

### 2016 initial randomized-trial report (PMID 27718847)

| Endpoint | Pembrolizumab | Chemotherapy | Comparative statistic |
|---|---:|---:|---|
| Primary PFS, median months | 10.3 | 6.0 | HR 0.50 (95% CI 0.37–0.68), p<0.001 |
| 6-month overall survival, % | 80.2 | 72.4 | Interim OS HR 0.60 (95% CI 0.41–0.89), p=0.005 |
| Objective response, % | 44.8 | 27.8 | Secondary endpoint |
| Any-grade **treatment-related** AEs, % | 73.4 | 90.0 | Descriptive AE comparison |
| Grade 3–5 **treatment-related** AEs, % | 26.6 | 53.3 | Descriptive AE comparison |

**Clinical interpretation:** a strong observed difference on the
prespecified PFS endpoint in this selected population; the hazard ratio is a
time-to-event relative hazard, **not** a 50% absolute risk reduction.
Open-label treatment leaves performance and some reporting biases possible;
the blinded central assessment mitigates ascertainment bias for PFS.

**Statistical caution:** the original and FDA regulatory summary report an
interim alpha allocation, with p=0.005 compared with an OS boundary of 0.0118.
The full protocol/SAP and all amendments have not yet been independently
reviewed here.

### 2017 patient-reported quality of life (PMID 29129441)

Prespecified **exploratory** EORTC QLQ-C30 global-health/QOL change at
week 15 was 6.9 points with pembrolizumab versus −0.9 with chemotherapy;
between-arm difference 7.8 points (95% CI 2.9–12.8; **nominal** p=0.0020).
The open-label design can affect subjective symptom reporting. The eligible
patient-reported-outcomes population is not the same as the entire randomized
population.

- https://pubmed.ncbi.nlm.nih.gov/29129441/

### 2021 five-year analysis (PMID 33872070)

With data cutoff **June 1, 2020**, median overall survival was 26.3 versus
13.4 months (HR 0.62, 95% CI 0.48–0.81); **Kaplan–Meier estimated** five-year
OS was 31.9% versus 16.3%. The publication reports a **66.0% effective
crossover** among chemotherapy-assigned participants who later received
anti–PD-1/PD-L1 therapy. The change in OS HR over time and substantial
post-randomization treatment must be examined; these are not the original
interim OS measurements.

- https://pubmed.ncbi.nlm.nih.gov/33872070/
- https://ascopubs.org/doi/10.1200/JCO.21.00174

### Distinct immune-related safety issue

NCI's summary reports **immune-mediated** adverse events in 29.2% with
pembrolizumab versus 4.7% with chemotherapy. That category differs from
all-grade and grade 3–5 **treatment-related** AE rates and must not be
incorrectly added, subtracted, or treated as a contradiction in adverse-event
frequency. Adverse-event severity, duration, exposure, and attribution need
a full source-table-level check.

- https://www.cancer.gov/types/lung/research/pembrolizumab-nsclc-keynote-024

## Eight-domain research board

| Domain | What the pilot has | Unresolved research |
|---|---|---|
| Disease biology | PD-L1 high-expressing NSCLC enrollment; EGFR/ALK exclusions | Intratumor heterogeneity, assay variability and broader generalizability |
| Mechanism of action | PD-1/PD-L1 immune-checkpoint biology described by NCI | Mechanism-specific resistance and biomarkers |
| Preclinical evidence | No adjudicated source | Target engagement, model relevance, translational concordance |
| Clinical design | Randomization, sample sizes, comparator, BICR PFS; crossover | Complete protocol/SAP, interim boundaries, censoring and amendments |
| Clinical results | Source-attributed PFS/OS/ORR, safety, QOL and five-year follow-up | Registry table reconciliation, individual safety signals, missing data, bias |
| Competitive landscape | Context of other first-line NSCLC trials | Comparable eligibility, PD-L1 cutoffs, evolving standard of care |
| Regulatory analysis | FDA-authored summary of historical approved indication | Exact submission/label chronology and application evidence chain |
| Advanced inference | Original/follow-up HR and CI available | Robustness, transportability, sensitivity to crossover, replication |

## Do not confuse these states

1. **Published result:** a numerical estimate stated in a traceable source.
2. **Source-level corroboration:** another trustworthy document reports an
   aligned value or clarifies a statistical or regulatory detail.
3. **Scientific adjudication:** a critical assessment of design, complete
   results, prespecification, alternatives, biases, and disagreements.
4. **Forecast:** an explicitly validated prospective model, which this pilot
   does **not** provide.

The code carries the first two as research material, while explicitly
labelling independent full appraisal incomplete. It never assigns a score,
changes PIPELINE/GEM JR/GEM/WT decisions or FS/FA memberships, or places orders.

## Pilot endpoint

Authenticated, read-only isolated staging route:
`GET /api/scientific-assessment/pilot/keynote024`

Requires a stored checksum-verified NCT02142738 archive record. Returns the
base eight-domain dossier and the dated published-results object. No external
network call and no database mutation occur in the request.

The new code remains on the isolated Trial Science branch / draft PR and is
**not deployed** to the running review service as part of this change.
