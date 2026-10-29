# Six-case official-evidence acquisition: operator handoff

**Research only — NOT READY / ABSTAIN.** This guide does not authenticate FDA documents, approve regulatory labels, or enable training, trading, deployment, or production scans.

## Current boundary
The research registry contains six **unverified** cases. The acquisition manifest is a set of requirements, not proof that a source document was obtained. A locator is a lead, not evidence of a document's contents or publication clock. Official FDA/NIH hosts may be blocked in Codex Cloud; do not bypass access controls.

## Step 1 — Generate the exact requirements

From the repository root, using the project Python environment:

```bash
python -m research.official_acquisition_manifest --output /tmp/pdufa-six-case-acquisition.json
```

The output includes case IDs, exact document IDs, application IDs, document families, source leads, and unresolved locator flags. Do not edit source identifiers to force a match. Inspect `cases[].documents[]`; entries without `source_url` require independent locator resolution before this importer accepts them.

## Step 2 — Acquire authorized originals

An authorized operator may download the original official archive/document outside the restricted cloud environment. For every original retain:

- Original bytes and an SHA-256 digest (not a screenshot or summary).
- The exact official URL and acquisition timestamp (with timezone).
- Dataset version or snapshot identifier.
- Any separately supported publication-time evidence.
- Application number, indication, and regulatory-cycle evidence.

**Do not claim a publication timestamp merely from the time of download.** Do not infer CRL or extension from the absence of an approval record or an elapsed target date.

## Step 3 — Prepare the offline import bundle

Create a JSON **array** of entries. Each entry must have exactly these keys:

```json
[
  {
    "document_id": "REPLACE_WITH_EXACT_MANIFEST_DOCUMENT_ID",
    "path": "original-file-relative-to-evidence-directory.zip",
    "sha256": "REPLACE_WITH_64_LOWERCASE_HEX_CHARACTERS",
    "dataset_version": "REPLACE_WITH_SOURCE_SNAPSHOT_VERSION",
    "operator_acquired_at": "2026-10-29T12:00:00Z",
    "claimed_published_at": null,
    "publication_evidence": null
  }
]
```

The date is **illustrative**, not a claim about an actual acquisition. The importer requires a known official source URL, exact document ID, recognized payload format, bounded file size, digest match, and additional application/trial identity checks where applicable. Entries for unresolved locators cannot be imported by pretending that a URL exists.

## Step 4 — Run fail-closed import

```bash
python -m research.official_acquisition_manifest \
  --output /tmp/pdufa-offline-import-report.json \
  --bundle acquisition-bundle.json \
  --evidence-directory /absolute/path/to/authorized-originals \
  --retention-directory /absolute/path/to/research-retention
```

The bundle file must be inside the evidence directory unless an accepted absolute path is used. The output report path must not already exist. Never place licensed, private, or otherwise restricted originals in a public repository. Use authorized secure storage and retention controls.

## Step 5 — Independent adjudication

An import receipt is **not** independent verification. Separate reviewers must establish authentic original-source provenance, exact NDA/BLA and review cycle, regulatory event classification, source publication time relative to the prediction cutoff, and conflict resolution. A formal extension requires explicit target-date revision evidence. Until these gates pass, the case is ineligible for training/evaluation and the system remains **NOT READY / ABSTAIN**.

## Blocking handoff to operator

1. Export the current six-case manifest.
2. Prioritize the known/derived official leads; record successful original-byte acquisitions separately from URL discoveries.
3. For unresolved locators, document required family, exact case/cycle, search route, and why resolution remains blocked.
4. Provide original files through approved secure intake, not a public GitHub commit.
5. Request independent adjudication and freeze a chronological evaluation protocol **before** fitting a model.

Do not claim six verified cases, any historical accuracy, or a live prediction merely because this runbook or importer exists.
