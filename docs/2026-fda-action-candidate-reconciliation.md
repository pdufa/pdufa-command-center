# November 19 FDA source reconciliation

This audit covers FDA action dates from January 1 through November 18, 2026,
inclusive. The requested 196 eligible PDUFA review cycles remain unverified.
The scope uses actual action dates, which allows a 2026 action whose published
goal date fell in 2027. Goal dates, FDA action dates and later announcement
dates are recorded separately.

| Snapshot | Distinct records | Scope |
|---|---:|---|
| Drugs@FDA originals, NDA | 90 | Full approval records |
| Drugs@FDA originals, BLA | 31 | Full approval records |
| Drugs@FDA efficacy supplements, NDA | 117 | Full approval records |
| Drugs@FDA efficacy supplements, BLA | 84 | Full approval records |
| openFDA 2026 letters | 39 | Published Complete Response Letter PDFs |
| openFDA 2026 letter awaiting publication | 1 | Missing application identifier and published letter |
| Versioned public timing sample v41 | 41 | Discovery records with separate goal-date and action-date source links |
| Public 2026 decisions page | 179 | Publisher's reported snapshot total |

The November 19 Drugs@FDA export contains 29,468 application records. Within
the action window, 1,162 NDA/BLA submission status rows include 322 full
approval records in the four selected classes. The audit deduplicates these on
application number, submission type, submission number and action date. The
number of duplicates under that key was zero. These classes capture actions to
research. Drug brand and sponsor are registry values, which can be broader
than the individual action and may reflect later transfers. Indication, target
date and exact review cycle each need a separate source check. Tentative
approvals, ANDAs, and supplements that FDA categorizes outside EFFICACY are
outside this automated query. Clinical-data labeling supplements and relevant
CBER approvals need separate review. Some CBER records are absent from the
Drugs@FDA bulk file.

The live openFDA query contained 40 records and was dated November 18. The
endpoint overview's stated historical date range lagged the live data. One of
the 40 is marked as under review for release and omits both an application ID
and a structured letter type. The 39 published letters were deduplicated by
filename. Letter IDs and approval submission keys represent different units.
A prior letter and later action can describe different cycles of an original
application. A single product announcement may also cover multiple FDA
submissions. A combined denominator therefore requires an event-level
crosswalk and cannot be computed by adding the source totals.

The 41-row timing snapshot supersedes the branch's 38-row discovery list for
source review. It groups some related applications and omits others. Exact
FDA identifiers take precedence where the discovery site bundles an original
application with a supplement or links a document from a different indication
on the same action date. The three additional rows in v41 are discovery leads,
independent of the count reported on the publisher's decisions page.

## Reproduce the candidate inventory

Compile and run `scripts/audit_2026_fda_action_candidates.py` against the
November 19 Drugs@FDA bulk ZIP, November 18 CRL date-range response, and the v41
timing CSV in a dedicated outcome-quarantine workspace. Pass that same
quarantine directory with `--quarantine`. Stdout contains only aggregate
counts, bounds and hashes. The script creates a private JSON file for
record-level FDA source links and actions. Keep the source files and private
JSON outside the prediction environment and the Git checkout.

| Input | SHA-256 |
|---|---|
| Drugs@FDA ZIP | `cff8c75eb5e347b6075fe45c4e6f1e05e3fcb144810c447c3c87e72bd8c80b47` |
| CRL query JSON | `b4a1081eb3c3d09a45f5fea2cca4ea9cd8e6b65e9680a579bd479eac867aa119` |
| Timing sample v41 CSV | `b196131a21d62e1ac4645c9a888b795f5917601af68a03c97b62dcbbce871b52` |

Outcome-team sources are the [openFDA download manifest](https://api.fda.gov/download.json),
[CRL date-range API query](https://api.fda.gov/transparency/crl.json?search=letter_date%3A%5B2026-01-01+TO+2026-11-18%5D&limit=100),
[CBER original BLA approvals](https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/2026-biological-license-application-approvals),
[CBER noteworthy BLA supplements](https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/2026-biological-license-application-supplement-noteworthy-approvals),
[versioned timing sample](https://www.pdufa.bio/research/fda-decision-timing/fda-decision-timing-2026-v41.csv),
and [publisher decisions page](https://www.pdufa.bio/decisions/2026).

## Review of the timing subset and outstanding records

The timing CSV overlaps 41 of the publisher's 179 distinct decision pages.
The branch's first 38 discovery IDs are preserved and the three additional
records have IDs 039 through 041. The outcome-team crosswalk records a primary
FDA source and a separate primary goal-date source for each. The team manually
cross-checked publisher linkage against FDA letters, agency communications,
the Drugs@FDA submission record and contemporaneous sponsor disclosures.
Several links in the discovery CSV were replaced after that check.

- 40 of 41 timing rows have a source-corroborated application, indication,
  sponsor, goal and FDA action. This count applies only to the timing subset.
  The eligible study denominator still needs reconciliation. The metadata
  handoff is for predecision research and does not establish evaluator
  blindness.
- PDUFA26-TIMING-027 has a documented Class 2 resubmission. The sponsor corrected
  its date in a January 29 update. The corrected June 29 goal is the one
  retained in the crosswalk.
- PDUFA26-TIMING-033 has a program-level goal and more than one application-level
  action. Determine which applications had independent target dates before
  assigning distinct eligible events.
- PDUFA26-ARCHIVE-001 through PDUFA26-ARCHIVE-138 identify the decision pages
  outside the curated timing study. IDs 110 and 114 were reconciled in the
  separate CBER intake below. The remaining 136 need indication, FDA application
  and submission ID, action date and goal-date corroboration. The exact
  source-key crosswalk is held in outcome quarantine.
- The official-source queue has 290 Drugs@FDA candidate keys and 36 published
  letter keys absent from the curated timing crosswalk, plus the one
  under-release letter record. These can overlap the 138 discovery records.
  The outcome-team queue numbers them as PDUFA26-DRUGS-001 through -290,
  PDUFA26-LETTERS-001 through -036 and PDUFA26-SOURCE-001. Match each across
  sources by application, indication, review cycle and action date before
  counting it. The under-release record depends on FDA disclosure.
- The CBER original BLA table had 10 rows through September 17. Four were in
  the timing crosswalk. Three additional therapeutic applications were
  reconciled as PDUFA26-CBER-001 through -003, of which -002 and -003 resolve
  archive IDs 114 and 110. The third is outside the 179-page discovery index.
  Keep the original and amended goal separately for the extension, and the
  voucher action and PDUFA goal separately for the accelerated review. The
  table also had three rows for plasma or assays that need eligibility review.
  The updated CBER product and supplement indexes need separate intake for
  later actions and for clinically relevant supplements.

These batches have 43 source-corroborated records and one program grouping
issue, across 44 distinct records reviewed. The counts still describe a
source-defined subset.
