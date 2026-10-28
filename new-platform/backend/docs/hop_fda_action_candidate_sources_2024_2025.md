# FDA FY2024–2025 application candidate reconstruction — nontraining research

**Purpose:** Build a reproducible *candidate review queue* covering source-reported
FDA NDA/BLA actions during **fiscal action years** FY2024 and FY2025. This
is a prerequisite for reviewing complete FDA application cohorts, but is
**not** a representative filing cohort and is **not** approval probability.

The source inputs are two actual FDA-export artifacts collected October
25, 2026 and pinned by the SHA-256 of the extracted source JSON:

| FDA source | Exported | Records | Archived source JSON SHA-256 |
| --- | --- | ---: | --- |
| Drugs@FDA approved-product registry | 2026-10-23 | 29,416 | `adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2` |
| openFDA selectively published Complete Response Letters | 2026-10-21 | 458 | `d3d284e1ec0aa62b6dfb7523bd7bbfc7324c3b218a412fd6ee357a35f5c39898` |

Existing original capture artifacts:

- [Drugs@FDA approved-only snapshot](https://github.com/pdufa/pdufa-command-center/actions/runs/40224730350/artifacts/12611090768)
- [Published CRL snapshot](https://github.com/pdufa/pdufa-command-center/actions/runs/40224038609/artifacts/12610736354)

These earlier artifacts expire under GitHub retention settings. Their original
source content was **not** committed to git, and the current validation
script refuses any future source bytes with different SHA-256, including
legitimate future FDA updates; such updates require a new versioned
provenance review.

## What the audit does

- Enumerates source-reported **ORIG** submission AP approvals and TA tentative
  approvals in the approved-product registry, excluding ANDAs and supplement
  submissions.
- Enumerates *selectively published* CRL records while preserving the
  difference among a parent-only NDA/BLA ID, an explicit Original number,
  an S-number supplement, a legacy/unparseable ID, and multi-ID sources.
- Preserves the source application identifier, original/supplement qualifier,
  action-year date, source record SHA and exact source class for each
  candidate, without inferring a review-cycle ordinal.
- Deduplicates duplicate original action claims, tallies distinct parent IDs
  and shows same-fiscal-action-year overlap between the two source archives.
- Separately displays official **filing-year original application totals**
  (FY2024 **129** after an FDA report revision; FY2025 **157**) as a
  cross-reference. It **does not subtract, divide or compare** these
  aggregates to action-year counts: applications may be filed in one year,
  reviewed and resubmitted in later years, and approval-source records omit
  never-approved or unresolved applications.
- Rejects input metadata that claims source completion, independent
  adjudication, early label publication, or approved model status.
- Keeps true population coverage, approval fraction, independent
  FDA historical test count and FDA probability **null / unavailable**.

The 2024 and 2025 fiscal **action** periods run from October 1 of the
preceding calendar year through September 30 of the named fiscal year.
Source status dates and source-publication dates are only *as reported in
the downloaded 2026 exports*; they are not independently verified FDA
action-letter dates or when these decisions became public.

## Developer entry points

`new-platform/backend/app/hop_fda_action_candidate_universe.py` is the
pure deterministic candidate-audit function.

`new-platform/backend/scripts/audit_hop_fda_action_candidate_sources.py`
accepts the downloaded GitHub source ZIP artifacts, verifies the exact
pinned JSON-source hashes, reconstructs candidates and writes two
**read-only research artifacts** in a caller-provided empty directory:
a JSON candidate queue and a detailed numerical audit. It never writes
the production database, scanner or trading systems.

The opt-in research workflow
`.github/workflows/hop-fda-action-candidate-replay.yml` uses short-lived,
read-only GitHub Actions permission to replay the actual retained original
source artifacts, verifies source hashes and preserves the resulting
research queue as a **14-day artifact**. If old artifacts expire, the
workflow fails instead of silently substituting another source.

## Interpretation and critical next step

The resulting candidate queue is **not a cohort**. It *cannot* enumerate
all original NDA/BLA submissions in a filing year, because Drugs@FDA
contains an approval-centric application inventory and the public CRL
database is selection-biased. Supplements, tentative approvals, rescinded
letters and legacy identifiers also require different treatment.

Before modeling, construct an **independent exact original NDA/BLA filing
roster**, sourced from comprehensive FDA application records or an
authorized FDA data request; track each application through all review
cycles including withdrawn, delayed and pending cases; independently
adjudicate exact action letters, PDUFA revisions, and first public
disclosures; then reconstruct genuinely predecision scientific evidence.

The script and the UI must never show a source-derived approval/nonapproval
fraction as actual future FDA prediction probability.

**Prediction status: INSUFFICIENT EVIDENCE. Model-eligible cases: 0.
Independent real historical backtests: 0.**

No FS/FA preset changes, production scanner activation, Google Sheets
writes, database mutations or broker operations were authorized.
