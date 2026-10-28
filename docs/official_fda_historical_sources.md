# Official FDA historical decision source registry

Status: source discovery verified against official FDA pages; no claim of downloaded, parsed, reconciled, or validated corpus.

## CRL source
- Dataset: openFDA Transparency / Complete Response Letters
- Documentation: https://open.fda.gov/apis/transparency/completeresponseletters/
- Download catalog: https://open.fda.gov/data/downloads/ (Transparency > Complete Response Letters)
- API example: https://api.fda.gov/transparency/crl.json?limit=1
- Role: documented CRL actions and deficiencies; not a complete denominator of all FDA decisions.
- Caveats: partial historical coverage, subsequent approvals, redactions, changing data, publication date versus decision date, and incomplete application linkage.

## Approval source to reconcile
- Drugs@FDA: https://www.accessdata.fda.gov/scripts/cder/daf/
- openFDA Drugs@FDA: https://open.fda.gov/apis/drug/drugsfda/
- Role: approved application actions and dates; not a complete list of CRL nonapprovals.
- Additional BLA records may require CBER source reconciliation.

## Required ingestion workflow
1. Fetch official source metadata and snapshot downloads with retrieved_at, SHA-256, original URL, and license.
2. Preserve source record IDs, application numbers, letter/action dates, publication dates, and links to original letters.
3. Validate event type from the document; do not infer PASS from absence of CRL.
4. Distinguish decision cycle from eventual application disposition: a CRL followed by approval represents distinct dated decisions.
5. Reconcile NDA/BLA identifiers and supplements, deduplicate *per application review cycle*, not forever per application.
6. Quantify coverage gaps, missing documents, redactions, and selection bias before using frequencies as probabilities.
7. Enforce as-of evidence availability separately from outcome label date in backtesting.
8. Publish verified eligible PASS/FAIL cycle counts, excluded events, and provenance audit before training.

## Release gate
No training, calibration, or approval-rate estimate until coverage and cycle-level identity have been audited. Publicly downloadable is not synonymous with imported or validated.
