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
