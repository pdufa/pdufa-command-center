# Official data recovery — research only

Prediction status: **NOT READY / ABSTAIN**. Acquisition and structural validation do not authenticate origin, adjudicate an FDA cycle, or validate scientific evidence.

## Acquisition implementation

`research.official_sources` provides source-bound official HTTPS adapters for Drugs@FDA TSV ZIP, openFDA download index and bulk JSON/ZIP, published CRL JSON, ClinicalTrials.gov current API and operator-supplied historical JSON, and FDA PDF documents. Defaults: 30-second timeout, three attempts, minimum one-second spacing, bounded backoff, Retry-After handling. Redirects require explicit review of the published official destination. No proxy rotation or access-control bypass.

Availability is one of SOURCE AVAILABLE, SOURCE TEMPORARILY UNAVAILABLE, ACCESS DENIED, SOURCE DOCUMENT MISSING, SOURCE DOCUMENT UNVERIFIED. These are retrieval states, never FDA outcomes. Every live attempt writes an immutable receipt. Valid or invalid original bytes are retained under SHA-256 names; stored bytes are checked before reuse. HTTP Last-Modified is retained separately and never promoted to a publication clock. Snapshot ID is the bytes' digest; ETag or the operator's dataset version is supplementary metadata. Duplicate exports are not independent evidence.

On 2026-10-29, one attempt each for Drugs@FDA, openFDA index, CRL API and ClinicalTrials.gov returned transport URLError through the unavailable configured proxy. Retained receipts: `research/evidence/official_access_20261029/`. No official records downloaded. The enforced environment allowlist excludes FDA/NIH destinations. These observations do not establish a remote FDA server's HTTP status. No further blocked probes are needed until environment access changes.

## Authorized operator acquisition

Use an environment authorized to reach these public sources. Preserve the exact downloaded file without editing, its official URL, acquisition UTC time, response headers and any independently evidenced publication time; compute SHA-256 before transfer. Do not invent timestamps from printed action dates.

1. Drugs@FDA published data files: https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files . Supply the official ZIP (Applications.txt and Submissions.txt required; retain Products.txt and ApplicationDocs.txt when present). Approval-oriented absence cannot establish CRL.
2. openFDA: https://open.fda.gov/data/downloads/ and https://api.fda.gov/download.json . Locate the published drug/drugsfda partitions and transfer the exact ZIPs. Explicitly select each published `download.open.fda.gov` URL. Imports are bounded to 256 MiB compressed and expanded per artifact; larger files require a reviewed limit change. These are another FDA export, not independent verification of Drugs@FDA.
3. Published CRLs: https://open.fda.gov/apis/transparency/completeresponseletters/ . Supply original metadata and linked letters, including redaction/coverage notes. The adapter currently validates the JSON envelope only; CRL field normalization remains blocked pending an authentic schema sample and adjudication.
4. ClinicalTrials.gov: https://clinicaltrials.gov/data-api . Supply current API records for leads and separately acquire dated historical versions from the official study history. Historical JSON import validates protocolSection/identificationModule/nctId but does not authenticate the historical version or publication clock.
5. Original application-specific approval letters, CRLs, review documents and formal extension notices. Exact document leads, application identities and gaps for NVAX, UNCY, TNXP, BCRX, CORT and VNDA are enumerated in `research/evidence/historical_verification_worklist_20261029.json`; this worklist preserves missing/ambiguous cycles and all trial leads. No drug-name matching or later approval substitution.

Example offline import (replace each placeholder with operator-recorded values):

```sh
python -m research.official_sources drugs_fda \
  --import-file /authorized/DrugsFDA.zip \
  --url https://www.fda.gov/media/89850/download \
  --sha256 RECORDED_SHA256 --dataset-version RECORDED_VERSION \
  --directory /research-artifacts/fda
```

`--published-at` accepts an aware timestamp when supplied with external publication evidence. Even then, `publication_timestamp_verified`, `independently_verified` and historical eligibility remain false. The receipt's fetched_at is this import time for offline transfers; the external acquisition time belongs in retained operator provenance. Checksum equality proves integrity against the supplied checksum, not authenticity.

## Verification

Run `python -m pytest -q tests/test_official_*.py` and the existing scientific, FDA and evidence/security regressions. `.github/workflows/official-source-recovery.yml` runs offline contracts only; no production deployment or scheduled source polling. Independent scientific review, exact cycle adjudication, original publication clocks and verified holdout data remain external dependencies. Structural completeness of 650 fields, 50 levels, 40 assessments and ten comparison criteria is not scientific validation.
