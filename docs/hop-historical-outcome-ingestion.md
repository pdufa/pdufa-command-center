# HOP Historical FDA Outcomes — Data Contract

This is a **curated input format**, not a populated historical database.
Do not create invented outcomes or infer FDA decisions from trial phases.

The JSON array now uses the same 15 metadata fields as the quarantined
[CSV intake](hop-historical-fda-csv-intake.md):

- `case_id`: local immutable identifier; this alone is not FDA event identity.
- `application_id`, `review_cycle`: exact NDA/BLA/ANDA and positive review cycle.
- `drug_name`, `sponsor`, `indication`, `therapeutic_area`, `modality`.
- `phase`: integer 1–4; intake does not activate formal deep investigation.
- `decision_date`: YYYY-MM-DD official action date requiring source review.
- `outcome`: `APPROVED`, `COMPLETE_RESPONSE`, `WITHDRAWN` or `OTHER_NONAPPROVAL`.
  Only the first two can be considered for binary descriptive comparisons.
- `public_features_as_of`: YYYY-MM-DD clinical snapshot strictly before action.
- `evidence_as_of`: YYYY-MM-DD outcome-evidence availability on/after action.
- `source_url`, `source_title`: primary FDA HTTPS source locator and title.

JSON uses integers for phase/cycle; CSV uses their textual equivalents. All
other fields are nonempty text. Both paths share the date, identity and official
source URL validator. Outcome evidence cannot predate the action. Neither path
fills in a missing public-availability date from a printed/retrieval date.

`parse_history(text, as_of=date(...))` and `load_history(path, as_of=date(...))`
support a fixed research snapshot; omitted `as_of` uses today's date. The entire
JSON import fails on an invalid row, repeated JSON object key, duplicate local
case ID or duplicate canonical application/cycle. Returned cases retain drug,
sponsor, source title and both evidence clocks, with independent adjudication
always false. No automatic conversion into training observations is provided.

## Deliberate legacy migration gate

Old nine-field JSON records had one ambiguous `evidence_as_of` clock and no exact
application/cycle or separate feature cutoff. Their parser required this clock
before action while the comparator required outcome evidence on/after action.
These inventories are now explicitly rejected. Do not rename or copy that date
into a new field, infer a review cycle, or overwrite an archived input. A source
reviewer must separately establish the action, feature snapshot and outcome
publication chronology, then prepare a new complete input while retaining its
original. Empty inventories remain valid empty inventories.

Independently adjudicated comparator inputs also require exact application/cycle
identity. Repeated claims to the same canonical cycle are all excluded before
other metadata quality filters; another local case ID cannot increase support.
Cases missing the new identity fields remain excluded.

A source URL passing format checks is **not** proof of a verified decision.
Every imported case still needs independent source-content verification and
time-correct trial feature extraction. Approval probability must remain null
until leakage-controlled backtesting, calibration, and outcome adjudication.

Never treat example fixtures as actual FDA outcomes.

PDUFA target versions and their contemporaneous source provenance, explicit
delay/refuse-to-file/unresolved event histories, representative cohort membership
proof and verified publication clocks remain unfinished dataset work. Withdrawals
and generic nonapproval observations are retained for research, never silently
scored as binary FDA rejections.
