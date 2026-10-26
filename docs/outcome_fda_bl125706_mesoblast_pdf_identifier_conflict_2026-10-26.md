# Mesoblast RYONCIL BLA 125706 — original PDF identifier discrepancy adjudication (2026-10-26)

**Finding:** a real internal inconsistency in an FDA-authored primary PDF, NOT a PDF text-extraction artifact.

## Direct original-PDF inspection

FDA December 18, 2024 Summary Basis for Regulatory Action: https://www.fda.gov/media/185192/download

- **Page 1, header** visibly prints `BLA STN: 127506/0`.
- **Page 6, regulatory-history table** identifies `BLA 125706/0` for the January 31, 2020 rolling submission.
- **Page 6, introduction** also explicitly identifies `STN 125706` for Mesoblast RYONCIL.

Independent FDA cross-checks:
- FDA approval letter: https://www.fda.gov/media/184605/download — `BL 125706/0`.
- FDA RYONCIL product page: https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/ryoncil — `STN 125706`.
- FDA Purple Book: https://purplebooksearch.fda.gov/index.cfm?blaNo=125706&event=productdetails — `BLA 125706`, Mesoblast, December 18, 2024 original approval.

## Decision and implementation rule

**Canonical application identity for RYONCIL: BLA 125706/0.** Retain `127506/0` as a verbatim, document-scoped conflicting source field with anomaly type `FDA_PRIMARY_DOCUMENT_INTERNAL_IDENTIFIER_CONFLICT`. Do NOT create a second application, silently overwrite the source value, or treat this typo as a new BLA. This is a research determination, not an FDA-issued correction notice; no official erratum was established.

This closes the *nature of the anomaly* (original document inconsistency vs extraction), not the broader review-cycle completeness gate.

Safety: `identity_verified=true`; `identifier_conflict_documented=true`; `complete_review_cycles_adjudicated=false`; `model_eligible=false`; `prediction_probability=null`.
