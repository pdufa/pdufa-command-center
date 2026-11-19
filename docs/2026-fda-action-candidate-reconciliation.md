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

## Archive and published-letter crosswalk, batch 1

The outcome team captured all 136 remaining publisher pages. Of these, 84
include an FDA-record section, 107 explicitly lack a goal day on record, and
4 report only a month. These are publisher statements checked for triage.
They do not establish an action or original PDUFA date by themselves.

| Disposition | Publisher pages |
|---|---:|
| Independently crosswalked to official FDA action and primary original goal | 6 |
| Alias of an already crosswalked application event | 4 |
| Requires primary goal and application-cycle review | 102 |
| Publisher provides no source | 17 |
| Publisher infers occurrence from market movement | 3 |
| Requires day-level goal source | 4 |

The six independently sourced rows are PDUFA26-ARCHIVE-008, -013, -040,
-052, -077 and -078. Four aliases map to existing timing crosswalk rows.
These are PDUFA26-ARCHIVE-080, -127, -137 and -138. The last had a link to a
same-day but unrelated supplement and was matched on the intended program
and action. The dataset retains one event for each verified review cycle.
Three further application actions, PDUFA26-ADDITIONAL-001 through -003, came
from official records outside this publisher index.

The overall source-corroborated subset now contains 52 review-cycle
records across 53 reviewed. Two of the nine new records had extensions,
for which the ledger stores both the original and revised goal dates.
A further publication date in the FDA letter index was a corrected letter
for a December 2025 action. That letter record is excluded from the 2026
action cohort and retains the official effective date in the restricted
ledger. The official queues now contain 289 requested approval-record checks
and 27 published letter checks, plus the single letter awaiting release.
Those counts overlap the 126 publisher records still awaiting verification.

The restricted workspace retains the 136 source HTML snapshots, their
per-page SHA-256 hashes, the authoritative source URLs, and all exact status
changes. The outcome-free handoff identifies the nine additional events.
No claims about a complete eligible census, blind scoring or evaluator
exposure follow from this source subset.

## Application-level resolution of PDUFA26-TIMING-033

The sponsor assigned one August 27, 2026 priority-review goal to its single-tablet combination NDA. The FDA parent application record identifies that regimen as NDA221104, original submission 1. Keep one source-corroborated timing record for that submission. The separate NDA221443 starter-pack record has a different filing identity, and its FDA correction retained the original action date. The available program goal source names the combination NDA. The starter-pack original and supplement remain in the separate-source queue pending their own goal-date corroboration, and are excluded from this timing row. The FDA action documents are retained in the outcome workspace. [Sponsor priority-review announcement](https://www.gilead.com/news/news-details/2026/u-s--fda-grants-priority-review-of-new-drug-application-for-gileads-once-daily-hiv-treatment-of-bictegravir-plus-lenacapavir)

The reviewed subset now has 53 source-corroborated timing and FDA action records. The study-wide eligible denominator remains open.

## Published-letter crosswalk, batch 2

The outcome team corroborated seven additional review cycles with the
official FDA letters and exact dates from contemporaneous original sponsor
goal sources. The rows are PDUFA26-LETTERS-001, -004, -012, -021, -024,
-029 and -032. Three link to publisher records PDUFA26-ARCHIVE-018, -117
and -118. All seven use the FDA action date. The later publisher or sponsor
announcement date was retained separately where present in the publisher
snapshot.

- PDUFA26-LETTERS-004 has a 2025 original goal, a 2026 revised goal and an
  independently documented 2026 action. The action-date window therefore
  includes the event.
- PDUFA26-LETTERS-012 and PDUFA26-TIMING-038 are distinct cycles of the same
  BLA. Their FDA letters identify separate resubmissions and original target
  dates for those cycles.
- PDUFA26-LETTERS-028 is a separate action on a paired application for
  PDUFA26-LETTERS-029. The sponsor explicitly documents an exact goal day for
  the NDA and confirms concurrent submission of the BLA. The exact target
  day is still unverified for the BLA, so the ledger keeps that action
  provisional.
- The TIMING-020 cycle label now specifies a Class 2 resubmission, consistent
  with the contemporaneous sponsor filing.

This batch adds seven cases to the prior source-corroborated set. The
publisher queue now has 123 open rows. The official published-letter queue
has 20 open rows, including the paired application. The official approval
candidate queue still has 289 open rows and the under-release letter remains
open. These queues overlap and cannot be summed into a study census.

The exact crosswalk, primary source links and action records remain in the
restricted workspace. The separate metadata handoff carries only
source-corroborated review-cycle identities and dates, and omits actual
outcome fields and links.

## CBER supplement screening

The November 19 capture of FDA's original BLA table still contains ten rows through September 17. The separately published noteworthy supplement table contains 14 rows through July 27. Its publication scope leaves later reviews and unlisted supplements outstanding. Two previously unmatched efficacy supplements have exact FDA application, action and goal-date documentation.

| Event | Application and cycle | Original goal | Scope |
| --- | --- | --- | --- |
| PDUFA26-CBER-004 | BLA125814 SUPPL:428 | June 18, 2026 | CAPVAXIVE pediatric population at increased pneumococcal disease risk |
| PDUFA26-CBER-005 | BLA125251 SUPPL:454 | July 3, 2026 | WILATE prophylaxis in children younger than six years with von Willebrand disease |

FDA action and review documents are retained separately from the metadata handoff. Later FDA reviews were used to verify the historical decision record and day-level goal. They are unavailable to the predecision assessor. CASGEVY BLA125787 SUPPL:457 and AREXVY BLA125775 SUPPL:414 have identifiable indication changes in this source but still need independent exact goal dates. The remaining noteworthy rows require cycle and scope screening. [FDA original BLA index](https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/2026-biological-license-application-approvals) · [FDA noteworthy supplement index](https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/2026-biological-license-application-supplement-noteworthy-approvals)

## Original-application review records, batch 3

The original-application batch adds 27 source-corroborated FDA review cycles.
For 26, the outcome team examined FDA review documents linked from the
original-application Drug@FDA records. The 27th has an exact target date in
the sponsor's dated announcement. Some records also had a contemporaneous
sponsor filing that resolved an earlier goal or a different review cycle.
The team compared the application, submission, sponsor, indication, and
action date against the official action record. Review documents published
after an action were used only to verify historical case identity and
target dates. They do not supply predecision features.

Two FDA candidate records, PDUFA26-DRUGS-214 and PDUFA26-DRUGS-232, have
conflicting day-level dates among the source review records. Their original
target dates remain open. The official Drugs@FDA queue now has 262 open
records, including those two conflicts. The 20 open published letters and
one under-release letter remain. This was an FDA-record batch, so the 123 open
publisher rows still await a page-level crosswalk and may overlap this batch.

The restricted workspace contains the exact original-application crosswalk,
FDA and target-date source URLs, and the disposition inventory. A metadata
handoff lists these 27 cases without outcomes or source URLs. These records
are a source-defined subset, and the 196-case denominator remains unverified.
