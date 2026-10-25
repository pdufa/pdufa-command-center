# HOP original FDA source dual-review packet preparation (research only)

**Purpose:** Turn an already-generated, fully unadjudicated PDF page-review
worksheet into two separately fillable local review packets. Two packets
do **not** constitute two independent reviews. No evidence is adjudicated,
no PDF content is fetched or independently checked by this operation.

## Prerequisite

Use the original `fda_shared_pdf_independent_review_worksheet.csv` from the
source-audit artifact created by
`new-platform/backend/scripts/collect_hop_fda_action_review.py`. The committed
October 25 audit **index** reports 154 published-letter references across
61 shared PDFs, with no independently verified FDA outcome labels. Those are
*source references*, not 154 independently verified application decisions.
An audit summary index alone is not a substitute for the complete CSV.

## Prepare separate blank packets

Run from the repository root using an existing, locally inspected worksheet:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/create_hop_dual_review_packets.py \
  /path/to/fda_shared_pdf_independent_review_worksheet.csv \
  --output-dir /path/to/private/local/review_packets
```

This produces:
- `first_independent_review_blank.csv`
- `second_independent_review_blank.csv`
- `dual_review_packet_audit.json`

Both CSVs contain identical original source-reference and provisional page
fields; each has **its own blank reviewer fields**. They intentionally do
not show the other reviewer's notes. Assign to two separately authenticated,
qualified reviewers outside this script. Preserve original source hashes,
PDF links, review priority and provenance. The raw worksheet and its audit
index should remain immutable and access-controlled.

The packet fields request each reviewer to record their identity, observed
original PDF digest, letter page boundaries, application identifiers, original
action date, document action type, review cycle and source-specific notes.
Provisional extraction suggestions are not verified page ranges.

The script refuses previously reviewed/promoted worksheets, altered column
sets, duplicate source IDs, non-FDA PDF origins, malformed page links or
spreadsheet-formula-like source cells. It stops without exporting successful
reviewer packets if the input fails validation. It does not connect to clinical
accounts, inspect private notes or contact reviewers.

## What is still missing

After **two separate, real** source reviews, an identity-verified, signed
adjudicator must independently reconcile original document page boundaries,
action date, action type, indication, application and review-cycle identity,
including special rescission/corrected action cases. Conflicts must remain
unresolved until documented. A publication-selected FDA letter archive also
cannot supply a complete approval/nonapproval decision denominator; that
population must be separately reconstructed and verified. Predecision features
require dated public provenance and time-forward model calibration.

The audit intentionally always reports:
`independent_review_pairs_completed = 0`,
`fda_review_cycle_outcomes_verified = 0`,
`model_eligible_records = 0`, and `prediction_probability = null`.

**No production merge, clinical rating, approval probability, scan, trade,
new paid service or import is authorized by these packets.**


## Later: compare submitted reviewer claims (still not an adjudication)

Once both original blank packet copies have been returned by separate people,
use the **unchanged original worksheet** as the reference. Keep completed
submissions and reviewer notes private; do not commit them to GitHub.

From repository root:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/reconcile_hop_fda_review_packets.py \
  /path/to/original_worksheet.csv \
  /path/to/first_completed_or_blank.csv \
  /path/to/second_completed_or_blank.csv \
  --as-of 2026-10-25
```

The tool refuses altered original-source columns, unknown or duplicated source
identities, missing rows, swapped packet roles, unsupported document hashes,
invalid date/page/application formats, and matching reviewer *tokens*. It
compares only the observed source digest, letter pages, application IDs,
action date, document type and claimed review cycle. It reports:

- Blank or incomplete review claims that require follow-up.
- Matching claims that still need authenticated original-source verification.
- Disagreements by FDA source-record SHA256 and disputed *field names*, without
  printing reviewer identities or textual evidence notes.

The tool intentionally exits nonzero and reports `REVIEW_REQUIRED` even if
every claimed answer agrees. Textual reviewer IDs do **not** prove separate
reviewer identities; matching claims do **not** prove correct source content or
regulatory decisions. An independent adjudicator and separate complete
approval/nonapproval decision denominator remain mandatory before FDA outcome
modeling. Do not feed this diagnostic report into prediction or scoring.
