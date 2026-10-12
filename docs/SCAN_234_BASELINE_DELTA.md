# #2 / #3 / #4 PDUFA baseline-first scanner contract

State: **DESIGN / PREFLIGHT ONLY**. This document does not activate a scheduled job,
call external sources, or certify coverage. The prior per-source GitHub scan
workflows were removed at the user's request and must not be silently restored.

## Source of truth and identity

* Snapshot the entire tracked universe at the start of each run, including all
  companies in `data/company_registry.csv`, all known NCT trials, exact
  company-drug-indication programs, NDA/BLA events, and active/historical PDUFA
  events. Keep the snapshot ID immutable for that run.
* The key for a clinical program is **ticker / issuer CIK / NCT ID / drug /
  indication** where available; FDA applications need their application or
  exact regulatory event key. Ticker alone is never sufficient to infer Phase 3
  success, financing completion, a PDUFA date, or drug ownership. Missing
  identity evidence goes to REVIEW; it is never joined indiscriminately.
* One canonical source ledger feeds all three dashboard views. Do not make three
  redundant ClinicalTrials.gov or SEC requests for the same evidence.
* Track a field's value, prior value, observed date, event date, provider,
  evidence URL, source record ID, evidence hash and verification state. A score
  is a derived output, not a primary source.

## Gate A — one complete **BASELINE** first

1. **#2 PIPELINE (full scope):** all tracked sponsors, clinical trials, drug
   modalities, phases, intervention/route, indications, milestones, outcome
   postings, Phase 2→3 transitions, NDA/BLA and post-decision follow-up;
   reconcile program identity and status for every company.
2. **#3 PRE3 (all qualifying + review rows):** Phase 2 primary p and linked
   source, Phase 3 protocol/design (primary/secondary endpoints, powering,
   randomization, comparator, follow-up, population, missing data), safety,
   readout date, actual readouts where posted, issuer announcements, financing
   stage and clinical/research score inputs. Missing p is UNKNOWN, not FAIL.
3. **#4 POST3 (all qualifying + review rows):** exact drug/indication Phase 3
   results, significance and effect sizes, safety, NDA/BLA acceptance, FDA
   actions/PDUFA extensions/CRLs/approvals, closed second financing evidence,
   ATM/dilution, cash/runway, product revenue/pipeline, borrow/short/IV when
   obtainable, daily price/volume, entry gates and trading score inputs.
4. Final consistency pass across the three outputs: same identity, event date,
   evidence citation, source timestamp and classification, with separate
   regulatory probability and market/trading score dimensions.

Required source families are ClinicalTrials.gov, FDA/public regulatory
documents, SEC filings, issuer announcements and the public-market feed.
Company-specific commercial metrics and options/borrow inputs are required
when relevant and available; unsupported data must be explicit rather than
inferred. The old `scripts/overnight_scan.py` calls only three clinical
collectors and CANNOT certify this full baseline.

**Completion:** mark the overall baseline COMPLETE only if every due identity
received every required supported check and the audit contains no unresolved
coverage gaps. COMPLETE WITH WARNINGS means all due records were attempted but
some sources are stale/unavailable/conflicting. PARTIAL means anything due was
not attempted/finished; FAILED means the run could not meaningfully execute.
An SEC HTTP 403 is never evidence of no filing or a completed financing.
Checkpoint between batches and resume remaining work without deleting
verified historical evidence.

## Gate B — **DELTA** after verified baseline

Every night:
* Inventory ALL active tracked identities, including new companies, new NCTs,
  new applications, new indications and previously known records.
* Lightweight-check **every tracked identity** for source update timestamps,
  SEC filing arrivals, FDA events, issuer releases and latest market session.
  Only the expensive detail extraction is restricted to NEW, CHANGED, CONFLICT,
  STALE, time-sensitive and previously FAILED checks.
* Retrieve and review full evidence for queued items, write old/new field diffs,
  update score history and attribute score changes to the source evidence.
* Detect phase movement #2 → #3 → #4 without removing a program from its
  longitudinal history; keep historical FDA and financing decisions.
* Persist per-source/per-identity checkpoints, rate-limit retries and failure
  reasons. Publish a Pacific-time digest of changes or NO NEW FINDINGS.

Nightly change checks are **not** only discovery of new tickers. That would
miss a changed PDUFA date, funding closure or failed endpoint on existing
programs. Deep-check near-catalyst records more frequently and perform a
periodic full reconciliation to catch missed source updates.

## Implementation sequence

1. Inventory + canonical identity + source-coverage ledger + checkpoints.
2. Wire existing ClinicalTrials.gov collectors and exact-NCT endpoints.
3. Integrate/verify FDA + issuer evidence.
4. Restore SEC access correctly with a compliant, identifying User-Agent and
   permitted API access. Keep 403 as BLOCKED; never guess a status.
5. Wire market/ownership/short/IV providers with source-specific limitations.
6. Recalculate scoring and publish the three consistent dashboard feeds.
7. Execute one manually started **BASELINE** in resumable batches. Review
   exceptions and the end-to-end ledger.
8. Only after the baseline gate passes, enable scheduled **DELTA** with a
   recurring deeper reconciliation and failure alerts.

**No overnight scan schedule is currently re-enabled by this plan.**
Existing scanner Python files and historical CSVs are preserved.

## Preflight command already available

`python scripts/scan_234_preflight.py`

This performs a read-only count/checksum inventory of all locally saved source
files needed for each view and writes `reports/scan_234_preflight.json`.
It does **not** contact external sources. Its success means only that inputs are
present; it always marks the full baseline unverified and nightly automation
disabled. The next implementation task is wiring the actual source-fetching
orchestrator with resumable checkpoints and a complete per-identity ledger.

## Mandatory two EMAIL alerts per scan (CRITICAL)

The user prefers **two emails per separately executed scan** while the
RingCentral/SMS delivery path remains unverified. This applies to all
#2 PIPELINE, #3 PRE3, #4 POST3 baseline/delta/deep/reconciliation scans and
any source collector run as its own separately tracked scan. Three scans
produce **six emails total**.

* **START** email before any data fetch: scan name, scan mode, start timestamp
  in America/Los_Angeles, run ID and dashboard link.
* **END** email upon completion or failure: scan and mode, status, finished
  timestamp in Pacific time, duration, actually checked/due identities,
  verified new/changed records, errors/warnings and dashboard link.
* Every END summary uses a *fresh, updated* output manifest. The scanner may
  claim COMPLETE for #2/#3/#4 only when the full-source ledger explicitly
  says `full_coverage_verified=true`; clinical-only completion is not enough.
* Failed jobs, blocked sources and subprocess timeouts still attempt an END
  email. An abrupt runner shutdown/host crash can prevent the final email;
  an independent watchdog or durable queue is still required to guarantee
  crash recovery. Do not claim device/email delivery merely because SMTP
  accepted an email.
* The scanner must **not start** if mandatory START email submission fails.
  No blind retry after an ambiguous provider response (avoid duplicates).
* A notification audit checkpoint is saved before starting each scan.
  Email credentials must only be injected through GitHub Actions secrets.

Current implementation:
`scripts/scan_email.py` + `scripts/run_scan_with_email.py`.
The generic wrapper does not enable a scan schedule by itself.
Tests: `tests/test_scan_email_notifications.py`.

Setup these private GitHub repository Actions secrets:

```text
PDUFA_GMAIL_USER
PDUFA_GMAIL_APP_PASSWORD
PDUFA_ALERT_EMAIL
```

Use the connected Gmail account as the sender if supported; Google app
password availability depends on Gmail account security settings and is
separate from the Gmail connection to ChatGPT. The password must NOT be
pasted into ChatGPT or committed to source code. Read:
`docs/GMAIL_SCAN_ALERT_SETUP.md`.

A manual one-email test is at
`.github/workflows/email-delivery-test.yml`.
The previously built SMS provider and the manual SMS test remain stored in
the repository as optional experiments; they are **not** the chosen
production notification path and no SMS is required to run the future
Gmail-notified scanner.

Example of the new wrapper, using one **clinical source-only collector**:

```bash
python scripts/run_scan_with_email.py --scan 2 --mode BASELINE \
  --status-file data/all_phase_scan_state.json --timeout-seconds 3000 -- \
  python scripts/all_phase_scan.py
```

This example is NOT a certified all-source #2 baseline. The END email must
therefore report UNVERIFIED, even if the local clinical collector says COMPLETE.

**Current state:** An initial delivery test using the connected ChatGPT
Gmail account was submitted successfully, but GitHub Actions SMTP secrets
are not configured/verified, and production scan notifications are not
active. No nightly scan workflow has been restored.

## Capacity guidance (planning, not a run promise)

The 717-company registry's prior clinical-only collector finished quickly,
but that is NOT all-source coverage. For an audited full FDA/SEC/issuer/clinical/
market baseline, reserve multiple source-bounded runs, provisionally **3–8+
hours** across checkpoints; blocked sources can extend the process until fixed.
A carefully indexed nightly delta may take **30–120 minutes**, depending on
provider limits, provider coverage, exception count and market-data access.
Benchmark each source on small batches and revise estimates before activating
a fixed nightly window.
