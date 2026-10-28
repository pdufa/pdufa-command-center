# Recovering the saved historical FDA metadata

`scripts/ingest_hop_recovered_metadata.py` recovers **existing GitHub Actions artifacts**, without contacting FDA, running workflows, opening a production database, or changing any live configuration. It validates a pinned three-artifact package and produces a deterministic audit. An explicit option creates a new local SQLite research file.

The artifacts contain **derived source metadata**, not retained original FDA archives or PDF bytes. Successfully checking a GitHub ZIP hash does not verify the truth of a regulatory action, certify a review cycle, establish source publication dates, or authorize model training. The original collectors discarded the source archives and PDF bodies after processing them.

## Reproduce the audit

From the repository root:

```sh
python scripts/ingest_hop_recovered_metadata.py research/fda/recovered-20261027/manifest.json
```

This is read-only by default. To create a **new** research database in an already existing local directory:

```sh
python scripts/ingest_hop_recovered_metadata.py research/fda/recovered-20261027/manifest.json \
  --database work/phase2-20261027/historical-source-metadata.sqlite3
```

An existing destination, including a symlink, is refused. There is no connection-URL option, environment database lookup, overwrite mode, network fetch, or trust override. SQLite builds the database in memory and serializes the completed transaction. The output is written through an exclusive file descriptor in a directory opened component by component without following symlinks. SQLite never reopens the destination filename. An output I/O failure may leave a new incomplete file for inspection; existing files are never removed as cleanup.

## Pinned provenance package

The JSON manifest has exactly these top-level fields:

```json
{
  "schema_version": 1,
  "record_type": "RECOVERED_HOP_ARTIFACT_PROVENANCE",
  "retrieved_on": "2026-10-27",
  "artifacts": []
}
```

`artifacts` must contain one receipt for each of `CRL_SNAPSHOT`, `DRUGSFDA_SNAPSHOT`, and `ACTION_REVIEW`. Each receipt contains `role`, `artifact_id`, `run_id`, `repository`, `relative_path`, `sha256`, `source_run_head_sha`, and `created_at`. The repository is `pdufa/pdufa-command-center`. The relative path is a unique ZIP filename beside the manifest. The code pins the IDs, run commits, creation timestamps, and ZIP digests obtained from GitHub metadata; modifying a receipt cannot authorize another artifact.

| Role | Run | Artifact |
| --- | --- | --- |
| CRL_SNAPSHOT | 40224038609 | 12610736354 |
| DRUGSFDA_SNAPSHOT | 40224730350 | 12611090768 |
| ACTION_REVIEW | 40236833550 | 12615481622 |

The recovery date means when the saved artifacts were recovered. The source snapshots separately retain their original `retrieved_on` date, October 25, 2026, and their export dates, October 21 and October 23. A collector run creation timestamp is not an FDA source publication timestamp.

The importer checks the full ZIP bytes, expected member sets, member byte digests, bounded expanded sizes, JSON duplicate keys and invalid numbers, regular file types, encryption flags, and quarantined source fields. It reads ZIP members in memory without extraction. Duplicate source IDs or registry IDs, audit count discrepancies, and review rows not linked to the original CRL inventory are rejected. Existing application crosswalk code performs descriptive identity linkage; registry presence does not label a CRL cycle approved.

## What the database preserves

- `source_artifacts`: GitHub receipt, ZIP digest, run, creation time, recovery time, and original snapshot retrieval/export dates.
- `artifact_members`: each original artifact member's byte digest and byte count. The saved ZIP remains the byte-preserving source for full members, including audits and the worksheet.
- `source_records`: canonical JSON of each recovered derived record, with a newly computed `recovered_row_sha256`. This is the recovered row's hash, not the original FDA row hash.
- `crl_observations`: original application ID strings, sponsor, published document type/date, descriptive canonical application candidates, and identity-link status.
- `registry_applications` and `registry_submissions`: raw application identifiers, formatting candidates, sponsor, submission types/numbers, published status codes/dates, and review priority. Each submission remains an indexed observation; it is not assumed to be a distinct review cycle.
- `action_review_observations` and `pdf_check_observations`: a separate observation per CRL source digest, without duplicating the CRL entity count. A recorded PDF fetch/hash check does not mean PDF bytes were retained here.
- `review_cycles`: empty. This importer cannot insert adjudicated labels.

Normalized tables call old source identifiers `claimed_original_source_record_sha256`: those hashes were recorded by the collectors for FDA rows whose original bytes are unavailable. They cannot be recomputed from the reduced recovered rows. The actual artifact member digest and recovered row digest are stored separately.

Drug, indication, trial, PDUFA target date, source publication date, and adjudicated cycle fields stay NULL when absent. A source letter date is not silently reused as an effective FDA action date or publication date. Bad/missing dates remain raw values and are excluded from date-range calculations. Formatting `NDA21939` as candidate `NDA021939` preserves the published identifier separately and does not independently verify that identity.

## Actual recovered inventory

The saved artifacts contain 458 published-letter observations, 29,416 approved-registry applications, and 188,890 submission observations. Source status codes are AP 187,733, TA 1,155, CR 1, and missing 1. The CR source code is **not** automatically an adjudicated CRL cycle. There are 2,706 registry applications without submission metadata.

All 458 published-letter date strings parse, ranging March 15, 2002 through August 7, 2026. Of the submission dates, 188,883 parse and 7 are missing/invalid; the valid range is February 9, 1939 through October 21, 2026. These are ranges of source metadata, not a statement of complete historical FDA decision coverage.

The action-review artifact contains 458 worklist observations, 458 PDF-check observations, and 154 unadjudicated worksheet rows. These overlap the same 458 letters and must not be added together as independent decisions.

**Independently verified eligible PASS: 0. FAIL: 0. Backtesting-eligible decisions: 0.** The full application/review-cycle denominator, exact cycle adjudication, primary document bytes, source publication chronology, and usable predecision scientific evidence remain incomplete. No prediction probabilities or predictive accuracy are established by this recovery or its software tests.

Run the importer for the full computed counts, exclusions, provenance/member fingerprints, and limitations. The report deliberately separates imported metadata from independently verified decisions.

## Regression verification

```sh
python -m pytest -q tests/test_ingest_hop_recovered_metadata.py
```

Tests use small synthetic integrity fixtures and isolated temporary SQLite files. They check actual normalized row counts, foreign keys, preserved NULLs/raw dates, forced model ineligibility, deterministic audits, cross-artifact joins, duplicate and malformed input rejection, symlink/encryption/size rejection, rollback before output, and refusal to overwrite a destination created concurrently. They do not measure FDA prediction performance.
