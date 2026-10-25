# KEYNOTE-024: published 2016 interim plan compared to observed evidence

**Status:** source-attributed historical comparison, not an independently
authenticated original signed protocol/SAP. For NCT02142738 only. Read-only.
The existing scientific **Input Readiness FAIL** and **Reluctance HIGH**
are intentionally unchanged; no scientific score or FDA probability is assigned.

## Published trial design (published after the original May 9, 2016 cutoff)

The original *NEJM* publication reports:

- Overall one-sided family-wise Type I error control: **2.5%**.
- **First interim:** objective response assessed after the first **191 randomized**
  participants reached **at least six months of follow-up**; allocated
  one-sided alpha **0.5%**.
- **Second interim:** primary PFS superiority test intended after roughly
  **175 progression/death events**; allocated one-sided alpha **2.0%**.
- Conditional OS group-sequential testing after approximately **110 and 170
  deaths**, assuming the PFS superiority gate was passed.

This is the authors' published *description of the plan*, not independent
evidence that the plan's exact revision was signed and effective before the
interim cutoff.

Primary publication:
https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774
(Statistical Analysis and Discussion).

## Original observed interim (separate from the plan)

- Primary PFS: **189** reported progression/death events; reported
  HR **0.50** (95% CI 0.37–0.68), p<0.001.
- Interim OS: **108** deaths; reported HR **0.60** (95% CI 0.41–0.89),
  p=0.005.
- FDA-staff-authored published efficacy summary reports OS interim
  allocated alpha **0.0118**, against which p=0.005 is compared.
  This does **not** replace the primary FDA clinical review, signed
  statistical analysis plan or the independent reconstruction of the
  group-sequential alpha-spending function.

FDA-staff-authored historical summary:
https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/
(KEYNOTE-024 efficacy table, footnote b).

**Provenance validation:** The source URLs and reported event/alpha values
are exact-checked by the frontend and bounded backend adapter. The backend
requires the existing pre-cutoff protocol checklist item to remain BLOCKED
and the publisher supplement to remain unreviewed. No reviewer statement
or source-candidate submission can silently upgrade a clinical finding.

The first and second interim planned event counts are approximate design
targets, not statements that the realized events must equal those counts.
Do not treat the numerical difference as a protocol violation.

## Original signed SAP still outstanding

The NEJM 2016 paper lists `nejmoa1606774_protocol.pdf`, but direct
retrieval of the complete publisher supplement has not succeeded in this
review. **Neither full PDF content nor its pre-interim effective version,
signatures or amendments have been verified.** The ClinicalTrials.gov-linked
protocol/SAP is dated December 20, 2017 (Japan-only amendment); it cannot
retroactively prove the signed plan governing May 2016.

Before advancing the scientific grade, independently inspect and
reconcile the original effective protocol/SAP, group-sequential
boundaries, risk sets, censoring, exact interim decision chronology,
missingness and treatment switching. Preserve primary 2016, 2019 follow-up
and 2021 five-year datasets as distinct analyses.

## Implementation

- Protected, historical exact-NCT pilot response adds
  `publishedInterimDesign` with immutable, clearly distinguished
  `reportedDesign`, `observedInterim`, `sourceDateContext`,
  and `reconciliation` sections.
- The validator *requires* Input Readiness FAIL / Reluctance HIGH and a
  critical BLOCKED original protocol check. A source listing cannot
  be silently upgraded to a verified SAP.
- Browser panel displays reported alpha, planned event thresholds and
  observed PFS/OS results in separate columns with source links and
  explicit uncertainty; no database writes, new scans, live downloads,
  trading, FS/FA edits or FDA forecast.
- Unit and HTTP tests cover both correct historical figures and
  deliberately tampered scores, dates, sources, alpha, PDF status,
  original protocol status and FDA probabilities.
