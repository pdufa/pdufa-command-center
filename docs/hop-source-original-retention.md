# Optional original FDA bulk-source retention

The CRL and Drugs@FDA collectors previously retained derived snapshots and archive
digests. Those artifacts do not contain the original FDA download manifest or ZIP
bytes. `--retain-originals-dir NEWPATH` now preserves exact source bytes during a
future successful collection, without changing default collector output.

```bash
cd new-platform/backend
PYTHONPATH=. python scripts/collect_hop_openfda_crl.py --output-dir /existing-parent/crl-derived --retain-originals-dir /existing-parent/crl-originals-new
PYTHONPATH=. python scripts/collect_hop_drugsfda.py --output-dir /existing-parent/drugs-derived --retain-originals-dir /existing-parent/drugs-originals-new
```

The retention flag is optional and has not been enabled in any workflow. The
destination must be new, its parent must already exist, and all parent directories
must be real directories rather than symlinks. Existing destinations are refused
before network work and checked again before writing. No existing data is
overwritten or removed.

With retention enabled, the collectors use `app/hop_source_receipts.py` to capture:

- `manifest.original.json`: exact bytes from the fixed official
  `https://api.fda.gov/download.json` URL, preserving original formatting.
- `<sha256>.zip`: exact archive bytes, content-addressed and never extracted by
  the retention helper.
- `source-receipt.json`: URL-to-file mapping, SHA-256, byte size, actual completed
  retrieval time for each source, batch start time, explicit unknown document and
  publication dates, and research-only restrictions.

Each source URL is validated before its request. The manifest URL is fixed;
archives require the exact official `download.open.fda.gov` host and the selected
CRL or Drugs@FDA source prefix. Credentials, ports, queries, fragments and
redirects are refused. The inherited proxy and default verified TLS remain in
use; source access denials are not bypassed. Individual reads retain their
collector limits, with an additional 24 MB maximum capture, 64 captures and
256 MB total bound.

Retrieval time is sampled after each response has been fully read and hashed,
separately from `intake_started_at`. A document acquired after a cutoff cannot
become available at that cutoff merely because its batch started earlier.
Regressing clocks are rejected. Neither the source export date nor a letter date
is substituted for original public availability; `publication_date` and
`document_date` remain null in the byte receipts.

The collectors first run their existing source staging and write their normal
derived outputs. Only then do they retain originals, after cross-checking every
archive digest against the existing staging audit. Invalid source data or failed
staging creates no original archive. Retention also rehashes captured bytes before
writing. Files are created exclusively with symlink protection, and the receipt
is written last. A filesystem failure can leave a partial new directory; the
collector reports failure, and an incomplete directory is not a successful
receipt.

These receipts establish byte acquisition provenance only. Source-content,
application, review-cycle and outcome verification flags remain false; verified
PASS/FAIL and model-eligible counts remain zero, and prediction probability
remains null. Original source retention cannot establish a complete historical
denominator, manufacture predecision evidence, or validate prediction accuracy.
Previously derived artifacts cannot be retroactively relabeled as original FDA
bytes. This change makes no database, production, schedule, restriction, FS/FA or
trading changes.

Validation uses synthetic test archives and mocked HTTP responses:

```bash
PYTHONPATH=new-platform/backend python -m pytest -q new-platform/backend/tests/test_hop_source_receipts.py
```

No real FDA request was made while developing these changes. The current cloud
policy still excludes direct FDA hosts; the optional flag does not grant access.
