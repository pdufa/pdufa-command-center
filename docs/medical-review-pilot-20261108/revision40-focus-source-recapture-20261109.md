# MAIN Revision 40 — source-specific recovery for 29 FOCUS trials / 23 provisional FDA applications

**Date:** 2026-11-09. **Issue:** #979 (priority-1 evidence validation), #980 (parallel historical replays), draft #965 (Stage 4 scientific installation). **Scope:** isolated development branch; read-only source audit, no scientific grades, no independent reviewer credentials, no database writes and no production deployment.

## Evidence collection design

The canonical 29 exact-NCT identities and 23 provisional application groups are read from the existing backend FOCUS source snapshots. Their file identity is pinned by Git object SHA in CI. The new \`refresh_focus_public_sources_r40.py\` collects two independent categories of current public source receipts:

1. **29 official trial registry records** through the allowlisted ClinicalTrials.gov API v2 exact-NCT route. Each received JSON is checked against the exact NCT ID, and results module presence, registered phase, status, updated date and response SHA-256 are recorded as *source-level observations only*. Study results presence does NOT establish scientific efficacy or FDA acceptability.
2. **23 application source pointers** from the existing provisional 23-cycle crosswalk. Identical source URLs are fetched once and linked back to every relevant application; HTTPS allowlisted redirect host protections, bounded body size, deadlines, HTTP-status/error reporting, MIME checking, fetch time and SHA-256 fingerprinting apply. An HTTP 403, broken page, inaccessible SEC issuer source or redirect does **NOT** mean negative efficacy, a CRL, or lack of an actual filing.

A successful retrieval proves only that source bytes were available now; it does not independently establish historical **first-publication time**, source version as originally filed, FDA reviewer signoff, current agency application-cycle acceptance, CMC adequacy, label, or the treatment's benefits and harms. Any unverified or blocked source must keep the prior noncalibrated research lean separate from the actual FDA prediction.

A fail-closed research receipt reports by-cycle source access, registry linkage, counts and exact remaining limitations. No sponsor page body is republished or archived; the GitHub artifact retains *only hashes and metadata*, expires after up to 90 days, and must not be mistaken for a regulated evidence vault or permanent backup.

## Acceptance

- 29/29 exact trial IDs accounted for, 23/23 application groups accounted for; Sarepta two separately reviewed supplements share one NCT, and obstructive-vs-nonobstructive HCM remain distinct.
- All 29 official registry lookups attempted. All distinct allowlisted issuer/regulatory source links attempted and classified as FETCHED or reason-specific UNAVAILABLE.
- Each successful response fingerprinted, source phase fields parsed only after exact NCT identity check, no unchecked redirect to unsafe/unlisted domains.
- 0 independent medical reviews, 0 independently verified source-as-published evidence versions, 0 historical backtests, 0 calibrated FDA forecasts, no numeric probabilities, no reviewer/scoring writes or database/production deployment.
- Actual retrieved/blocked source counts and links must be reported from the *successful real CI run*. Synthetic test-only pass is not an externally fetched-source result.

## Next scientific gates

Compare the source retrieval results against each of the 23 application’s pivotal efficacy, full statistical analysis plan, population flow, safety and published FDA/issuer regulatory documents. Manually authenticate originally published versions and source timing; independently adjudicate pivotal effect statistics, counterevidence, CMC and regulatory-cycle identities; preserve verified provenance before adjusting any clinical/approval or delay assessment. The historical FDA cohort work (#980) continues separately, with zero currently independently verified real backtests.

The 29/23 clinical research-leans of Rev39 must be preserved as versioned historical information. Any future stronger claim requires a separately dated revised assessment and explicit audit trail, not silent mutation.
