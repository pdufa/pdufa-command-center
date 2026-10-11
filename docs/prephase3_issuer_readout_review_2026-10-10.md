# PRE PHASE 3 — exact-trial readout exclusions

Reviewed October 10, 2026 Pacific. These are publication checks, not clinical
success ratings, FDA predictions or trading entry attestations.

| Ticker / exact trial | Corporate publication | Action |
| --- | --- | --- |
| ABVX / NCT05535946 | June 1, 2026 | Exclude ABTECT maintenance from pre-readout scoring. |
| ACAD / NCT06173531 | September 24, 2025 | Exclude COMPASS PWS from pre-readout scoring. |

Abivax's [primary release](https://abivax.gcs-web.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial)
reports ABTECT maintenance outcomes and explicitly lists NCT05535946 among
the program's three pivotal trials. The [exact registry](https://clinicaltrials.gov/study/NCT05535946)
and its API identify **ABTECT - Maintenance / ABX464-107**, ABX464 with synonym
obefazimod, ulcerative colitis, and Week-44 remission. This identifies the
maintenance study specifically, rather than assigning its disclosure date to
the other induction trials or other ABVX programs. Continued registry activity
reflects follow-up and does not undo the published readout.

Acadia's [primary release](https://acadia.com/en-us/media/news-releases/acadia-pharmaceuticals-announces-phase-3-compass-pws-trial)
reports COMPASS PWS results, a missed primary endpoint and discontinued
development. The [exact registry](https://clinicaltrials.gov/study/NCT06173531)
and its API identify ACP-101-302, the same sponsor, carbetocin nasal spray
3.2 mg three times daily, PWS population, placebo and Week-12 HQ-CT primary
endpoint. The issuer release does not print the NCT: this is a documented
study-design identity review, not an automated ticker-only match. Other ACAD
studies keep their own status.

The existing announcement ledger retains both rows as
`ISSUER_TOPLINE_RELEASE` / `ISSUER_TOPLINE_EXACT_TRIAL_REVIEW`. Their dates
are corporate publication dates, never registry-posting dates. Both original
registry snapshots were checked through the public ClinicalTrials.gov v2 API
during this review. The original pipeline snapshots remain intact.

Exact ticker, NCT, drug and indication, primary issuer host, source link,
review status and observation dates must match before a disclosure blocks a
clinical pre-readout score. In the live research table, the trials remain
visible with announcement date/source; they leave the next-scoring worklist.
Issuer rows are preserved by subsequent registry ingestion and excluded from
the registry-only primary-p collector. An announcement cannot create a
positive clinical score, FDA probability or ENTRY READY status.
