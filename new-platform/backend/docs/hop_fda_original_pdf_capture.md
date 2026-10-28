# Original FDA action letter HTTPS byte capture — opt-in, nontraining

## Purpose and current evidence

Two FDA-signed primary action letters have been inspected in the research
manifest: ripretinib NDA213973 approval (2020-05-15) and odronextamab
BLA761303 Original 1 Complete Response Letter (2024-03-22).

**Neither original PDF has yet been retained with a verified original-source
SHA-256 by this capture workflow.** Do not fill in hash fields, signed action
adjudication, FDA first-publication dates, review-cycle ordinal or prediction
probabilities until the proper evidence and reviewers are available.

The source roster remains **2 real letter observations, 0 independently
adjudicated model-eligible historical review cycles, 0 independently backtested
cases and no validated predictive accuracy or FDA PASS/FAIL probability.**

## Exact-URL trust boundary

File: `new-platform/backend/scripts/capture_hop_fda_original_https.py`.

The script pins the following two **exact** official FDA URLs. It rejects any
other URL or modified source URL, even when the host is an approved FDA domain:

- https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2020/213973Orig1s000ltr.pdf
- https://download.open.fda.gov/crl/CRL_BLA761303Original1_20240322.pdf

For each manual source capture it uses ordinary TLS verification, disallows
redirects, requires the exact requested URL and HTTP 200, accepts PDF/octet
media types only, reads bounded chunks (20 MiB maximum), requires a
plausible PDF header/trailer and minimum byte length, and calculates SHA-256
over the actual received bytes. Its local receipt contains UTC acquisition
time, original URL, byte count, SHA-256, and HTTP response metadata such as
Date/Last-Modified/ETag when supplied.

The original source bytes and receipt are created as separate files in an
already-existing, non-symlink output folder, with no overwrites. A
failed/truncated/oversize/non-PDF response leaves no output files; a failure
while writing the provenance receipt also rolls back the captured PDF.
The script never uses credentials, the PDUFA database or broker/Sheet APIs.

**Important distinction:** a successful TLS download and SHA-256 receipt
prove that particular response was received and give a repeatable fingerprint.
Neither a matching domain, original document hash, timestamped HTTP
Last-Modified header, nor the document's signature date proves its
first *public* release date, exact FDA review-cycle identity, complete
regulatory action history, or independent scientific adjudication.

## Manual CI workflow — disabled until authorized trigger

Workflow: `.github/workflows/hop-fda-source-capture-manual.yml`

This workflow has **only** a `workflow_dispatch` trigger, no nightly schedule,
PR trigger, branch push or scanner integration.

After the workflow is merged into `main`, a repository operator may choose
GitHub → Actions → **Manual FDA source-byte research capture** → Run workflow.
Select `both`, `nda213973`, or `bla761303`. The job uses a
no-secrets, read-only repository token and a 5-minute timeout.

If the official host permits the runner's request, the job packages the
captured PDF(s) and provenance JSON receipt(s) as a private/repository-scoped
GitHub Actions artifact retained for **7 days**. This does not populate the
source manifest or production database and does not certify a model label.
The operator must independently verify the original PDF and its action/
application identity, assess source availability, and preserve provenance
in an approved, longer-term evidence store if necessary.

If FDA returns HTTP 403/404, a redirect, HTML, timeout or another
unverifiable response, the job fails closed and **no hash or success is
claimed**. It should not be automatically retried by changing to an
unverified mirror or disabling TLS.

## Local offline use

From the repository root, with a controlled original-source capture directory
already created:

```sh
mkdir -p /tmp/pdufa-fda-evidence
chmod 700 /tmp/pdufa-fda-evidence
PYTHONPATH=new-platform/backend python new-platform/backend/scripts/capture_hop_fda_original_https.py /tmp/pdufa-fda-evidence --record-id NDA213973_ORIGINAL_1_20200515_APPROVED
```

This is **an online read-only source retrieval**, unlike the prior
`audit_hop_fda_pdf_bytes.py` tool, which accepts already downloaded local
bytes and cannot establish source origin.

Run purely offline source-mocked safety tests:

```sh
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests/test_hop_fda_original_https_capture.py
```

Tests exercise exact domain and URL identity, successful bounded hashing,
non-PDF and oversized responses, redirects, HTTP errors, duplicate outputs,
symlink destinations, corrupt source identities, fake promotions and partial
receipt-write rollback. They use **synthetic bytes only** and are not
independent FDA decision evidence.

## Evidence still required for historical PASS/FAIL validation

1. Independently inspect retained original FDA PDF contents and exact
   submission/original/supplement/review-cycle histories.
2. Verify when each label became publicly available, independent of the
   letter's signed action date and the date this job downloaded it.
3. Reconstruct predecision feature snapshots and original/revised PDUFA
   target chronology.
4. Reconcile a representative, *consecutive* historical FDA population,
   including approved, CRL, withdrawn and delayed decisions.
5. Complete independent review, honest holdout selection, calibrated
   backtesting and performance comparison before generating approval odds.

Do not infer predictive accuracy from source capture success. No trading,
scanner scheduling, Google Sheets writes or saved FS/FA associations are changed.
