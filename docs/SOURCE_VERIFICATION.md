# Nightly source verification

The nightly source workflow now collects evidence, verifies specific claims,
and reconciles the resulting ledgers. Successful execution alone does not prove
that a source claim is correct or that the full trading baseline is complete.

Every ledger finding has one status:

| Status | Meaning |
| --- | --- |
| VERIFIED | The named claim passed the source, identity, date, and data checks applicable to its scope. |
| NOT_APPLICABLE | Same-period primary financial facts establish that a finite cash-burn runway does not apply because operating cash flow is nonnegative. |
| UNAVAILABLE | A separately identified supplemental market field is unavailable; this is never accepted as a verified trading input. |
| REVIEW_REQUIRED | Required evidence is missing, ambiguous, stale, or outside the automated check's scope. |
| CONFLICT | A primary/provider value or identity disagrees with the saved claim. |
| TECHNICAL_FAILURE | The worker could not retrieve or inspect the required response. |

Source ledgers include the event and ticker, claim, expected and observed value,
reason in English, source URL, response SHA-256, fetch timestamp, and evidence
excerpt. They are saved with the scan artifacts. The combined audit also saves
`combined_verification.csv` and the full `verification_review_queue.csv`.
The final Gmail summary separates verified, unresolved, conflicting, and
technically failed checks.

## October 13 required-item repairs

Exact event mappings in `config/issuer_sources.json` provide official source
links and documented drug/indication aliases. They never supply expected dates,
cash balances, outcomes or verification statuses. Each source is fetched again
and subjected to the same issuer, program, indication and claim checks. A map
for another event cannot be used. For a clinical-data supplement, the FDA-signed
letter can be paired with its FDA-approved label only when application number,
supplement number and year match; the label supplies the full indication while
the letter supplies the signed effective action date.

Funded loan receipts, completed securities sales and `placement closed on`
clauses are recognized without treating agreements, available facilities,
quarter-end ATM totals or anticipated dates as exact closes. Discovery links
retain the original expected closing date. A verified individual transaction
still does not automatically verify its ordinal after the Phase 3 readout.

When current USD Companyfacts are missing, a reviewed SEC interim statement
layout may supply cash and operating flow. Company/CIK, reporting period,
currency, current/prior column order, unit scale, signs and unique table/row
matches must pass. Numeric values are always parsed from the freshly fetched
source, never copied from configuration. Foreign-currency values remain outside
the USD claim, and missing same-period operating flow remains unresolved.

The Synergy registry row now uses SNYRQ/OTC while retaining CIK 0001562733;
the live SEC identity check must independently confirm that ticker. Nuvation's
abbreviated disease label is expanded to the FDA-label wording. These source
repairs do not change probabilities, scores or trading eligibility.

## Checks by source

| Source | Implemented checks and scope limits |
| --- | --- |
| FDA | FDA pages, company-matched SEC documents, or explicitly mapped official issuer hosts; drug, indication, and explicit claim date. FDA pages also require company identity. A reported PDUFA target cannot become a decision date. A past target with no resolved outcome remains under review. Publication dates cannot substitute for action dates. |
| SEC | Nonempty submissions response with matching CIK and ticker, valid filing identities, and aligned arrays. A filings inventory does not establish insider accumulation. Legacy records can have blank primary-document names without invalidating the dated accession inventory. Event-matched financing review ledgers supply documents to inspect again. A completed, dated, quantified transaction clause can verify that closing; it does not certify the post-Phase-3 second-financing sequence. |
| FINANCIAL | Matching Companyfacts CIK, current USD cash facts, including transition and applicable foreign filing forms, with the same filing accession and period for operating cash flow. Cash including restricted cash is labeled LIQUIDITY_FACT and cannot become spendable-cash runway. Simple runway arithmetic is an estimate, not a company forecast. Restricted cash and investments are not silently relabeled as cash. |
| MARKET | Direct market-provider ticker, aligned and finite price/volume bars, session freshness, and disagreement with collected price. Nasdaq short shares and days to cover are checked separately against ticker and settlement date; shares are not relabeled as percent of float. Provider-reported near-money options IV is checked when obtainable; access-denied or missing data and unconfigured broker borrow remain explicit UNAVAILABLE supplemental fields. |
| ISSUER | Direct company-matched SEC issuer exhibit or explicitly mapped official issuer source with company, drug, indication, announcement language, and a release dateline or publication metadata. When no saved exhibit is available, the verifier inspects exhibits from up to eight recent 8-K/6-K filings. Google News RSS remains discovery only. |

Requests retry transient HTTP/network failures once. SEC requests are paced;
three HTTP 403 responses activate a circuit breaker. Shared URLs are cached
within a verification job, including their actual fetch timestamps.

## Completion and reconciliation

A source run can earn `COMPLETE` for its declared ledger scope when every
required finding is VERIFIED or evidence-backed NOT_APPLICABLE and all event rechecks belong to that execution. Supplemental market fields use an explicit separate policy: their absence produces COMPLETE WITH WARNINGS for core price/volume checks, while their actual missing values remain unavailable to trading gates.
Otherwise it stays `PARTIAL`; a failed collector/verifier is `FAILED`.

The combined audit verifies the workflow run, attempt and commit, scope hash,
ledger hash, fetch times, identities, required claims, and counts. A bare
`COMPLETE` label, old manifest, missing ledger, or inconsistent counts cannot
pass. It recomputes verification totals from accepted ledgers and reports missing
or rejected manifests explicitly.

`full_coverage_verified` remains false for these extended source jobs. Clinical
evidence, exact second-financing sequence, complete trading inputs, and dashboard
ingestion have separate requirements. This change supplies verification and a
concrete gap queue; it does not fill unavailable data or promote trade eligibility.

## Validation

Offline tests exercise primary identity mismatches, dates, conflicts, empty or
malformed responses, SEC blocking, cash/flow period alignment, stale market data,
direct issuer-exhibit discovery, ledger tampering, stale runs, and email reporting.

Run the focused suites:

```bash
python -m unittest discover -s tests -p 'test_source_verification.py' -v
python -m unittest discover -s tests -p 'test_nightly_missing_sources.py' -v
python -m unittest discover -s tests -p 'test_scan_email_notifications.py' -v
python -m unittest discover -s tests -p 'test_sec_recheck_fail_closed.py' -v
```


## Publishing and repair validation

The reconciled five-source summary, full ledger, and required review queue are published to `data/pdufa_source_report.json`, `data/pdufa_source_verification.csv`, and `data/pdufa_source_review_queue.csv`. SCANS shows scan execution separately from required-evidence verification, source counts, and unavailable supplemental data. A fresh hash/scope/run audit is required before publishing. This publication does not promote trading gates or manufacture missing FDA/financing/borrow evidence.

The extended-source workflow also runs after changes to its collectors or issuer source mapping, so a collector repair receives a fresh live check and the existing START/END notifications. Checkouts are pinned to the workflow commit. `tests/test_scan_completion_repairs.py` covers the observed legacy SEC, transition-report, cash-period, issuer, funding handoff, and supplemental-data failures.
