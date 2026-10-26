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

## Nightly scan health on the dashboard

In **PDUFA → PIPELINE**, the separate **Nightly research scan · GitHub status** panel queries an authenticated, read-only server endpoint, which checks public GitHub scheduled runs. It does **not** recalculate or update the pinned historical 741-study scorecard.

The health panel checks the actual `research-ledger` job for scheduled MAIN workflow runs, and requires the exact named research-only artifact to exist and be unexpired before saying a full scan completed. It distinguishes:

- **No full scheduled research scan observed:** before the nominal night's 10:30 PM Pacific grace deadline, or only deliberate seasonal DST-alternate skips before the deadline.
- **Expected scheduled scan overdue:** after **10:30 PM Pacific**, if no full source-run attempt is observed for the expected Pacific research date. This persists into the following day until the next nightly deadline; a yesterday-successful run or a deliberately skipped DST alternate does not satisfy tonight's requirement. It means GitHub has not shown a qualifying full run by the grace deadline, **not** that the source data, clinical study, or commercial-rights claim failed.
- **Scheduled research scan in progress:** the actual source job has not finished.
- **Completed, report confirmed:** the full source job succeeded and its artifact exists.
- **Last result stale:** the most recent full job succeeded, but is more than 36 hours old.
- **Failed full source scan:** the source job or DST gate failed/cancelled.
- **Report artifact missing:** workflow/job success does not establish a downloadable research report.
- **GitHub status unavailable:** retrieval or validation failed; never displayed as a successful scan.

The **Refresh status** button checks again. The source API uses a short cache to avoid exhausting GitHub's public rate limit; the check timestamp is displayed. Job runs that intentionally skip due to the paired UTC daylight-saving schedule are not counted as successful full scans. Link directly to the selected full GitHub run for inspection.

The overdue indicator deliberately uses the original schedule activation date (**October 26, 2026**) to avoid claiming that the nightly workflow missed days before installation. It uses `America/Los_Angeles` calendar days across both spring and fall daylight-saving transitions; scheduled jobs that start many hours late on the next day are attributed to the prior night's expected window until the following 7 PM local schedule window. The grace period does not guarantee GitHub will ever start a delayed job. A current full scan marked failed or in progress overrides an overdue warning. A GitHub API error reports **status unavailable**, never a definite missed scan.

**The daily scan status is not the live PIPELINE/GEM collector** and does not independently prove registry coverage, SEC primary-document access, company commercial rights, clinical outcome prediction, or any current candidate membership. Pinned evidence numbers remain fixed until independently republished and reviewed.

## Source artifact integrity manifest

Each successful full `research-ledger` scan now validates **16 expected output files before upload**, then writes a seventeenth file named `main_phase3_run_integrity_manifest.json`. The manifest records the exact GitHub run ID, commit SHA, trigger event, Pacific research date, original filename, byte count and SHA-256 hash for each of the 16 source reports. The same step reconciles **741 exact distinct registry trial IDs** across related reports, **130 issuer research pointers**, **6,669 nine-gate check slots**, and **4,446 commercial-rights review slots**. It also confirms that research-only qualified-Pipeline claims remain **unknown** and commercial rights have not been autonomously promoted.

If an expected source report is absent, corrupt, has duplicate NCT IDs, has mismatched denominators, or contains an unsupported promotion, the validation step fails the research job. The artifact upload uses `always()` to retain forensic debugging files on failed attempts, so **the presence of an uploaded ZIP by itself does not prove a successful nightly scan**. Check the job conclusion, required artifact presence and integrity step outcome. GitHub Actions can still delay its nominal 8 PM Pacific schedule.

**SHA-256 checks document-byte integrity only**; they do not authenticate FDA/SEC external claims, validate commercial development rights, or make the historical study census a qualified Pipeline count. The dashboard scan-health indicator checks the scheduled job conclusion, the stable, named **research artifact integrity-validation step**, and the unexpired research artifact, in that order. It shows **integrity unverified** rather than success if that step is absent, failed, or skipped. It does not download and independently validate individual ZIP contents or source hashes; success here means the GitHub runner reported executing the validator successfully.

## Original registered status and update recency

Each full run now produces `main_phase3_registry_status_recency.json` and a sortable `main_phase3_registry_status_review.csv` with one source-linked row for each of the 741 historical NCT studies. The current overall ClinicalTrials.gov status, dated-census status, and whether Phase 3 remains registered are separately reported. Posted-update ages are grouped into 0–90, 91–180, 181–365, over 365, missing, and future-date-review categories, with exact-NCT source hashes.

The summary contains a collapsed status/recency section below the nine main qualification gates. Review priorities are **source-research priorities**, never stock or approval rankings. Neither a RECRUITING registry status nor a recent posted update independently establishes active commercial development; likewise, COMPLETED or a stale posted update does not prove development has ended. The independent `active_phase3_development`, `original_source_freshness`, commercial-rights, and FDA qualification gates remain REVIEW until separately substantiated.

Both new files are now part of the SHA-256 nightly integrity manifest and their NCT scope, summary denominators, and nonpromotion flags are checked before the research artifact is published.
