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

## One-time authenticated live HTTP smoke verification

The isolated review service can exercise its real loopback HTTP API using its
**existing environment-held internal API key**. No API key is pasted into chat,
GitHub, logs, a browser URL, or a test fixture.

1. Confirm the review PostgreSQL database already holds `NCT04280705`,
   has no active batch, and the isolated review service ID is
   `srv-dbehn9fb9u1s739ok5vg`. Ensure the review-only import switch is on.
2. Temporarily set `PDUFA_SCIENTIFIC_SMOKE_NCT=NCT04280705` **only**
   on that review Render service and deploy the reviewed feature branch.
3. After app startup, a **one-shot** daemon thread contacts
   `http://127.0.0.1:8000` to verify unauthorized requests return 401,
   authenticated list requests return 200, and the authenticated POST
   returns 202. It polls the new job until one existing trial is confirmed
   `already_exists` without changing the stored trial archive.
4. Inspect `SCIENTIFIC_E2E_SMOKE status=PASS` or a sanitized FAIL/SKIPPED
   reason in review logs. The stored batch history also records the attempt.
5. **Immediately clear** `PDUFA_SCIENTIFIC_SMOKE_NCT` and redeploy.
   Leaving it configured can cause repeat attempts after future restarts,
   although a durable single-ID-job replay guard prevents repeat submission
   once such a job was recorded.

### Concurrent deployment replay guard

A deployment overlap revealed that two startup test workers could each pass
the earlier read-only check. The updated test now atomically inserts an exact
NCT claim into `scientific_smoke_claims` **before** making any HTTP request.
The PostgreSQL primary key guarantees only one worker can claim an NCT, even
if multiple review instances have passed a stale preflight at the same time.
The claim records pass/fail and remains in the database; it never resets
automatically. Startup logs include `smoke_claim_count` to verify the table.

Two smoke jobs completed successfully before this atomic fix was added. Both
returned `already_exists`, and the clinical trial archive stayed at two.
The smoke setting was then cleared and the review deployment completed.
Any future smoke attempt for a different existing NCT must be explicitly
authorized again; no production or bulk trial imports are enabled.

The smoke test will **skip** instead of importing if the exact trial is not
already archived, the service identity differs, the DB/key/switch is absent,
an unfinished batch holds the exclusive slot, or a prior identical single-ID
batch already exists. If the registry/network fails, it logs FAIL and leaves
the durable job intact; there is no automatic retry, unlock, or cleanup.
The smoke does not confirm external-browser functionality and does not
constitute scientific efficacy or safety verification.
