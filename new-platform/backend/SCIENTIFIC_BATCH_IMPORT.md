# Scientific Assessment: bounded manual batch import

**Scope:** isolated scientific review environment only. This workflow is intentionally **not** scheduled and does not touch production scanners, orders, or trading.

## Run an explicit batch

Run only in a backend environment configured with the isolated review **persistent PostgreSQL** database. Credentials remain in the environment; do not paste them into commands, source, or logs.

Create a plain UTF-8 file `trial_ids.txt` containing one exact NCT identifier per line:

```text
NCT04280705
NCT02142738
```

From `new-platform/backend` run:

```bash
python -m app.scientific_batch_import --batch-file trial_ids.txt
```

No more than **25 identifiers** per invocation. Duplicate or malformed IDs and oversized input are rejected **before any imports**. Each import uses the existing checksum-protected, identity-validated ClinicalTrials.gov archiver; imported records are idempotent. Requests are sequential with a one-second gap, not parallel.

## Progress, failures, and exit codes

One JSON line is printed at batch start, after each attempted trial, and at the end. Fields include `index`, `total`, `nct_id`, `status`, `processed`, `imported`, `already_exists`, and `failed`; failed trials also report a sanitized `error_type` and `http_status` when available. Errors in a trial do not stop later trials.

- `0`: all attempts imported or already existed
- `1`: entire batch rejected (invalid input, missing file, or non-PostgreSQL destination)
- `2`: one or more individual trials failed; other trials still processed

A failure should be reviewed against the registry before explicitly retrying it. There are **no automatic retries**, background scans, or scheduled jobs. Raw exception messages, database URLs, and response bodies are not printed.

**Limitations:** JSONL output is live process output, not a database-backed job history, UI progress panel, or guaranteed durable report. To retain output, arrange log capture in a controlled execution environment. Merely deploying this module does not import additional trials: a separately initiated batch command is required.
