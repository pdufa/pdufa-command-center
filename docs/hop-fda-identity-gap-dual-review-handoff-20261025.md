# Dual independent-review handoff for the 124 FDA letter identity gaps

**Research-only | October 25, 2026 | No verified regulatory decisions**

This handoff extends the existing scientific PDF review infrastructure without
replacing the original dual-review packets for 154 **shared-PDF** source
references. The **separate identity-gap** stream covers 101 research groupings:
84 candidate original NDA/BLA applications with 107 published-letter
references, and 17 letters whose applications are ambiguous. Those 124
references were selected for **source evidence investigation**, not because
their outcomes were approved or rejected.

The existing pinned FDA PDF provenance audit makes previous official PDF
URL + SHA-256 evidence leads available for 123/124 references. The remaining
source letter is an unclassified Chiesi record whose PDF was still "Under
Review for Release"; it has no application number or released PDF in the
source inventory.

## What the handoff generates

The isolated source workflow now writes **two distinct, blank** private JSON
reviewer handoffs of **124 records each**, one `FIRST` and one `SECOND`.
Both have identical source metadata but distinct roles, empty reviewer tokens,
empty observations, and explicit unverified/model-ineligible flags.

Each original letter source row is bound by a SHA-256 lock incorporating the
research grouping, provisional original NDA/BLA application candidate (or
null), published-letter row digest, letter type/date, historical official FDA
document URL and hash where available, and whether that PDF was checked in
the **earlier** source audit. A reviewer can enter a provisional observed
application ID, original/supplement/unknown submission class, original
document page interval, FDA effective action date, document classification,
review cycle (or `UNKNOWN`), and text evidence notes. These remain
**claims** unless independently authenticated and adjudicated.

The source-locked review-claim comparator
`app/hop_fda_identity_gap_dual_review.py` refuses mutated source
identifiers/URLs/digests, forged proof flags, duplicate or missing records,
invalid dates and page ranges, conflicting claimed reviewer identity tokens,
and spreadsheet-formula-like reviewer entries. It separates:

- `SOURCE_DATA_INCONSISTENCY` — missing PDF, ambiguous original ID, or
  a claimed application number contradicting the source candidate.
- `TWO_CLAIMS_DIFFER` — both syntactically complete but disagreeing
  claimed FDA source observations.
- `CLAIMS_INCOMPLETE` — at least one reviewer has not supplied a
  complete claim.
- `MATCHING_TEXT_UNVERIFIED` — matching reported field text, **not**
  authentication of the reviewers, source pages, decision or original FDA
  review cycle.

The comparator exposes only source hashes and disputed field names,
**never the identities or free-text notes of reviewers**. It never reports
a verified original FDA decision, model eligibility, FDA approval rate or
prediction probability.

## Isolated private execution

`scripts/prepare_hop_fda_identity_gap_dual_review.py` reads the **private**
enriched research packet source from the previously completed FDA PDF lead
join, and writes blank role JSONs to
`private_original_tables/blank_first_fda_identity_gap_review.json` and
`private_original_tables/blank_second_fda_identity_gap_review.json`.
A third **aggregate-only** audit records two blank row counts, the number
of referenced letters with no original PDF lead, grouping counts and
immutable unverified clinical/denominator flags.

The workflow uploads **only the aggregate count JSON** in the existing
public_aggregate_only artifact directory. It does not upload the private
reviewer packets, future observations, reviewer identifiers, original FDA
PDF files or link mappings. Generated private runner files are not durable
reviewer storage; a separate, access-controlled process is required for real
review and later authorized adjudication.

**No human reviewer has been assigned, authenticated, or recorded as having
performed this work.** These are blank documents, not completed investigations.
The earlier PDF fingerprints are historic checks and **were not rehashed
in the current workflow**.

Original PDF-page verification, original/submission-versus-supplement
history, complete NDA/BLA review-cycle population including nonapprovals,
reviewer independence and qualified human regulatory adjudication are
unresolved. The existing GEM JR and GEM FS/FA preset mappings, scans and
production system remain unchanged.

**Verified original action cycles = 0; model-eligible records = 0; approval
probabilities and predictive accuracy = unavailable.**
