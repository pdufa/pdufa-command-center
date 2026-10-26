# OUTCOME — FDA ALYGLO, LANTIDRA and Capricor review-cycle source crosscheck (2026-10-26)

**Research-only adjudication pass.** The dates below are source-supported submission/action pairs, **not** a certified exhaustive application history or a model-ready FDA cohort. Original FDA PDFs were inspected visually where available. FDA SBRA means Summary Basis for Regulatory Action.

## ALYGLO — BLA 125743, Green Cross / GC Biopharma

FDA 2023 SBRA regulatory history, **PDF p. 6 (zero-based 5)**, https://www.fda.gov/media/175227/download:
- Original BLA submitted/received **2021-02-25**; original Complete Response **2022-02-25**.
- Resubmission **2023-07-14**; later approval **2023-12-15**.
- SBRA regulatory history prints **2024-01-13 action due date** for the resubmission; clinical review https://www.fda.gov/media/175311/download prints **2024-01-12**. **Source discrepancy remains OPEN**, and is not a new action date.
- Original signed CRL https://download.open.fda.gov/crl/CRL_BLA125743_20220225.pdf directly prints `BL 125743/0`, recipient **Green Cross Corporation**, original receipt **2021-02-25**, and `COMPLETE RESPONSE` dated **2022-02-25**.
- Signed FDA approval https://www.fda.gov/media/174897/download directly prints `BL 125743/0`, recipient **GC Biopharma Corp.**, receipt **2023-07-14**, and `BLA APPROVAL` dated **2023-12-15**.
- Preserve both sponsor names on the underlying documents; **one application, two actions**, not two independent applicant denominators.

Structured cycles:
`BLA:125743:ORIGINAL` from **2021-02-25** to **2022-02-25** CRL;
`BLA:125743:RESUBMISSION-1` from **2023-07-14** to **2023-12-15** approval.

## LANTIDRA — BLA 125734, CellTrans

FDA 2023 SBRA https://www.fda.gov/media/170457/download, **PDF page 7 (zero-based 6)** regulatory-history table:
- Original application receipt **2020-05-19**.
- **2021-08-18 Complete Response** documented by the FDA's own regulatory-history table.
- Resubmission after CRL **2022-12-30**.
- FDA action due date **2023-06-28**.
- Signed approval https://www.fda.gov/media/169921/download is dated **2023-06-28**, BLA `125734/0`.
- **Evidence limitation:** the signed original **2021-08-18 CRL was not directly retrieved**; the 2021 agency action is **secondary within a primary FDA regulatory-summary document**, not a visually authenticated action letter. The research fixture points to the SBRA and explicitly keeps direct action-letter verification pending.

Structured cycles:
`BLA:125734:ORIGINAL` **2020-05-19** → **2021-08-18** CRL, with FDA SBRA provenance (signed CRL pending);
`BLA:125734:RESUBMISSION-1` **2022-12-30** → **2023-06-28** approval, signed action corroborated.

**New research-only action endpoint:** 2021 CRL, added to sampled event fixtures rather than hiding a known historical nonapproval.

## Capricor deramiocel — BLA 125842

FDA advisory committee presentation https://www.fda.gov/media/193912/download, **PDF slide 12 (zero-based 11)**:
- Original BLA submitted **2024-12-31**.
- Original complete response issued **2025-07-09**, corroborated directly by signed CRL https://download.open.fda.gov/crl/CRL_BLA125842_20250709.pdf.
- Post-CRL resubmission **2025-12-29** was deemed **incomplete**, and **does not create another FDA final action**.
- FDA history lists **2026-02-20** resubmission, but **no future final decision is inferred** from this source. The original submission-to-CRL timeline is the only 125842 entry in this pass.
- The FDA July **2026** slide date makes the regulatory-history document **ineligible as evidence available before the 2025 action**; no as-of feature clearance.

Structured cycle: `BLA:125842:ORIGINAL` **2024-12-31** → **2025-07-09** CRL.

## Selection counts and safety

Before: **19** selected final-action research endpoints across **10** BLA identifiers, **11** selected endpoints with structured review timelines spanning **5** applications.

After including LANTIDRA's previously unsampled 2021 CRL and five sourced timelines here: **20 selected FDA action endpoints / 10 application identifiers**, **16/20 endpoints linked to a structured review timeline**, **8/10 sampled application identifiers represented**. These are **sampled research records**, NOT an exhaustive historical cohort or approval probability.

Unlinked selected endpoints: Mesoblast 2020 CRL (1); Atara/Pierre Fabre 2025 and 2026 CRLs (2); REGENXBIO 2026 CRL (1). Missing exact FDA receipt dates, signed original letters or incomplete histories remain blockers. Atara/Pierre Fabre and REGENXBIO sponsor disclosures cannot silently replace an independently established precise FDA receipt date.

All `review_cycle_certified=false`, `source_publication_asof_verified=false`, `complete_application_denominator_verified=false`, `model_eligible=false`, `prediction_probability=null`. No edits to the immutable published FDA audit indexes.
