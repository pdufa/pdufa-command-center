# Official FDA/ClinicalTrials.gov access recovery — research-only

Status: **SOURCE ACCESS NOT VERIFIED IN CODEX; NOT READY / ABSTAIN**.

## Problem
Codex reported HTTP 403 responses from FDA and ClinicalTrials.gov and
restricted GitHub API access. An HTTP 403 is a failed retrieval, not proof
that a clinical fact or regulatory outcome does not exist. Do not bypass
access controls, rotate proxy identities, or disguise automated requests.

## Supported official retrieval paths (test separately)
1. FDA Drugs@FDA bulk TSV tables:
   https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files
   - Official application/submission/action and document metadata.
   - Preserve application number, submission type/number, action date,
     document URL, dataset version and download timestamp.
   - Dataset is approval-oriented: absence does not prove CRL.
2. openFDA Drugs@FDA bulk JSON and published download index:
   https://open.fda.gov/data/downloads/
   - Prefer official published bulk downloads when API or website requests
     fail; retain origin, SHA-256, and download timestamps.
   - Cross-check normalized keys against FDA TSV; do not count duplicate
     exports as independent sources.
3. FDA published CRL transparency resource:
   https://open.fda.gov/apis/transparency/completeresponseletters/
   - Check coverage and redaction; do not assume comprehensive CRL history.
   - Require exact NDA/BLA, submission cycle, decision date and letter.
4. ClinicalTrials.gov official data API:
   https://clinicaltrials.gov/data-api
   - Registry updates may occur after prediction cutoff. Require
     versioned historical records or dated archival proof for backtests.

## Implementation acceptance criteria
- Add source adapters behind a single interface with explicit provenance,
  rate limits, bounded retries, timeouts and source-specific error codes.
- On 403/429/network failures: mark SOURCE_UNAVAILABLE, never mark MISSING
  EVIDENCE or invent a negative outcome.
- Store original response/document bytes, SHA-256, fetched_at, source
  publication date (when proven), and dataset snapshot identifier.
- Import bulk datasets only after checksum, schema, and row-count checks.
- Link by NDA/BLA application and exact review cycle, not drug name alone.
- Keep approval, CRL, and extension labels separate; do not infer CRL or
  extension from elapsed PDUFA target dates.
- Never substitute a current updated record for a pre-cutoff snapshot.
- Test 403/429, corrupted ZIP, schema drift, missing historical timestamps,
  duplicate cases, ambiguous cycle identity and cutoff leakage.
- Log which endpoints succeed in the actual Codex environment. This plan
  does not claim any endpoint is reachable there.

## External blockers
If the execution environment cannot reach official sources, an authorized
operator may supply legitimately downloaded original FDA/NIH archives for
offline, checksum-verified import. Do not claim verification before source
documents and review-cycle evidence have been independently adjudicated.

No production merge, scan changes, or trading enablement is authorized.
