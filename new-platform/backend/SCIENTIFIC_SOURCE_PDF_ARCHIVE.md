# Scientific source-PDF preservation — read-only by default

**Scope:** Isolated Render review service on `feature/scientific-assessment-v1`. This feature can preserve the actual bytes of user/curator-supplied PDF source documents and verify their stored content and provenance metadata against SHA-256 digests. It **does not** authenticate a publisher, confirm a clinical finding, resolve an adjudication question, or assign an approval probability.

## What is now installed

An additive PostgreSQL table, `scientific_source_documents`, records exact NCT identity, external evidence gate, public HTTPS source URL, source type, generated immutable filename, curator label, capture timestamp, byte length, original binary PDF bytes, SHA-256 of the file, and a separate SHA-256 of the canonical provenance metadata.

Each read recomputes both checksums, checks PDF byte boundary markers, verifies the byte count and refuses to return a record unexpectedly marked verified. A modified byte or metadata field **fails closed**, including the trial evidence ledger and the downloadable scientific review packet. This is a byte-integrity audit, not third-party notarization: a database administrator could still rewrite both data and hashes.

The authenticated trial page displays **Preserved source PDFs**, capture counts, source URLs, hashes and the explicit warning that publisher and scientific contents remain unverified. A reviewer can download a stored PDF using an authenticated same-origin request and a *browser-calculated SHA-256 check* before the file is saved. The key is sent in a header only; no credential is added to a URL, localStorage, sessionStorage, filename or exported dossier. PDFs are returned as attachments with no-store and nosniff headers, not automatically executed as inline page contents.

The existing 20-level JSON dossier now contains PDF metadata and SHA-256 hashes but **never embeds full PDF bytes**. Existing scientific grades, source reconciliation questions and reviewer statements are not changed by the presence of a captured document.

## Disabled by default — explicit source capture

`POST /api/scientific-assessment/source-documents/NCT########` accepts a JSON document containing `gateId`, `sourceUrl`, `sourceType`, lowercase file `sha256`, strict `contentBase64`, and `capturedBy`. The source must already appear as a citation for the **same exact trial and evidence gate** in the preidentified bibliography/worklist or an existing validated source-candidate ledger. A ClinicalTrials.gov URL referring to a *different* NCT is rejected.

For a write, **all** of these must be true:
- Exact isolated Render service ID `srv-dbehn9fb9u1s739ok5vg`, backed by PostgreSQL.
- Valid internal API key and **separate** scientific review write key.
- `PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED=1` **and** `PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED=1`. Both default to disabled for operations that write. Nothing is enabled by this deployment.

Capture accepts only strict base64 submitted PDF bytes, at most 4 MiB per file and 8 files per archived NCT. The PDF must contain its expected header and EOF marker, and its raw SHA-256 must match the curator's declared digest exactly. This lightweight boundary check is **not** exhaustive PDF structure or malware validation. Files are not fetched by the server from arbitrary URLs. Duplicate byte content per trial is rejected; there is no overwrite or delete endpoint. Raw PDF bytes are held within the isolated access-controlled review database, not GitHub.

The underlying byte-read endpoint `GET /api/scientific-assessment/source-documents/{nct_id}/{document_id}` requires the internal key and exact isolated review environment. It returns only bytes verified against both stored content and metadata hashes, with explicit `X-Source-Scientific-Status: not-independently-verified`.

## Scientific interpretation

- **Captured PDF** means a curator supplied these bytes and the system can detect accidental changes.
- **Document authorship independently verified: NO.** URL and file content are not automatically tied to a real publisher.
- **PDF content independently reviewed: NO.** No clinical, statistical or FDA conclusion follows from a checksum.
- **Independent adjudication: NOT IMPLEMENTED.** Reviewers must examine actual source pages and dated versions, record conflicts, verify identities and establish a separate signed two-person decision.
- **Current operation:** No historical source PDF bytes were silently backfilled by deploying this code. The preidentified KEYNOTE-024 PDF links remain **citations only** until a curator explicitly and securely captures their bytes.

Do not store confidential patient data or protected clinical records without a separate privacy/security review. Avoid putting source-document bytes or credentials into GitHub commits, chat messages or unprotected URLs.

## Test coverage and rollback

Offline tests verify default-disabled capture, both authentication layers, isolated Render fencing, exact trial/source gate, non-PDF and over-size rejection, digest mismatch, duplicate handling, byte-for-byte authorized download, tampered metadata, tampered PDF, archive integrity, and no scientific-grade promotion. Chromium tests check browser SHA-256 download verification. The isolated startup diagnostic is `SCIENTIFIC_PDF_ARCHIVE_READBACK`.

The table is additive; this change neither migrates nor replaces trial archives, FS/FA presets, scan schedules, or trading functions. To disable any document writes, leave or restore `PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED=0`. Reading and verifying existing captured bytes remains independently possible with the internal review key.
