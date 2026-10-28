# Controlled original FDA PDF retrieval and actual SHA-256 provenance

This increment adds a narrowly scoped, read-only HTTPS capture tool for
**exactly two historical FDA action documents** previously observed through
rendered FDA pages:

- NDA 213973, ripretinib signed approval (2020-05-15):
  https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2020/213973Orig1s000ltr.pdf
- BLA 761303/Original 1, odronextamab CRL (2024-03-22):
  https://download.open.fda.gov/crl/CRL_BLA761303Original1_20240322.pdf

## Tool

`new-platform/backend/scripts/capture_hop_fda_original_https.py`

Only the immutable repository case identities and pre-reviewed FDA URLs may be
requested. The download uses standard TLS hostname verification and a
**no-redirect** client, bounds the entire response to 20 MiB, checks HTTP 200,
PDF media type/header/EOF, streams real binary data into a temporary file,
computes its **actual SHA-256**, and atomically saves a local PDF plus
provenance JSON. It refuses overwriting previous captured bytes. An actual
HTTP Last-Modified header, if present, is stored as **response metadata only**,
never converted into FDA first-publication history.

The user must not supply API keys or private credentials. The tool never
writes a database, commits the PDF to the repository, changes the PDUFA
scanner, writes sheets or authorizes a trade. The source document content
still requires inspection and independent regulatory adjudication.

To run from the repo root on an authorized networked machine:

```sh
mkdir -p /secure/temporary/fda-research
PYTHONPATH=new-platform/backend python new-platform/backend/scripts/capture_hop_fda_original_https.py /secure/temporary/fda-research
```

A CI research-only workflow,
`.github/workflows/hop-fda-original-source-capture.yml`, attempts both
public URLs on pull requests modifying this tool. If successful it retains
PDF and provenance files as a **14-day GitHub Actions artifact**, not as
permanent storage. If source access is unavailable, the job prints
`SOURCE_CAPTURE_BLOCKED` and does not claim a hash. The workflow is
**informational**, separate from the mandatory software test pass status.

All software regression fixtures use **synthetic pseudo-PDF byte streams**
and fake HTTP clients and therefore demonstrate only security boundaries:
strict origin, no cross-host redirects, bounded bytes, refused source
overwrites, mismatch detection, and the untrained/no-probability outcome
status.

## Essential scientific boundary

Even a successful, original-host HTTPS PDF download, SHA-256, and reference
ID match **do not prove** (1) the original public release date of the PDF,
(2) the historical application/review-cycle ordinal, (3) the first public
decision label date, (4) a population-complete FDA denominator, (5) frozen
predecision clinical features, or (6) independent reviewer signoff.
Publication chronology from FDA/issuer press releases remains a separate
research lead with its own uncertainty.

Model-eligible historical cycles remain **zero**; real independent
backtests **zero**; PASS/FAIL prediction confidence and calibration
**unavailable** until genuine cohort and evidence adjudication are complete.
