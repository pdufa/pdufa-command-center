# HOP Historical FDA Outcomes — JSON data contract v2

This is a **quarantined curated input format**, not a populated historical database.
Do not create invented outcomes or infer FDA decisions from trial phases.

The JSON envelope is `{"schema_version": 2, "records": [...]}`. An explicit empty
inventory uses `records: []`. The unversioned v1 array is rejected: its
`evidence_as_of` mixed predecision feature dates with outcome-document dates.
Migrate from original dated sources rather than relabeling or guessing dates.

Each record requires exactly the fields in the historical CSV intake contract:

- `case_id`: unique immutable decision/program identifier.
- `application_id`: explicit NDA, BLA or ANDA identifier with six digits; an optional
  hyphen is normalized, for example `BLA-125807` to `BLA125807`.
- `review_cycle`: positive integer from reviewed cycle evidence, never inferred
  from the number of letters or a later approval.
- `drug_name`, `sponsor`, `indication`, `therapeutic_area`, `modality`: nonempty
  source-supported text.
- `phase`: integer 3 or 4 for the retained HOP comparator contract.
- `decision_date`: YYYY-MM-DD official FDA decision date.
- `outcome`: `APPROVED` or `COMPLETE_RESPONSE` for binary comparators. Other
  actions remain in the broader CSV review queue and are not forced into binary
  historical outcomes.
- `public_features_as_of`: YYYY-MM-DD public availability date of the comparison
  features, strictly **before** the historical FDA decision.
- `evidence_as_of`: YYYY-MM-DD public availability date of the outcome evidence,
  **on or after** the FDA decision, separately from feature availability.
- `source_url`: official FDA HTTPS document URL, without credentials, a custom
  port or a fragment.
- `source_title`: original document title.

The JSON adapter reuses CSV record validation. Dates must be real calendar dates;
all must be at or before the import `as_of` date (today by default). Case IDs and
canonical application/review-cycle pairs must be unique. A CRL and a later
approval can coexist only with distinct explicit reviewed cycle identifiers;
this intake does not prove those identifiers. Missing/extra fields, duplicate
JSON keys and unbounded input fail the whole import. No partial result is returned.

`parse_history` and `load_history` return comparator records with the canonical
application/cycle IDs and both separate dates. Their
`independently_adjudicated` flag is always **false**. Schema checking does not
examine source content, authenticate identities, establish cycle boundaries,
verify predecision availability, or establish a complete historical denominator.
Supplying a reviewer or eligibility flag in JSON is rejected as an unknown field.
The comparator excludes these records until a separate independent adjudication
workflow has established source truth; the importer provides no promotion path.

Approval probability remains null until leakage-controlled independent
backtesting, calibration and outcome adjudication. Source URLs and SHA-256
fingerprints do not establish predictive validity. Never treat synthetic test
fixtures as actual FDA decisions or validated prediction accuracy.
