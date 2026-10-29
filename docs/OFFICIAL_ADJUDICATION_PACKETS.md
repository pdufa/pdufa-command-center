# Historical FDA original-byte review packets

Status: **NOT READY / ABSTAIN**. This increment prepares independent review;
it does not perform or certify it.

The latest research baseline is PR #522, commit `92443fb2`. Its thirteen
pull-request workflow runs were inspected on October 29, 2026: twelve succeeded,
and Official source recovery safety run `40881886113` failed during collection
because `tests/test_fda_directional_sanitizer.py` imports pandas through the
existing legacy script. The recovery job now installs that missing dependency.
No legacy model is run by this change. Production configuration is unchanged.

## Completed engineering milestone

`research.official_adjudication_packets` joins authorized acquisition receipts
to the existing six-case scientific verification worklist. It matches exact
action-document URLs, reopens and hashes original bytes, checks the acquisition
snapshot digest and minimal PDF contract, and retains a digest of the receipt.
The PDF check is structural only: it does not authenticate a document, parse its
contents or establish application/cycle identity from those contents.

Originals and receipts must be inside the operator-selected evidence directory.
Reads are bounded; symlink paths, path escapes, repeated JSON keys, modified
bytes, unrelated URLs and attempted receipt self-certification are rejected.
Identical URL/byte candidates are deduplicated. Different versions of one exact
source remain separate, explicitly conflicting review candidates; no version
silently wins. Output creation never overwrites an existing report, and input
validation completes before output creation.

All original worklist identities, trial leads, missing documents, cutoff
exclusions and nine independent review tasks remain present. Claimed cycles and
outcomes stay separate from null adjudicated fields. Acquisition time, claimed
publication time and HTTP Last-Modified never become a verified publication
clock. A successful byte check closes no independent review task and creates
no training eligibility, prediction, probability or performance metric.

## Authorized offline replay

After acquiring originals using the existing recovery instructions, use absolute
paths or paths relative to the evidence directory. For a relocated bundle,
change the receipt's `original_path` to its relative filename; retain the original
receipt separately. A changed receipt has a different receipt digest.

```sh
python -m research.official_adjudication_packets \
  --evidence-directory /authorized/fda-bundle \
  --receipt CAPTURE.receipt.json \
  --output /authorized/review-packets.json
```

Repeat `--receipt` for each candidate. Omitting receipts produces the six-case
missing-original queue. Keep raw evidence and full research packets in the
authorized research location, outside committed source. The packet contains
metadata and source leads, never raw PDF bytes or local filesystem paths.

## Observed verification

- Recovery/research/scientific/FDA suites: **753 passed, 298 subtests passed,
  one external RFC3161 fixture skipped**, no failures. Includes 25 packet tests
  using explicitly synthetic PDF bytes, not FDA evidence.
- Full backend preservation suite: **1,004 passed, one external receipt fixture
  skipped**, no failures; existing dependency/deprecation warnings remain.
- Original eight-field contract, 650-definition/50-level structural validator,
  and reproducible existing verification worklist checks passed. Structural
  checks establish no independent scientific validation.
- Actual no-receipt CLI replay: six cases, zero retained-original candidates,
  zero independently verified decisions, zero evaluated predictions.

Remote CI for the implementation must be checked after publication; the baseline
failure above is not a claim about the new commit's checks.

## Remaining evidence milestone

No new official FDA/NIH documents were downloaded. Existing access observations
and host restrictions remain unchanged; blocked source probes were not repeated.
An authorized operator must supply authentic original documents and publication
evidence. Independent reviewers must resolve exact application/indication/cycle,
PASS/CRL/formal extension, scientific/CMC conflicts and predecision chronology.
The frozen cohort/model/calibration and holdout protocol remains unresolved.
These packets are review preparation, not completion of that scientific work.

No scanner schedules, API routes, production authentication, database schemas,
GEM JR/GEM FS/FA associations, memberships, spreadsheets or trading settings were
changed. No merge or deployment is part of this increment.
