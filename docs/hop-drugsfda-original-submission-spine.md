# Drugs@FDA original NDA/BLA submission inventory — research only

This new offline intake is a first *population-inventory* step, **not a
completed FDA decision denominator**. Its primary purpose is to preserve the
difference between an FDA application, an original submission, a review cycle,
a Complete Response Letter, and a subsequent approval.

## Official source and data handling

Use FDA's [Drugs@FDA Data Files](https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files),
which documents the downloadable, tab-delimited `Applications` and
`Submissions` tables. The source's `ApplType`, `SubmissionType`,
`SubmissionNo`, `SubmissionStatus` and `SubmissionStatusDate` columns are
raw metadata; **no single field independently proves an application review
cycle or adjudicated outcome**.

FDA's [published CRL database](https://open.fda.gov/apis/transparency/completeresponseletters/)
provides historical letters, but letters are distinct from review-cycle
decisions and cannot establish a full approval/nonapproval population.
The Drugs@FDA export is approval-centric and may not include all never-approved
applications, unreviewed submissions, decisions or cycle histories.

The new ingestion only:
- accepts 6-digit application identities from `Applications.txt`;
- retains applications classed as NDA or BLA, while counting but excluding ANDA;
- retains submission records with **`SubmissionType=ORIG`** and their
  original submission number; excludes supplements from this first population;
- preserves raw submission status codes and reported status dates as
  **unverified metadata**, never translating `AP`, `CR` or other codes
  into FDA approval or nonapproval outcome labels;
- detects repeated original-submission keys, missing registry application
  identities, missing or malformed status dates, unsafe status code strings,
  and dates beyond the requested research cutoff;
- computes local SHA-256 fingerprints of the supplied TSV files so repeated
  local analyses can be compared; those fingerprints do *not* independently
  authenticate FDA origin;
- returns **`review_cycle: null`, `fda_action_outcome: null`** for every
  retained row and globally `model_eligible_records: 0`,
  `prediction_probability: null`, `approval_rate: null`.

The intake never fetches external data, writes to Render/Postgres, changes
the live system, or acts on a ticker.

## Local execution

After obtaining and extracting the official FDA data ZIP, select the actual
tab-delimited Applications and Submissions files. Filenames/case may differ;
supply their concrete paths. From the repository root:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/audit_hop_drugsfda_original_submissions.py \
  /path/to/Applications.txt \
  /path/to/Submissions.txt \
  --as-of 2026-10-25 \
  --output-json /path/to/private/drugsfda_original_submissions_audit.json
```

A count of captured original NDA/BLA *submission history entries* may help
prioritize historical source reconstruction. It is **not** the number of
unique FDA decisions or the denominator of a predictive success rate.

In particular, an original `SubmissionNo=2` may be a separate original
submission, not the second FDA review cycle; the current extraction
intentionally leaves `review_cycle` empty until original action chronology
is independently established. Raw `SubmissionStatusDate` is not always
equivalent to the original FDA letter's effective date.

## Unresolved scientific work

An independently specified historical study frame must include both approved
and nonapproved original NDA/BLA application review-cycle decisions in the
same exact period. Later approval does not change an earlier CRL's action
classification. Resolve original versus supplement, multiple original
submissions, and multiple FDA action letters as different entities; acquire
and adjudicate original contemporaneous evidence. Reconcile candidate records
against the official registration history and published letters, plus other
authoritative sources for never-approved applications. Prevent post-decision
information from entering pre-decision predictors. Perform temporal
out-of-sample testing and probability calibration only after adjudication.

The offline command intentionally returns nonzero, even if all raw rows
parse successfully, because scientific completeness is not established.
The current research branch **does not contain or claim an installed
29,416-row original-review-cycle dataset**; that prior number refers to
approval-centric application references, not this new extractor's output.

## Actual official FDA collection: October 25, 2026

The research-only pull-request workflow
[HOP original NDA/BLA source audit](https://github.com/pdufa/pdufa-command-center/actions/runs/40246351051)
successfully downloaded the FDA ZIP through the pinned `www.fda.gov`
media URL, examined the tab-delimited `Applications` and `Submissions`
tables, and saved the **aggregate-only** audit as
[GitHub Actions artifact 12618966198](https://github.com/pdufa/pdufa-command-center/actions/runs/40246351051/artifacts/12618966198).
Its captured, byte-fingerprinted aggregate record is committed in
`new-platform/backend/app/research_sources/hop_drugsfda_original_submissions_20261025.json`.

| Raw-source observation | Observed result | Interpretation |
|---|---:|---|
| Raw application table rows | 29,417 | FDA source-table observations, not FDA decisions |
| Valid non-placeholder application IDs | 29,415 | Includes ANDAs as well as NDAs and BLAs |
| Invalid/placeholder application IDs quarantined | 2 | Do not silently treat as a valid FDA application |
| Raw submission rows | 194,280 | Includes supplements and ANDA histories |
| Original NDA/BLA submission rows | **6,033** | Raw original submission *history entries*, not review cycles |
| Distinct NDA/BLA application IDs in original submission rows | **5,973** | Approval-centric registry subset with apparent original-submission history |
| Submissions excluding NDA/BLA application types | 101,547 | Mutually exclusive first-pass classification |
| Nonoriginal submission histories excluded | 81,325 | Predominantly supplements and other types |
| Submissions with no matching valid application identity | 5,375 | Require source reconciliation; do not assign |
| Raw submission status missing | 1 | Data-quality flag, not a nonapproval outcome |
| Independently verified original FDA review-cycle decisions | **0** | Nothing qualifies for predictive model training |

The original `Applications` file decoded as UTF-8; `Submissions` used a
strict Windows-1252 fallback for source text with legacy punctuation. Neither
raw table was modified in the deployed application or committed as a bulk
database. The archive hash, table hashes, run link, source URL and download
timestamp are preserved in the aggregate index. Source CSV/TSV data are not
part of the GitHub workflow artifact; it contains only counts and checksums.

The 5,973 applications, 6,033 original-submission records and 458 selectively
published response-letter references have **different units and coverage**.
They cannot be combined into an FDA approval/decline denominator, and a
submission `SubmissionNo` does not identify an independently verified FDA
review cycle. Also, Drugs@FDA primarily describes *approved* drugs; its
source rows do not enumerate all applications never approved. Differences from
other previously collected approved-drug snapshots are possible and require
source/version reconciliation, not averaging or inferring new decisions.

**All subsequent steps are blocked on independent original action chronology,
cycle reconstruction, explicit inclusion of unapproved NDA/BLA candidates,
verified predecision evidence and out-of-time model calibration.** Approval
rates, accuracy and per-drug FDA approval probabilities remain unavailable.
No PIPELINE, GEM JR, GEM, WT, scan, trading or production configuration changed.
