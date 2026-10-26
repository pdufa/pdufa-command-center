# Bounded official FDA published-letter PDF page-candidate sampling

**Research-only, October 25, 2026. Not FDA outcome adjudication.**

The source inventory currently has **123 previously byte-confirmed FDA published-letter references** covering **122 distinct full PDF files** within the 101 private original application-identity research packets. A hash-confirmed document does not establish its individual letter page, original versus supplemental FDA action, FDA review cycle, or approval/nonapproval decision.

## Added actual-source inspection

`new-platform/backend/app/hop_fda_pdf_page_candidate_sampling.py` and
`scripts/sample_hop_fda_published_letter_page_hints.py` select up to **eight
distinct PDF fingerprints**, sorted by their recorded full-file SHA-256 so
input order does not influence selection. The selection is a **technical
smoke sample**, not representative of approvals or nonapprovals.

For each selected original FDA `https://download.open.fda.gov/crl/` PDF,
the isolated research workflow:

- Fetches the exact published FDA PDF URL, blocks redirects and imposes a
  20 MB download cap.
- Re-hashes the retrieved PDF and **refuses** data whose complete bytes do
  not match the earlier observed PDF SHA-256.
- Reads at most **40 pages per PDF**, with a 300-page upper bound on the
  document's declared length, leaving uninspected pages explicitly counted.
- Records blank/scanned/non-text pages and provisional zero-based page
  numbers containing the **already known application candidate ID**.
- Flags pages with multiple candidate application IDs; this is ambiguity,
  not proof of a shared or distinct FDA decision.
- Counts unavailable PDF downloads/parsing failures separately. It will
  never silently convert a missing document or page to a negative outcome.

The sample's **per-document URLs, source hashes, provisional application
identities, and page-number hints stay private in the isolated CI runner**.
Only the aggregate sample count, pages inspected, page-extraction coverage
and scientific quarantine flags are written to the public-only artifact.

The source hashes are taken from the earlier actual published-letter PDF
probe, not synthetic trial outcomes. A page that contains the app number is
only a candidate for human reading; it is not independently verified as an
original action-letter page. The process does not interpret a raw
`COMPLETE RESPONSE` or `APPROVAL` string into a regulatory-cycle label.

## Unresolved scientific dependencies

Independent qualified reviewers must inspect the actual original FDA pages,
determine whether a letter pertains to an original NDA/BLA or supplement,
resolve effective decision dates (including corrections and rescissions),
authenticate their separate findings and establish the full application
review-cycle chronology. The published CRL collection cannot serve as a
complete denominator, including never-approved applications or cycles.
Prevent postdecision scientific features from leaking into any historical
prediction study. Do not calculate any model accuracy, calibration or FDA
approval probability until those conditions are established.

**Verified original FDA review-cycle outcomes = 0; model-eligible records =
0; approval probability and retrospective predictive accuracy = unavailable.**
The implementation remains a draft, with no changes to production,
GEM JR/GEM FS/FA presets, scanner operation or trading.
