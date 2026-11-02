# KEYNOTE-024 original FDA letter — research-stage pilot

**Status:** primary document visually inspected for research and recorded as a
**candidate** historical regulatory action, NOT independently adjudicated.
There is no claim that two qualified reviewers have signed a verification,
that original FDA PDF bytes were preserved with a verified digest, that the
historical approval/nonapproval denominator is complete, or that an outcome
model is ready. This example is **not** loaded into production or a training
cohort.

Machine-readable record:
\`new-platform/backend/app/research_sources/hop_keynote024_primary_letter_pilot_research.json\`

Offline safety audit:
\`new-platform/backend/app/hop_fda_pilot_case_audit.py\`

## Original FDA approval document inspected

- Original FDA PDF: https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf
- FDA reference ID: **4003165**; PDF is six pages, with both
  **BLA 125514/S-8** and **BLA 125514/S-12** on the same original letter.
- **Page 1:** S-8 modifies the previous metastatic NSCLC indication and
  removes its accelerated-approval contingency following fulfillment; S-12
  expands first-line metastatic NSCLC use for tumors with PD-L1 TPS at least
  50% and no EGFR/ALK genomic tumor aberrations. The FDA letter states
  the supplemental applications are approved.
- **Page 3:** postmarketing commitment 3127-1 names KEYNOTE-024 and
  requests mature overall-survival data. A separate 3127-2 commitment names
  KEYNOTE-042. **KEYNOTE-042 must not be conflated with the original
  KEYNOTE-024 evidence** for this S-12 approval.
- **Page 6:** electronic signature dated **October 24, 2016**.
  This is the FDA letter action date, **not a proved PDUFA target date**
  and not proof that the letter was publicly available before the action.

Two **supplement action claims** are preserved under one original FDA PDF.
They must not be merged into a single original BLA approval, or counted as
two independently adjudicated clinical review cycles.

## Point-in-time clinical evidence candidate

KEYNOTE-024 is NCT02142738. The trial report, *Pembrolizumab versus
Chemotherapy for PD-L1-Positive Non-Small-Cell Lung Cancer*
(DOI 10.1056/NEJMoa1606774), is indexed in PubMed at
https://pubmed.ncbi.nlm.nih.gov/27718847/.

- **First ahead-of-print publication:** October 8, 2016,
  which was before the FDA letter date.
- **Print issue date:** November 10, 2016, which was afterward.

An October 8 electronic report is a *candidate* predecision evidence source.
The print issue must **not** be treated as available on October 24 merely
because it describes the same trial. A source-archived point-in-time feature
snapshot, exact feature release dates, and independent provenance review are
still missing. Do not move findings from the later 2019 S-47/KEYNOTE-042
approval into this historical S-12 prediction snapshot.

## Independent release gates still blocked

The single visually inspected document does not authenticate reviewer
identities, source byte digests, application-cycle adjudications or historical
population completeness. The direct original-letter research note therefore
retains:

- \`independently_verified_review_cycle_outcomes: 0\`
- \`model_eligible_records: 0\`
- \`approval_rate: null\`, \`predicted_probability: null\`
- no automatic scoring, scanner activation, or trading labels.

Before any model training, obtain a complete predecision evidence freeze and
a **representative** FDA action sampling frame with independently verified
approvals and nonapprovals. Keep this trial and approval action as a pilot for
manual source-review rehearsal and retrospective time-bound testing only.
