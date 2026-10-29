# Historical FDA database and prediction architecture

Status: **NOT READY / ABSTAIN**. No trained model, calibrated probabilities, independently verified FDA decisions, or measured platform performance.

## Completed engineering

- `research/official_sources.py`: reusable official-source adapters and bounded authorized offline imports. Original bytes, SHA-256, source URL, schema checks, duplicate detection, timestamps and dataset versions remain distinct from origin authentication and publication verification. Existing FDA redirect policy is reused. See [acquisition instructions](OFFICIAL_SOURCE_RECOVERY.md).
- `research/official_history_store.py`: append-only SQLite claims and original BLOB storage, exact application and recorded submission identities, program scopes, conflict reporting, atomic claim import, idempotent exact duplicates. Conflicting versions remain separate claims, never resolved by last write. Byte digests are rechecked on storage. SQLite triggers protect routine writes, not a malicious database owner; this is a local research store, not the existing authenticated service's review ledger. No HTTP route is added.
- Existing six-case registry imports into the store without overwriting it. Company/ticker/drug/indication, target and action dates, source leads, trial/scientific gaps and the entire original registry provenance are retained. Unknown original PDUFA dates remain null: the registry's window target is stored separately as `pdufa_target_date`. Unknown cycles remain null. The existing registry's linked trial metadata is retained in provenance; no uncertain trial lead is promoted into an adjudicated trial identifier. Evidence findings, designations and publication clocks remain unknown unless explicitly sourced.
- Official Drugs@FDA TSV ZIP and openFDA JSON/ZIP normalize recorded application/submission metadata into unverified claims. Official AP/CRL metadata remains in provenance; outcomes remain UNRESOLVED pending action-document/cycle adjudication. FDA submission numbers do not become independently adjudicated review cycles. Bulk import is linear in table size, not a drug-name cross join.
- `research/official_history_readiness.py`: strict pre-cutoff evidence clocks, outcome-document exclusion, exact label identity, official regulatory sources, explicit formal extension events, chronology and related application/family separation. Missing/conflicting evidence and self-certification keep all records ineligible.
- `research/evidence/official_validation_protocol_v1.json` and `research/official_validation.py`: SHA-pinned engineering protocol with distinct PASS/CRL/EXTENSION outcomes and no inferred defaults for unresolved scientific/model parameters. Boundary, required fields, model, sample size and abstention threshold must be prespecified in a new reviewed immutable version. Operational validation only reports blockers.
- Metric arithmetic is exercised exclusively on named built-in synthetic fixtures: per-class confusion/precision/recall, three-class Brier score/log loss, fixed-bin calibration, abstention, area/year strata, sample sizes and descriptive Wilson intervals. This is not a historical backtest. Brier/log-loss intervals remain unavailable until a family-cluster resampling protocol and adequate sample are prespecified. Caller verification flags cannot activate operational metrics.
- `research/official_prediction_contract.py`: authorized read-only output projection reusing existing evidence and historical comparison services. Ten expandable section descriptors, evidence availability grade separate from prediction confidence, provenance/conflicts, biological evidence, risk/score/uncertainty placeholders. No production UI or route is mounted. All predictive scores and probabilities remain unavailable. Existing ten criteria explain agreement, differences, missingness and case selection; descriptive agreement does not establish clinical similarity. Disease biology uses existing BIO fields without inventing a validated similarity score.
- Original eight-field contract, separate 650 draft definitions, 50 levels, 40 canonical assessments and ten comparison criteria are preserved. Structural validation never becomes scientific certification.

## Reproduction

```sh
python -m pip install pytest -r research/requirements-security.txt
python -m pytest -q tests/test_official_*.py tests/test_scientific_*.py tests/test_historical_decision_registry.py tests/test_prediction_v1_1_*.py tests/test_fda_*.py
python research/prediction_v1_1_catalog_validator.py
python -m research.scientific_field_catalog
python -m research.scientific_historical_verification --output research/evidence/historical_verification_worklist_20261029.json --check
python -m research.official_history_store --database /tmp/pdufa-research.sqlite --curated
```

The new snapshot `research/evidence/historical_store_snapshot_20261029.json` is reproducible from an in-memory store and checked by regression test. It contains **six existing curated source-lead cases, zero new external FDA records and zero independently verified decisions**. It is metadata, not original FDA documents. Runtime SQLite files are not committed.

For official bulk ingestion, first use the offline adapter command in the recovery instructions. Then import its receipt:

```sh
python -m research.official_history_store --database /tmp/pdufa-research.sqlite \
  --bulk-receipt /research-artifacts/fda/SNAPSHOT.receipt.json
```

No official bulk dataset was accessible here. The format contracts are fixture-tested, not certified against newly acquired live archives. The CRL adapter validates only the JSON envelope; authentic schema review and field normalization are still required. CT.gov historical imports require external historical-version/publication evidence. No blocked connections were repeated after the initial four transport observations.

## External acquisition worklist

All six need original source bytes, proven public timestamps and independent application/cycle/action review. These URLs are existing source leads, not verified downloads:

| Case | Exact application | Existing document lead |
| --- | --- | --- |
| BCRX | NDA219776 | https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219776Orig1s000ltr.pdf |
| CORT | NDA219398 | https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf |
| NVAX | BLA125817 | https://www.fda.gov/media/186545/download?stream=top |
| TNXP | NDA219428 | https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219428Orig1s000ltr.pdf |
| UNCY | NDA218607 | https://download.open.fda.gov/crl/CRL_NDA218607_20250627.pdf |
| VNDA | NDA220152 | https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220152Orig1s000Approv.pdf |

The existing [verification worklist](../research/evidence/historical_verification_worklist_20261029.json) gives per-case trial leads, 26 observations, gaps, cutoff exclusions and nine independent review tasks. CORT and UNCY review-cycle identity remains unresolved. Original FDA review packages, inspection/CMC evidence, pivotal protocol/SAP/results and dated CT.gov history must be externally acquired and adjudicated; do not extract verified scientific facts from narrative claims.

## Validation and boundaries

Final local checks are recorded in the completion report and PR. The initial broad run needed PyJWT installed and network permission for FastAPI's local test client; isolated networking stalled that preexisting test infrastructure. It passed with the proper permission. Deprecation and unregistered integration-mark warnings are preexisting. External real timestamp/receipt fixtures remain skipped where not supplied.

The new `official-source-recovery.yml` CI runs offline contracts and catalog/worklist checks. Existing CI and backend tests preserve platform behavior. No production scanner/authentication/membership/preset changes, trading enablement, merge or deployment.

Next milestone: an authorized operator supplies original official archives/documents and publication-clock evidence; independent reviewers resolve the six exact cycles and scientific comparisons. Freeze a scientifically reviewed cohort/model/calibration protocol before any fitting or historical performance claim.

Local verification for this increment:

- Combined official-source/history/protocol/output, scientific, historical registry, evidence/security and FDA suites: **728 passed, 298 subtests passed, one external RFC3161 fixture skipped, zero failures**.
- Existing full backend preservation suite: **1,004 passed, one external receipt fixture skipped, zero failures**.
- Original eight-field contract, 650-definition/50-level structural validator, reproducible verification worklist, saved GEM ledger validator and `git diff --check`: passed. Saved-ledger validation is not live verification.
