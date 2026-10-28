# Exact historical FDA cohort roster audit

The existing manifest audit now compares actual declared members, rather than
only two caller-supplied counts. Equal counts cannot hide a missing application
and an unrelated substitute. This is a metadata audit, not independent FDA
source verification, a representative-sampling certificate or model clearance.

## Input and replay contract

Call `audit_cohort_manifest(manifest, expected_members=..., observed_members=...,
as_of=date(...))`. Existing count-only calls remain blocked with
`exact_roster_required`. An empty expected roster cannot reconcile. The existing
manifest coverage/source/reviewer fields remain required; `as_of` fixes the
research audit date, not a historical prediction or publication timestamp.

Each expected member supplies `application_id` and positive integer
`review_cycle`. Supported application spelling is NDA/BLA/ANDA plus six digits,
optionally one hyphen; whitespace/case aliases normalize to the same identity.
Boolean or textual cycles and ambiguous identities are rejected, never guessed.
Reviewers must still resolve original applications, supplements and exact cycle
definitions upstream; this audit does not infer them from filenames.

Each observed member also supplies a `disposition`:

| Disposition | Binary FDA label supplied by this audit |
| --- | --- |
| APPROVED | None; counted as an approval metadata claim only |
| COMPLETE_RESPONSE | None; counted as a CRL metadata claim only |
| WITHDRAWN | None |
| DELAYED | None |
| REFUSE_TO_FILE | None |
| UNRESOLVED | None; additionally blocks resolution |
| OUT_OF_SCOPE | None; requires a nonempty exclusion reason |

Target revisions and unresolved action types need separately verified dated
event histories; no string alias converts them into a binary rejection.
Unknown/missing dispositions remain visible as invalid claims. They cannot
remove their member from the denominator.

Identity reconciliation happens before disposition quality filtering. Every
repeated expected/observed identity is reported, including invalid sibling
claims. The output distinguishes raw row counts, unique identities, invalid
identities/dispositions, missing/extra members and duplicates. Declared counts
must equal both actual row counts and unique identities.

`disposition_row_counts` retains all recognized row claims.
`disposition_counts` and `binary_disposition_cycles` count only unique observed
identities matched to unique expected members. They are **not verified outcomes
or model-eligible cases**. The output always retains `metadata_only=true`,
`model_eligible_records=0`, `probability=null`, and an unconditional external
source-verification blocker. `RECONCILED_METADATA_ONLY` describes matching
declarations; overall status remains `BLOCKED`.

## Offline command

The input envelope has exactly four fields: `schema_version: 1`, `manifest`,
`expected_members` and `observed_members`. Both member fields are arrays. No
populated real cohort is supplied by this engineering change.

```sh
PYTHONPATH=new-platform/backend python new-platform/backend/scripts/audit_hop_cohort_manifest.py /path/to/reviewed-cohort-input.json --as-of 2026-10-28
```

The command reads the local file, rejects repeated JSON keys and writes a JSON
audit to stdout. Exit **1** means review remains blocked; exit **2** means invalid
input or inaccessible local file. It never returns model clearance, fetches a
source, writes to a database, changes a sheet or modifies its input.

`input_metadata.sha256` is computed from the actual input file bytes. Its scope
is explicitly **research metadata, not FDA source-document bytes**. Neither this
hash nor a caller's reviewer name/flag establishes source truth, a prespecified
sampling frame, blinding or independence. Expected membership must come from a
separately justified complete population, never copied from a selected CRL-only
archive or a model's successful predictions.

## Remaining empirical prerequisites

Original-document availability and publication clocks, exact action/cycle and
PDUFA target histories, independent adjudication, frozen predecision features,
related-program grouping and a genuinely untouched evaluation partition remain
upstream requirements. This increment supplies no baseline model or measured
accuracy. Existing legacy prediction-history labels are not certification of
out-of-time independence.
