# Six-case official document acquisition and offline import

**NOT READY / ABSTAIN.** This is an acquisition requirements manifest and
operator-import workflow, not an independently verified historical cohort.

`research/evidence/official_acquisition_manifest_20261029.json` is reproducible
from the existing six-case registry and scientific verification worklist. It
preserves exact application/drug/indication claims and unresolved cycle identity.
Each case explicitly requests the Drugs@FDA action dataset, its known FDA action
letter, original target-date evidence, official target revisions, multidisciplinary
review and historical trial records. Original official locators not present in
the registry remain null, requiring source review. SEC issuer observations stay
separate source leads; they are not substituted for official FDA correspondence.

The six exact primary-document leads are preserved unchanged:

| Case | Application claim | Exact original FDA document lead |
| --- | --- | --- |
| BCRX | NDA219776 | https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219776Orig1s000ltr.pdf |
| CORT | NDA219398 | https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf |
| NVAX | BLA125817 | https://www.fda.gov/media/186545/download?stream=top |
| TNXP | NDA219428 | https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219428Orig1s000ltr.pdf |
| UNCY | NDA218607 | https://download.open.fda.gov/crl/CRL_NDA218607_20250627.pdf |
| VNDA | NDA220152 | https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220152Orig1s000Approv.pdf |

UNCY's existing later 2026 CRL lead remains a separate requested document, never
a replacement for the 2025 letter or proof of independently adjudicated cycles.
TNXP's existing NCT05273749 supports a derived current-record API query; it does
not establish historical availability. RELIEF/F304 and RALLY/F306 registry IDs
remain unresolved. No trial IDs, review packages or target-revision URLs are
invented. A null locator blocks import until an independently reviewed source
manifest supplies the missing locator in a subsequent version.

Each document family references relevant existing comparison criteria. The
multidisciplinary review requirement maps to all ten existing criteria, while
trial history maps to design, endpoints, efficacy, safety and statistics. These
are evidence requirements, not newly established scientific findings. The
existing 650 draft definitions, 50 investigation levels and 40 canonical
assessments remain unchanged. Retained observations keep their assessment IDs,
source locations and availability caveats.

## Reproducible manifest

```sh
python -m research.official_acquisition_manifest \
  --output research/evidence/official_acquisition_manifest_20261029.json --check
```

To create a new local copy, omit `--check` and use a new output path. The CLI
never overwrites an existing report.

## Authorized offline bundle

FDA/NIH hosts remain outside this runtime's allowed destinations. Do not retry
blocked hosts or bypass access controls. An authorized operator acquires the
originals elsewhere following `OFFICIAL_SOURCE_RECOVERY.md`, preserves original
bytes and original acquisition/publication provenance, and transfers an offline
bundle. Its JSON plan is an array with exactly these keys per entry:

```json
[
  {
    "document_id": "BCRX|2025-12-12:APPROVAL_LETTER",
    "path": "original-letter.pdf",
    "sha256": "REPLACE_WITH_ACTUAL_64_CHARACTER_LOWERCASE_SHA256",
    "dataset_version": "REPLACE_WITH_OPERATOR_RECORDED_VERSION",
    "operator_acquired_at": "REPLACE_WITH_AWARE_ORIGINAL_ACQUISITION_TIMESTAMP",
    "claimed_published_at": null,
    "publication_evidence": null
  }
]
```

This example is deliberately not importable without real integrity/provenance
values. `document_id` is copied exactly from the manifest. An operator does not
supply a new URL or an independent-verification assertion. Paths are absolute
inside the chosen evidence directory or relative to that directory. A claimed
publication timestamp requires a retained evidence description and cannot
postdate the external acquisition timestamp. Neither field becomes independently
verified. Preserve actual external acquisition time separately from local import
time; neither proves earliest public availability.

```sh
python -m research.official_acquisition_manifest \
  --bundle bundle.json --evidence-directory /authorized/fda-bundle \
  --retention-directory /authorized/retained-fda \
  --output /authorized/review-import-report.json
```

The entire batch is preflighted before retention: exact schema, known document
requirement and official URL, original SHA-256, adapter schema, confined paths,
symlink rejection, aware acquisition time and exact current-trial ID. Batch limits
are 128 entries and 256 MiB aggregate original bytes. Unknown official locators
fail visibly instead of accepting arbitrary guessed PDFs. The exact requested
application must occur in a Drugs@FDA import's application table. A bulk dataset
may omit a CRL-only application; this rejects that case-bound import, never
assigns a negative outcome. Use the existing general-source adapter to retain
the unmatched dataset separately. Application/cycle reconciliation still requires
the existing historical store and independent source review.

The existing `OfficialAdapter` retains original bytes and append-only acquisition
receipts. Identical entries are deduplicated within the batch; different source
byte versions are retained and reported as conflicts. Identical bytes with
different operator provenance retain separate acquisition claims and receipts;
the report calls for provenance review instead of selecting a publication claim.
Repeated imports can append
new receipt observations without overwriting originals. A filesystem failure
during retention may leave earlier valid receipts; rerun/reconcile them rather
than deleting audit history. The report shows missing and conflicting families
for all six cases, including cases with no supplied documents. Its explicit scope
is the current bundle only, not complete retention history: previously retained
receipts must be reconciled separately using the historical store/review ledger.
It reports zero
independently verified decisions and supplies no model metrics or probabilities.

Action-letter receipts feed the existing `official_adjudication_packets` CLI
unchanged. Drugs@FDA receipts feed the existing `official_history_store
--bulk-receipt` path; the resulting application/submission claims remain
UNRESOLVED and unverified. FDA PDF signature/header checks are structural only,
not document authentication or application/cycle adjudication. Current trial
records never substitute for historically versioned records.

No new official records were acquired by this engineering increment. The next
external step is authorized original-document acquisition, publication-clock
proof and independent case/scientific review. No production scanner,
authentication, membership, FS/FA, spreadsheet, database or trading setting changes.
