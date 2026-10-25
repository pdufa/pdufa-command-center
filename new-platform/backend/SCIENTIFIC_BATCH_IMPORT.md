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

## Secure review web panel and durable batch history

Open the **isolated** review-service page:

`https://pdufa-scientific-assessment-review.onrender.com/scientific-assessment/batches`

Enter the review service's **PDUFA_INTERNAL_API_KEY** directly in the browser field (never paste it into chat, URLs, source code or logs). The page uses same-origin requests with the `x-pdufa-internal-key` header and never writes the key into browser storage. Public visitors can load the static shell, but cannot read job history or submit imports without the key.

The review-only POST requires all of:
1. An authenticated internal API key.
2. Persistent PostgreSQL available.
3. `PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED=1` on the Render **review service**.
4. Render's automatic `RENDER_SERVICE_ID=srv-dbehn9fb9u1s739ok5vg` identity.

The production service ID is not allowed. **Do not set this write flag on production.** This opt-in is specific to scientific archival imports and does not unfreeze checklist migrations or enable production trading/scans.

### API

- `POST /api/scientific-assessment/batches` accepts `{"nct_ids":["NCT04280705","NCT02142738"]}` and responds HTTP 202 with a newly persisted job.
- `GET /api/scientific-assessment/batches` returns the 20 newest job summaries.
- `GET /api/scientific-assessment/batches/{job_id}` returns the recorded per-trial outcomes.

Each endpoint requires `x-pdufa-internal-key`. No API secret is included in the static page source. The service accepts only one unfinished batch at a time using a unique PostgreSQL active slot; concurrent submission gets HTTP 409. Batch processing is explicitly started by the authenticated POST and runs sequentially in the service process. Results are committed to PostgreSQL after each attempted trial and survive normal restarts.

**Crash limitations:** A forced instance shutdown can leave a queued or running job row with its active slot reserved. The system deliberately **does not automatically resume or retry** such a job; restarting could duplicate requests while an old instance is still operating. An administrator must verify the old worker is stopped and reconcile the unfinished job before allowing another. Do not manually delete a job without first recording its outcome. A separate safely fenced interrupted-job recovery workflow is needed before high-volume operation.

The browser updates the selected job every four seconds while queued or running. This is **status polling only**, not a scientific source scan.
