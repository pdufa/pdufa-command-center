# Step 4 — SEC Financial Analysis

Step 4 is **separate** from clinical scorekeeping, PRE PHASE 3, the PDUFA Pipeline and FDA Prediction Engine.

## Open it

In the Streamlit app sidebar select **SEC Financial Analysis**. The page lists registered stock tickers, sources, cash/runway estimates, quarterly or derived operating cash flow, debt/shares data and SEC filing links. It does not initiate a SEC request until the user presses the fetch button.

## Required one-time SEC access configuration

The SEC requests a descriptive User-Agent with an active contact address. Set a Streamlit secret called **SEC_USER_AGENT** (or an environment variable with that name):

```toml
SEC_USER_AGENT = "Your Research App research-contact@your-real-domain.com"
```

Use your real contact email. Do not commit personal contact addresses or API secrets to GitHub. SEC network access may return 403 or 429 even with a configured identity; the client returns an error and never fabricates financial data.

**Command-line, one company:**

```bash
export SEC_USER_AGENT="Your Research App research-contact@your-real-domain.com"
python sec_step4.py --ticker ABCD
```

The ticker must exist with a unique CIK in `data/company_registry.csv`.

**Explicit capped batch (maximum 25 companies):**

```bash
python sec_step4.py --all --limit 5
```

This is a manual scan, **not** a complete backfill. No API request is made without explicit scan action, a valid SEC contact identity and unambiguous registry mapping.

## Financial calculations

Cash is from the latest available SEC US-GAAP reported **cash and cash equivalents** as of the analysis date. If only cash-plus-**restricted cash** is disclosed, the engine does not calculate spendable runway. It reports short-term investments separately but never adds them to runway unless separately verified to be available.

Monthly operating burn uses the **quarter's negative operating cash flow**, divided by three. For second and third quarters SEC cash flow statements commonly report year-to-date cash flow: the engine takes the difference between the current and prior compatible year-to-date statement first. If the prior period is missing it **does not** treat a six- or nine-month cumulative figure as quarterly. An annual operating cash flow average may be shown and is labeled as such. Positive operating cash flow gives no numeric runway (rather than an invented infinite one).

Cash runway = reported cash / estimated monthly net operating burn. A numeric runway is withheld if cash or cash flow evidence is too stale (older than 150 days), the periods are materially mismatched, or there is no confirmed net operating cash burn.

A **risk band** highlights short runway. The composite financial score stays **NOT SCORED** until documented, defensible scoring inputs and validation are available.

SEC company revenue is **not** assumed to be product revenue. Missing current/noncurrent debt is not assumed to be zero; the financing maturity schedule, ATM utilization, dilution from financing and *actual offering close* require filing-document evidence, not just structured SEC facts.

## Financing evidence

The SEC `submissions` index returns filing metadata for current reports, registration statements and prospectus filings. These become a **manual review queue** with source URLs. A registered shelf (`S-3`) is not an executed offering. A prospectus supplement (`424B5`) is not sufficient proof of financing closed. An `8-K` alone may cover almost anything. **No financing will be marked completed simply because a form exists.**

The Phase 3 post-readout second-financing ledger remains unchanged and must undergo its own event-specific review.

## Evidence, auditing and storage

- Read endpoints: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` and `https://data.sec.gov/submissions/CIK##########.json`
- Each snapshot stores the SEC CIK, accession, filing date, period end and concept tags.
- `data/sec_step4_snapshots.sqlite3` has append-only, content-hashed revision records; identical rescans are idempotent.
- Download the complete audit history JSON from the Streamlit page.
- **Streamlit Community Cloud local filesystem can be reset** on reboot/redeploy. Export the audit history or deploy with a persistent external database for durable storage.
- No production SEC scan or validation of all tickers has been run by this implementation.

## Tests

```bash
python -m unittest tests.test_sec_step4 -v
```

Fixtures are synthetic; they exercise CIK mismatches, cross-year/fiscal cash flow period selection, as-of date filters, restricted cash, financing false positives, SEC 403s and append-only revisions without contacting the SEC.
