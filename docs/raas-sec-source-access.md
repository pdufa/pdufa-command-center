# SEC share-evidence access for RAAS

The historical share-data workflow downloads SEC public DEI cover-share research as a **lead**, never an automatically qualified historical market capitalization.

## Production outcome and fix

The 2026-11-03 production run reported `SEC_HTTP_403` for all 64 selected issuer requests. The 403 is an *access blocker*, not proof that an issuer had no disclosed shares. The updated collector stops following the first 403/429 rather than issuing requests for all issuers after an access restriction.

SEC guidance requires that programmatic requests declare the organization and a contact email in the HTTP User-Agent. To comply, set one encrypted GitHub Actions repository secret named **`SEC_USER_AGENT`** (example format: `Organization Name contact@example.org`). The value must contain a legitimate operator-controlled contact address; never insert another person's address or an unmonitored placeholder. The workflow reads this secret but does not print its value.

SEC documentation:
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- https://www.sec.gov/about/developer-resources
- https://www.sec.gov/about/webmaster-frequently-asked-questions

A declared identity is necessary but may not restore access from GitHub-hosted runners. If the official endpoint still returns 403, move SEC research to an authorized source environment or use the SEC-provided bulk XBRL dataset in an environment permitted to access it, not a proxy to evade access controls. Stop and contact SEC webmaster for additional assistance. Do not scrape around the block.

## Artifacts and status

Use `RAAS historical SEC share evidence audit` under GitHub Actions. The JSON artifact records:
- `secAccessStatus`, `secAccessBlockReason`
- `SEC_SOURCE_UNAVAILABLE` for the first blocked issuer
- `NOT_REQUESTED_SEC_ACCESS_BLOCKED` for remaining, deliberately deferred issuers
- date-checked raw share facts when available

**Never** multiply an adjusted Alpaca closing price by unadjusted SEC shares. Complete dated raw-price, share-class, ADR-ratio, stock-split, original public target-date and issuer-rights verification independently before an entry-day $300 million–$10 billion qualification. No RAAS approval grade or PDUFA success probability should be derived from these source leads alone.
