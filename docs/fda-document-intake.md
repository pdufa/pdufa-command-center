# Quarantined FDA PDF intake

`scripts/ingest_fda_documents.py` adds an original-byte retention boundary to the
existing FDA document availability probes. The probes retain a digest; this tool
can retain the supplied/downloaded PDF bytes and the exact input manifest together
with a receipt. It does not populate the historical outcome corpus, infer review
cycles, extract scientific features, or authorize training or prediction.

## Manifest

The JSON envelope has exactly `schema_version: 1` and `documents`, an array of
1–20 document objects. Each object requires:

| Field | Meaning |
| --- | --- |
| `id` | Unique bounded identifier; letters, digits, underscore, dot or hyphen |
| `url` | Original exact FDA HTTPS document URL |
| `document_date` | Declared date printed on the document, `YYYY-MM-DD` or null |
| `publication_date` | Separately established declared public-availability date, `YYYY-MM-DD` or null |
| `relative_path` | Offline mode only: nonempty path beneath the explicit source directory |
| `expected_sha256` | Required offline, optional for download: lowercase SHA-256 of the intended PDF bytes |

Unknown fields, duplicate JSON keys/IDs/paths, invalid dates, future dates, and
caller-supplied verification/outcome/model flags are rejected. Do not substitute
a letter's date for its publication date or its effective FDA action date.
`publication_date: null` explicitly records unknown public availability. All
manifest identity/date/URL fields are declarations requiring source review.

Allowed source hosts are exactly `www.fda.gov`, `accessdata.fda.gov`,
`www.accessdata.fda.gov` and `download.open.fda.gov`. URLs cannot carry credentials,
ports, query strings or fragments. A new URL requiring redirection must be reviewed
and declared explicitly. The tool does not rewrite source URLs.

## Offline originals

Run without `--output-dir` to inspect supplied bytes and emit a JSON report without
writing an archive:

```bash
python scripts/ingest_fda_documents.py manifest.json --source-dir /path/to/reviewed-export
```

With an explicit **new** destination, retain the exact manifest,
content-addressed `<sha256>.pdf` bytes and `receipt.json`:

```bash
python scripts/ingest_fda_documents.py manifest.json --source-dir /path/to/reviewed-export --output-dir /path/to/new-quarantined-archive
```

The source directory and all nested paths must be real directories/files, without
symlinks. Traversal, FIFOs and other special files are rejected. ZIP archives are
not extracted. Files are read with bounded stable-file checks and every offline
digest must match before any destination is created. The manifest is limited to
1 MB, PDFs to 20 MB each, and the whole batch to 100 MB. No prior files are
overwritten or removed. A filesystem failure while writing may leave a partial
new archive; a successful archive has its complete `receipt.json`.

An offline receipt records the time these bytes were **received**, leaving
`retrieved_at` null. It cannot establish who retrieved the original, the URL that
served those bytes, or when the original first became public. A matching hash
only establishes consistency with the supplied expected hash.

## Direct acquisition when authorized source access is available

```bash
python scripts/ingest_fda_documents.py download-manifest.json --mode download
python scripts/ingest_fda_documents.py download-manifest.json --mode download --output-dir /path/to/new-quarantined-archive
```

Download dry runs validate the manifest and make **no network request**. Explicit
new output directories enable acquisition through the inherited proxy and default
verified TLS. Only an HTTP 200 response from the exact declared URL, an accepted
PDF media type and bounded PDF-header-bearing bytes can be retained. Redirects,
changed URLs, HTML responses, oversize content and digest mismatches fail closed.
The tool does not alter network policy or bypass a source-access denial. Download
receipts record actual acquisition time separately from declared source dates.

The present cloud policy excludes FDA hosts. Automated tests exercised mocked
HTTP behavior and synthetic local bytes. A real acquisition attempt using the
ZEVASKYN manifest failed with `Tunnel connection failed: 403 Forbidden` before
an archive was created; no real PDF was acquired by this CLI.
Supported connected-tool document observations are a separate evidence type
and must not be relabeled as retained original PDFs.

## Required review boundary

Receipts always have `original_source_authenticity_verified: false`,
`independently_verified: false`, `review_cycle_verified: false`, `outcome: null`
and `model_eligible: false`. Verified PASS/FAIL and model-eligible record counts
remain zero; approval probability remains null. A PDF header does not validate
PDF semantics. Review must still establish source authenticity, application,
drug/indication, effective action date, submission/review cycle, final versus
nonbinary action, and the chronology of independently sourced predecision
features. Hashes and successful HTTP requests do not replace those judgments.

The archive is a development/review artifact. No database, live scanner,
restriction/FS/FA association, production setting or trading behavior is changed.

Validation: `python -m pytest -q tests/test_ingest_fda_documents.py`. The test
fixtures measure software integrity safeguards, not real FDA prediction accuracy.
