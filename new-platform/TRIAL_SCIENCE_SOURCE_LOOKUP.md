# Trial Science — external scientific-source lookups (isolated review)

This module is a **read-only research reference finder**, **not** a scientific
assessment, clinical adjudication, financial analysis, FDA probability model,
or production crawler.

## Available source adapters

- PubMed: search for the **exact NCT ID** using NIH/NLM ESearch, then retrieve
  up to five bibliographic summaries using ESummary.
  Source: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- FDA: retrieve the publicly indexed Drugs@FDA application record for an
  **explicitly provided** six-digit NDA or BLA identifier. It is not inferred
  from the ticker, company, medicine, or NCT ID.
  Source: https://open.fda.gov/apis/drug/drugsfda/how-to-use-the-endpoint/
- ClinicalTrials.gov: previously archived exact-NCT registry source is
  checksum-verified **before** any external lookup is allowed.

No user-supplied URLs are fetched. Requests have fixed provider origins, timeouts,
a bounded response size, and limited result counts.

## Isolated, authenticated endpoint

`GET /api/scientific-assessment/dossier/references?exact_id=TRIAL%7CNCT12345678`

Optional: `&application_number=NDA012345`.

Requires an authorized internal API request and a valid archived NCT record.
This route is **disabled by default**. Enable in an isolated staging service
only after CI review by setting `PDUFA_SCIENTIFIC_EXTERNAL_LOOKUP_ENABLED=1`.

The ordinary
`GET /api/scientific-assessment/dossier?exact_id=TRIAL%7CNCT12345678`
continues to read only the existing, checksum-verified stored record and does
not request internet resources.

## What returned evidence means

- `bibliographic_match_only`: a PubMed search found a publication indexed
  with the NCT string. This is **not proof** that the publication is
  the primary results paper, contains this trial's results, or supports a
  clinical conclusion.
- `application_record_only`: Drugs@FDA lists the explicitly supplied
  application number; its association with the specific clinical trial is
  **not independently verified**.
- No external results: either no indexed reference was returned or a source
  lookup failed. Provider failures yield an unavailable error, not negative
  evidence.
- All eight domain scores, aggregate score, FDA approval probability, GEM,
  GEM JR, Pipeline, and existing FS/FA preset memberships remain unchanged.

## Operational safeguards

- No automatic scans, scheduler, background jobs, trading commands or writes.
- Never turn this on for the entire Pipeline without a separate reviewed
  rate-limit, cache and prioritization design.
- NCBI advises an unauthenticated limit of **3 requests/second** across API
  use; this route does not implement a cross-worker quota. Use one trial
  request at a time during isolated evaluation.
  https://eutilities.github.io/site/API_Key/usageandkey/
- Do not put API keys, database URLs, cookies, or user secrets in request logs.
- Test a real verified NCT citation result and FDA application lookup before
  enabling this on a shared service; mocked CI tests are not live-source proof.

## Verification and next steps

Automated tests cover exact-NCT validation, FDA application ID validation,
cross-record rejection, provider failure, missing and corrupt archived data,
authentication, missing evidence, and the rule that source metadata never
generates scores.

Next: manually confirm the source references for one selected Phase 3 trial,
add independently corroborated clinical-result evidence with source dates
and analytic uncertainty, and then design a bounded review queue for GEM JR,
GEM, and WT (a future separate scope decision).
