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


## Actual result: full 29/23 source access, 2026-11-09 16:24:54 UTC

[Final successful audit run #42654460905](https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905) checked a known immutable FOCUS/source-crosswalk snapshot and completed **29 synthetic integrity and historical anti-leakage regression tests**, then executed actual public HTTPS source reads.

| Source retrieval measure | Observed |
| --- | ---: |
| Exact ClinicalTrials.gov registry source JSON retrieved | 29 of 29 |
| Trial registry modules with posted results present | 12 of 29 |
| Trial records registered Phase 3 only | 28 |
| Trial record registered both Phase 2 and Phase 3 | 1 (NCT04871282) |
| Provisional application groups with at least one accessible public primary source pointer | **23 of 23** |
| Canonical issuer/SEC/source URLs (distinct) | 21 |
| Explicit additional official SEC alternative for redirected issuer | 1 |
| All unique attempted source URLs | 22 |
| Source URLs fetched and SHA-256 fingerprinted successfully | **21 of 22** |
| Independently signed scientific reviews / FDA application-cycle decisions | **0** |
| Validated clinical method scores, FDA probabilities, real historical FDA backtests | **0** |

**One remaining original issuer URL access issue, fully traced:** Achieve Life Sciences' company-hosted August 11, 2026 10-Q returned HTTP 301 in the CI collector; the *exact equivalent original filing* is independently discoverable at [SEC accession 0001193125-26-344624, company CIK 949858, 10-Q](https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm) and was fetched via explicit SEC allowlisted fallback. This is evidence accessibility, not validation of the June 2026 manufacturing deficiency's resolution. The untouched source crosswalk still points at the originally recorded issuer URL; both receipt statuses remain separate.

Sarepta's shared full [2026 September 30 10-Q](https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm) is 5,331,458 bytes, larger than the first 5 MB cap; Rev40 now hashes it by streaming with a bounded 50 MB limit. This file supports **two separate** application groups and is not counted as two independent historical outcomes.

Public registry \`resultsSection\` presence is mere source availability; only 12 of 29 studies reported a results module in the exact version retrieved. Non-posting of registry results may coexist with sponsor/academic trial readouts and must **not** be equated to negative pivotal results. Exact source-publication chronology, full original analysis, CMC and independent reviewer verification are not certified by this scan. The combined Phase2/Phase3 status of NCT04871282 needs phase-first review, not forced invalidation.

The final research receipt bytes were independently re-opened and SHA-256 checked: \`0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c\`. [Artifact #13691348436](https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905/artifacts/13691348436) expires 2027-02-07 16:24:36 UTC; it is **not** a permanent vault and holds metadata/hash fingerprints, not source HTML/clinical documents. The display pins the exact run and digest. Future rechecks must generate a new dated receipt and preserve this version rather than overwrite history.

**Next scientific review priorities:** 1) independently inspect original full analyses for the nearest application dates CAPR/SVRA/COGT; 2) reconcile differing Phase 3 SAP, safety/CONSORT and report clocks (especially ACACIA-HCM); 3) recover complete pivotal statistics through issuer/publications for the other 17 NCTs whose registry resultsSection is not currently posted; 4) separately establish FDA cycle/CMC/label identity and signed medical review before numerical forecasting. No current clinical grade or FDA model prediction release is authorized by this source scan.
