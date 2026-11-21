# FDA published-letter identity gap triage — 2026-10-25

**Status: quarantined research, not an FDA original decision census.**

The original NDA/BLA submission spine and the published FDA letter archive
have different units, dates and coverage rules. A letter not linked to
an original NDA/BLA submission is **not proof of FDA rejection, permanent
nonapproval, missing clinical evidence, or a review-cycle outcome**.

Prior cross-source snapshot: 458 published FDA letter references, of which
334 match an original NDA/BLA application in the tabular FDA source, 107 have
a single resolvable NDA/BLA identity not in the *original-submission*
inventory, and 17 have ambiguous or unparseable application IDs. Published
letter reference counts can include multiple letters for one application.
None of these counts is the true complete NDA/BLA review-cycle denominator.

## What has been added

`new-platform/backend/app/hop_fda_unmatched_letter_triage.py` creates a
read-only review queue from three inputs at the same pinned data cutoff:

- the **actual** FDA tabular Applications.txt roster;
- the NDA/BLA `ORIG` submission history from the matching Submissions.txt;
- the selectively published official FDA letter archive, pinned by its
  source hash and original collection run.

The source check recalculates the original letter/application crosswalk. It
separates each unlinked reference into three cases: uncertain/ambiguous
published application ID; application present in the FDA tabular roster but
lacking an original submission in this extract; or application absent from
the tabular FDA application roster altogether. All require independent FDA
source verification. The queue prioritizes ambiguous ID resolution before
source completeness investigation. Repeated letters for one application
are counted as letters, **not multiple independent FDA decisions**.

Each private worklist record contains the letter's source-row SHA,
a provisional canonical application ID if unambiguous, its published letter
type, an unresolved reason, and a human-review task. Review-cycle numbers,
FDA action labels, approval probability and any model eligibility remain
blank, null or false.

The isolated
[`HOP original NDA BLA submission-source audit` workflow](https://github.com/pdufa/pdufa-command-center/actions/workflows/hop-drugsfda-original-source-research.yml)
runs synthetic security and regression tests, downloads the official
research sources, and writes a **private runner-only letter review queue**.
Only summary counts and immutable source fingerprints are uploaded as
the public aggregate artifact. The per-letter queue is **not uploaded**
or merged into the production data store. Original source data remains
research-only.

The collected aggregate should reconcile all 458 published references
into matched, nonmatching, ambiguous, and any out-of-scope ANDA letter
identities; a failure stops the workflow before any report is accepted.

## Additional checks still necessary

The original-drug registry may contain some application records without
their corresponding original-submission history. Its coverage of never-approved
applications is incomplete. This triage does not establish whether a
published letter was actually an original NDA/BLA action, a supplement,
a refusal-to-file, a rescinded CRL, or a final negative outcome. These
statuses need primary-source action-letter inspection and application-cycle
reconstruction. Never treat a raw `COMPLETE RESPONSE` string as a model
label without an independently verified document, date, identity, and
review-cycle mapping.

GEM JR and GEM FS/FA original preset relationships remain unchanged;
no live scanner, model training, probabilities, or production deployment
is authorized by this workflow. Until a complete source cohort and
independently verified original FDA decisions exist:

**Independent review-cycle outcomes: 0. Model-eligible records: 0.
Approval rates, probability estimates and prediction accuracy: unavailable.**


## Actual official-source audit result

The pinned official-source workflow
[40254738326](https://github.com/pdufa/pdufa-command-center/actions/runs/40254738326)
succeeded. Its
[aggregate research artifact 12622062153](https://github.com/pdufa/pdufa-command-center/actions/runs/40254738326/artifacts/12622062153)
reconciled **all 458 published FDA letter references**, with **334**
linked to original NDA/BLA applications in the tabular source, **107**
resolvable published letter references whose complete application
identifiers are **absent from the approval-centric tabular application
roster**, and **17** references with ambiguous or unparseable identity.

**None** of the 107 is an application present in the tabular source but
simply missing an `ORIG` submission row; that subcategory has count
**zero** in this exact snapshot. The 107 references belong to **84
distinct candidate application IDs**, of which **20** have repeated
published letter references (maximum **three** references for a
candidate application). The 17 ambiguous letters cannot be assigned a
reliable distinct-application count until a human validates their
identifiers. The complete private review queue contains 124 *letter
references*; this is not 124 FDA regulatory decisions.

Snapshot: `app/research_sources/hop_fda_unmatched_letter_gap_audit_20261025.json`,
with SHA fingerprints of both pinned tabular source files and
the official published-letter export date. Regression tests check its
counts and consistency with the earlier published-letter bridge.

**Interpretation:** Unlike an original NDA/BLA decision cohort, a
published FDA letter collection is selected by release and disclosure;
an NDA/BLA missing from the tabular `Applications` roster might reflect
source scope, data-history limitations, later/never approval, or an
application identity discrepancy. No attempt was made to select the
explanation by assuming any of these outcomes. Independent FDA record
adjudication remains necessary for each specific review cycle.
