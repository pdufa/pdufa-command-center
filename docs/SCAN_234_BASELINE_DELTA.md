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

## Mandatory two SMS texts per scan (CRITICAL)

**Contract:** Every individually executed scan, including #2 PIPELINE,
#3 PRE3, #4 POST3, source collectors, deep reviews, reconciliations and
nightly deltas, submits **exactly one START text before collecting data and
one END text with an actual results summary when execution ends**. When three
individual tabs are scanned, that means **six SMS messages total**. These
are scan-level notifications, not per-ticker texts.

* START contains scan name, baseline/delta/deep mode, Pacific start time and
  run ID. It must be acknowledged by the SMS provider BEFORE scanning starts.
* END contains completion status, verified checked/due count, new/changed
  records, warnings/errors when supplied by a *newly updated scan ledger*,
  run duration and run ID. If there is no fresh verified ledger, text
  **UNVERIFIED** instead of fabricated counts.
* END is attempted after success, partial coverage, nonzero exit or caught
  scanner failure. If the final SMS fails, retain the job failure in a JSON
  notification audit; never silently claim that the user received it.
* The SMS transport sends **one ASCII single-segment message**, with no
  automatic retry after an ambiguous carrier/provider outcome (avoids duplicate
  SMS). The provider accepting a message does **not** prove iPhone delivery.
* **Critical precondition:** if provider secrets are not configured, or the
  START text isn't acknowledged, do not run the scanner. It is safer to delay
  scans than to silently violate the notification requirement.
* The notifier runs through a generic command wrapper so a newly added scan
  must opt into the same enforced contract, rather than implementing its own
  untested notification rules.

Implementation: `scripts/scan_sms.py` (Twilio REST API via Python stdlib),
`scripts/run_scan_with_sms.py` (scan command wrapper + audit log), and
`tests/test_scan_sms_notifications.py` (success/failure/duplicate guards).
For production, store the following **only as repository Actions secrets or
runner environment variables**, not in Git or logs:

```text
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
PDUFA_SMS_TO_NUMBER
```

The sender must be an SMS-capable number provided by Twilio and the recipient
must be a validated E.164 mobile number. The generic invocation is:

```bash
python scripts/run_scan_with_sms.py --scan 2 --mode BASELINE \
  --status-file data/all_phase_scan_state.json -- \
  python scripts/all_phase_scan.py
```

**This example runs only the existing clinical inventory collector, not a
certified all-source baseline.** All future workflows must call the wrapper for
*every separately executed scan* rather than bypassing it. The wrapper writes
`reports/scan_notifications/<run_id>.json` for auditing. Retain those audit
records in a protected log/artifact; they do not include Twilio credentials.

Current state: **SMS credentials are not configured or verified; no texts have
been sent from this code, and no nightly scanning workflows were re-enabled.**
The earlier ChatGPT push-notification test is distinct from SMS and cannot
be used by a GitHub worker as a substitute for these two texts.

## Capacity guidance (planning, not a run promise)

The 717-company registry's prior clinical-only collector finished quickly,
but that is NOT all-source coverage. For an audited full FDA/SEC/issuer/clinical/
market baseline, reserve multiple source-bounded runs, provisionally **3–8+
hours** across checkpoints; blocked sources can extend the process until fixed.
A carefully indexed nightly delta may take **30–120 minutes**, depending on
provider limits, provider coverage, exception count and market-data access.
Benchmark each source on small batches and revise estimates before activating
a fixed nightly window.
