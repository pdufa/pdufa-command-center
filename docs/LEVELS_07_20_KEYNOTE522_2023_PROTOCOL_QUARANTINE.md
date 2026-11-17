# KEYNOTE-522 protocol amendment 522-06 — post-decision quarantine

**DECISION: NOT ELIGIBLE as a 2021-07-26 blind backtest input.**

## Verified PDF front matter
- Source: https://cdn.clinicaltrials.gov/large-docs/88/NCT03036488/Prot_SAP_000.pdf
- NCT: NCT03036488
- Official document date: **25-May-2023** (PDF page 1).
- Protocol/amendment: **522-06**, `MK-3475-522-06 Final Protocol 25-May-2023` (PDF page 2).
- PDF: **151 pages**, 2,566,239 bytes, SHA-256 `4301c9e7420623207b7d66d3cac197922139de82653ed0be04696cde93f8700f`.
- Acquisition run: https://github.com/pdufa/pdufa-command-center/actions/runs/44002352494
- Extracted 35 candidate pages for revision/endpoint review; artifact: https://github.com/pdufa/pdufa-command-center/actions/runs/44002352494/artifacts/14292577310

## Leakage prevention
The 2023 revision **postdates** the FDA approval decision 2021-07-26 by approximately 22 months. Even if it describes earlier protocol elements, the entire acquired revision must be treated as **post-decision** until earlier original versions can be independently obtained and authenticated.

- `blind_eligible=false`
- `historical_snapshot_verified=false`
- `protocol_revision_date_verified=true` for this PDF's **2023** version only
- `predecision_protocol_eligible=false`
- `outcome_partition=QUARANTINE_POST_DECISION`
- No scores, probabilities, or accuracy evaluations may use the 2023 PDF.
- The research workflow's `DISCOVERY_ONLY` designation remains appropriate for acquisition, but the historical selection gate must reject this revision.

## Required follow-up
Locate an independently dated pre-2021 KEYNOTE-522 protocol or SAP revision (e.g., earlier registry attachments or sponsor/regulatory archive); verify its version and original publication/availability date before use. Do not infer earlier protocol wording from the 2023 amendment.
