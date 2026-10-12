# Nightly source verification

The nightly source workflow now collects evidence, verifies specific claims,
and reconciles the resulting ledgers. Successful execution alone does not prove
that a source claim is correct or that the full trading baseline is complete.

Every ledger finding has one status:

| Status | Meaning |
| --- | --- |
| VERIFIED | The named claim passed the source, identity, date, and data checks applicable to its scope. |
| REVIEW_REQUIRED | Required evidence is missing, ambiguous, stale, or outside the automated check's scope. |
| CONFLICT | A primary/provider value or identity disagrees with the saved claim. |
| TECHNICAL_FAILURE | The worker could not retrieve or inspect the required response. |

Source ledgers include the event and ticker, claim, expected and observed value,
reason in English, source URL, response SHA-256, fetch timestamp, and evidence
excerpt. They are saved with the scan artifacts. The combined audit also saves
`combined_verification.csv` and the full `verification_review_queue.csv`.
The final Gmail summary separates verified, unresolved, conflicting, and
technically failed checks.

## Checks by source

| Source | Implemented checks and scope limits |
| --- | --- |
| FDA | FDA pages or company-matched SEC documents; drug, indication, and explicit claim date. FDA pages also require company identity. A reported PDUFA target cannot become a decision date. A past target with no resolved outcome remains under review. Publication dates cannot substitute for action dates. |
| SEC | Nonempty submissions response with matching CIK and ticker, valid filing identities, and aligned arrays. A filings inventory does not establish insider accumulation. A dated closing clause remains under review until the exact deal and post-Phase-3 second-financing sequence are adjudicated. |
| FINANCIAL | Matching Companyfacts CIK, cash-equivalents USD fact with filing accession and a current period, plus same-period operating cash flow. Simple runway arithmetic is an estimate, not a company forecast. Restricted cash and investments are not silently relabeled as cash. |
| MARKET | Direct market-provider ticker, aligned and finite price/volume bars, session freshness, and disagreement with collected price. Quote verification does not verify short interest, IV, or borrow. Those fields remain explicit gaps. |
| ISSUER | Direct company-matched SEC issuer exhibit with company, drug, indication, announcement language, and a release dateline or publication metadata. When no saved exhibit is available, the verifier inspects exhibits from up to three recent 8-Ks. Google News RSS remains discovery only. |

Requests retry transient HTTP/network failures once. SEC requests are paced;
three HTTP 403 responses activate a circuit breaker. Shared URLs are cached
within a verification job, including their actual fetch timestamps.

## Completion and reconciliation

A source run can earn `COMPLETE` for its declared ledger scope when every
required finding is verified and all event rechecks belong to that execution.
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
