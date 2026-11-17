# KEYNOTE-522 protocol version exclusion — confirmed 2023 amendment

## Verified finding
GitHub Actions research-only run https://github.com/pdufa/pdufa-command-center/actions/runs/44002352494 successfully downloaded and extracted text from https://cdn.clinicaltrials.gov/large-docs/88/NCT03036488/Prot_SAP_000.pdf .

- PDF page 1: "Document Date: 25-May-2023"; NCT03036488.
- PDF page 2: "Protocol/Amendment No.: 522-06", "MK-3475-522-06 Final Protocol 25-May-2023".
- Extracted pages: 151; candidate review pages: 35.
- Raw PDF SHA-256 from previous acquisition: `4301c9e7420623207b7d66d3cac197922139de82653ed0be04696cde93f8700f`.
- Research artifact: https://github.com/pdufa/pdufa-command-center/actions/runs/44002352494/artifacts/14292577310

## Mandatory temporal classification
**POST_DECISION_VERSION — EXCLUDE FROM PRE-2021 BLIND EVIDENCE.**

FDA decision cutoff for the historical test: 2021-07-26. This PDF is dated 2023-05-25, so it is not eligible regardless of its legitimate source, SHA-256 integrity, or earlier amendment references in its document history.

- `source_integrity_verified=true` (PDF signature, hash and byte count)
- `protocol_version_date=2023-05-25`
- `version_predates_cutoff=false`
- `blind_eligible=false`
- `historical_snapshot_verified=false`
- `accuracy_evaluated=false`

The 2023 document can be retained for **non-blind protocol archaeology** only. Earlier amendments described retrospectively within it are leads, not authenticated pre-decision original versions. Do not import 2023 changes into the 2021 model's evidence set.

## Required next step
Locate an actual 2021-or-earlier dated protocol amendment or SAP, independently verify its version and source provenance, and apply the point-in-time gate before any blinded assessment.
