# MAIN Phase 3 nightly qualification research scan

The source-grounded **741-study historical research pipeline** runs nightly at a **nominal 8 PM America/Los_Angeles** after this workflow is merged to `main`. The scan is a GitHub Actions read-only evidence report and **not** the application's live candidate/scanning engine, an FDA filing monitor, or a trading signal.

## Scheduling

GitHub Actions cron uses UTC and cannot directly express Pacific daylight-saving changes. The workflow lists **two UTC schedules**:

| Pacific season | Nominal UTC trigger | Gate result |
|---|---|---|
| Daylight saving (PDT) | 03:00 UTC on the following date | Full source check |
| Standard time (PST) | 04:00 UTC on the following date | Full source check |
| Opposite-season UTC trigger | The other listed hour | Skip full source check deliberately |

The `pacific-nightly-gate` job checks `America/Los_Angeles` on execution and only enables `research-ledger` for the correct seasonal trigger. Both schedules appear in workflow history; **one is intentionally skipped**. Do not classify a correctly skipped alternate as a failed nightly scan. GitHub may delay, suppress, or drop scheduled starts during high load or service outages; there is no guarantee of exact 8 PM arrival. Pull requests and manual `workflow_dispatch` always bypass the time gate so they can be tested and run immediately.

## What is generated on the full run

- Original ClinicalTrials.gov identity evidence for **741/741 historical NCT study records** and linked **130/130 SEC issuer pointers**, subject to source availability.
- Nine mandatory Pipeline qualification checks per record (**6,669** trial/gate slots) with PASS/FAIL/REVIEW counts and denominators.
- Six independent commercial-rights evidence checks per record (**4,446** trial/review slots), including submitted-source/reviewer coverage.
- SEC issuer indexes and up to 20 SEC primary-document pilot leads, with requested/fetched/missing-contact counts clearly separated.
- GitHub Actions job summary with the main metrics first and the nine-gate/secondary details in collapsible sections.
- JSON, a human-readable Markdown scorecard, and a 741-row CSV rights review list in the read-only `main-phase3-evidence-qualification-research-only` Actions artifact.

Artifacts are retained for 30 days, subject to the repository's retention policy. Long-term archival needs a separate reviewed storage/backup workflow; ephemeral GitHub Actions artifacts are **not** a permanent journal.

## Where to view the latest run

Open the repository's [MAIN Phase 3 evidence-to-qualification workflow](https://github.com/pdufa/pdufa-command-center/actions/workflows/main-phase3-evidence-qualification.yml). Select the latest completed full `research-ledger` job, rather than its skipped off-season alternate. Use its **Summary** and the **research-only artifact**.

The public dashboard's **PDUFA → PIPELINE** historical panel is currently a **pinned, dated verified snapshot**, not a dynamically refreshed feed. The nightly workflow does not silently rewrite or publish that snapshot. A future release can add a reviewed snapshot-publishing step with source-run provenance and gate checks.

## SEC primary-document blocker

The pilot needs the actual organization contact secret `SEC_USER_AGENT`. Until a real contact is configured, it will intentionally report 0 attempted SEC primary-document requests (with a denominator for selected leads). Do not fabricate a User-Agent or interpret this as adverse legal-rights evidence.

**Scope guarantee:** None of these runs adds historical census trials to live Pipeline or GEM JR/GEM, changes the Pipeline **$300M–$10B** market-cap restriction, reassigns independent FS/FA preset memberships, creates trades, or claims PDUFA/FDA outcome predictions.
