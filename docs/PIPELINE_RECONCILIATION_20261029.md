# First authenticated staging Pipeline reconciliation

Prediction status: **NOT READY / ABSTAIN**. Preliminary predictions generated: **0**.

[Run 40969177461](https://github.com/pdufa/pdufa-command-center/actions/runs/40969177461)
successfully executed the existing **Authorized staging Pipeline reconciliation**
job on research commit `07968fec1182168f60de9ccf735710bca96a0b77`. The run started
at `2026-10-29T22:52:59Z` and completed successfully. The unrelated isolated-review
job was skipped as intended. No additional staging retrieval was performed for
this offline audit.

## Actual reconciliation results

| Metric | Verified report value |
| --- | --- |
| Workspace version | `fdccd924f40af590ef6ae3107783d7ca37d27d8a503d33c0d99485c5a53d7eef` |
| Source date | `2026-10-29` |
| Source precision | `CALENDAR_DATE_LOS_ANGELES` |
| Observation timestamp | `2026-10-29T22:53:06.034570+00:00` |
| Total Pipeline records | 11,812 |
| Records retrieved | 11,812 |
| Pages retrieved | 119 |
| Unique permanent program IDs | 11,812 |
| Unique source program IDs | 11,812 |
| Missing source program IDs | 0 |
| Duplicate permanent program IDs | 0 |
| Duplicate source program IDs | 0 |
| Missing records relative to API total | 0 |
| Market-cap source evidence present | 114 |
| FDA target source evidence present | 0 |
| Candidates passing the research scope gate | 0 |
| Blocked candidates | 11,812 |
| Retrieval complete | YES |
| Summary-to-page reconciliation passed | YES |
| Artifact transport integrity checked | YES |

The observation time is October 29, 15:53:06 PDT, agreeing with the reported Los
Angeles source date. `freshness_basis=CURRENT_LA_CALENDAR_DATE` records that
calendar-day check. It does not establish an exact elapsed-hour snapshot age or
the publication times of original documents. Cap-claim freshness uses the actual
observation clock, explicitly labeled `OBSERVATION_TIME_NOT_SOURCE_PUBLICATION`.

## Preserved original artifact and audit

Artifact ID **12940010697**, name **staging-pipeline-reconciliation**, contains
only `pdufa-pipeline-reconciliation.json`. Original bytes are retained in
[the evidence directory](../research/evidence/pipeline_reconciliation/20261029_run_40969177461/),
alongside a versioned [audit manifest](../research/evidence/pipeline_reconciliation/20261029_run_40969177461/audit-manifest.json).
This avoids losing the report when GitHub's one-day artifact retention expires.
No raw program records, individual IDs or credentials are included.

- Original ZIP: **787 bytes**, SHA-256
  `8c89a4e99f8c35aa93ea2e3879212bbcd09ae9660873a9d66a174972ab772bf8`.
  This matches GitHub's artifact metadata and upload log digest.
- Original JSON: **1,208 bytes**, SHA-256
  `66a166adc368d779cb59574fb77b32f227968cb9e288ddaf44c056b2016fc6b8`.
- Reported retrieved-row hash:
  `ddde33a9108e847a3a54d48be8058942d5f8b59fcb07bed9cf5498b4636709fa`.
  Its scope is `RETRIEVED_JSON_NOT_INDEPENDENT_SOURCE_OR_RESTRICTION_VERIFICATION`.

The primary review and a separate software reviewer independently read the ZIP
and JSON bytes, matched their hashes, checked the sole ZIP member and CRC,
rejected ambiguous/nonfinite JSON, and verified count types and arithmetic.
11,812 records equal 118 full 100-row pages plus a final 12-row page. Unique
source IDs plus missing source IDs equal the received count; candidates plus
blocked records equal the total. Both duplicate counts are zero only because the
runner completed its global identity checks before emitting a success report.

Raw rows are intentionally absent from the aggregate artifact. The offline audit
therefore cannot independently recount individual identities or recompute the
retrieved-row hash. Those checks were performed by the committed authenticated
runner. Software review is not independent FDA regulatory adjudication.

## Eligibility and scientific interpretation

The 114 market-cap entries are source-supported, timely **claims**, not verified
public listings or proof that the $300M–$10B restriction is satisfied. That count
can include values outside the permitted range. The zero FDA count means no row
met the existing mapper's target-date/source/status contract; it does not prove
that no real program has a PDUFA target.

Published membership and ticker fields do not independently verify public
listing or approved restrictions. The conservative mapper keeps both gates
unverified. Thus all 11,812 records are blocked and zero pass the current research
scope gate. Actual company/program eligibility remains unestablished. No
therapeutic-area comparison, clinical efficacy, safety, CMC assessment, FDA
outcome label, calibrated probability or trading conclusion is inferred.

<details>
<summary>Scientific readiness and next evidence requirements</summary>

- **Evidence readiness:** inventory transport/count reconciliation passed;
  independent regulatory, listing and restriction evidence is incomplete.
- **Scientific assessment readiness:** not established for an eligible program.
  The aggregate does not retain individual program identities or original
  scientific records needed to select the earliest upcoming eligible decisions.
- **Historical validation readiness:** no new independently adjudicated FDA
  decisions or genuine out-of-sample prediction results were produced.
- **Prediction confidence:** unavailable; no numerical confidence or prediction
  accuracy is justified. Principal outcome remains **NOT READY / ABSTAIN**.

Next obtain source-bound program-level evidence in an authorized research
workspace, join it to exact permanent/source identities, and independently
verify listing, market cap/range, active program, applicable phase/pathway, drug,
indication, application/cycle and official target date. Continue original FDA
document acquisition and independent adjudication before model evaluation.

The existing 650 fields, 50 investigation levels, 40 assessments and ten
comparison criteria remain unchanged.

</details>

## Comparison with previous operational observations

| Population | Observation | Verification limit |
| --- | --- | --- |
| Retrieved staging Pipeline | 11,812 records | This run's summary/pages/summary checks passed |
| Previously reported registry | 11,636 entries | Earlier observation; no current SQL recount |
| Previously reported candidate assessments | 11,812 records | Earlier observation; identities not joined to this run |

Equal numeric counts do not establish equal populations. No missing-record,
registry-allocation or overlap count is inferred from differences between these
observations. The run may have inserted only missing permanent identities via
the already authorized mechanism; the number of new allocations is unmeasured.
Existing-ID stability and database constraints have source/isolated-test
coverage, not an independent before/after staging SQL audit.

## Verification and preservation

At retrieval commit `07968fec`, all **14 PR CI workflows passed**. Its relevant
regression suite passed **148 tests**; broader research checks passed **903 tests
plus 43 subtests**, with one genuine external TSA fixture skipped and zero
failures. The manual retrieval and artifact upload also passed. Preserved-byte
hash checks and count/clock review passed on the actual downloaded artifact.

This completion increment preserves the aggregate evidence and report. It does
not change production settings, authentication, scanners, restrictions, original
FS/FA associations, PIPELINE → GEM JR → GEM → WT, or trading functionality.
No merge, deployment or new credential was performed.
