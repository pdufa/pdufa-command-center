# FDA original-source byte provenance — observed 2026-10-28

**Real source retrieval was performed successfully**, using the read-only,
no-redirect GitHub Actions source-capture job in
[run 40716416188](https://github.com/pdufa/pdufa-command-center/actions/runs/40716416188).
Both original FDA URLs returned HTTP 200 with the expected PDF media type.
The original downloaded PDF bytes were retained **temporarily** in the
14-day [GitHub Actions research artifact](https://github.com/pdufa/pdufa-command-center/actions/runs/40716416188/artifacts/12828286739).
The source ZIP was subsequently downloaded into the ChatGPT tool container
and all three SHA-256 hashes were recomputed directly from those bytes.

## Real captured original PDF fingerprints

| Original document | Bytes | Pages | SHA-256 |
| --- | ---: | ---: | --- |
| NDA 213973 QINLOCK/ripretinib signed **APPROVAL** 2020-05-15, FDA ref 4609421 | 768,468 | 8 | `5c559425eddb609ab8c2c2545413860947ca0f30e9a937fd81eca502dba4626e` |
| BLA 761303/Original 1 odronextamab signed **CRL** 2024-03-22, FDA ref 5352252 | 168,170 | 7 | `394bc0667eb2704b34fbb40046e068b0c087e07865dd89658ef4f2f858c8f880` |

The complete artifact ZIP SHA-256, independently recomputed, is
`765dc93ca2fafa048dceb2d48221d00b74eaa909cbc24b3c570a33d6ca7060eb`.

The SHA-256 of the two extracted PDF blobs exactly matches the captured
provenance JSON and workflow logs. The first pages, FDA reference IDs,
document action headings and electronic signature dates were inspected.
The odronextamab CRL's **first PDF page is image-only for text extraction**;
it was rendered and visually inspected, rather than incorrectly assumed
to have searchable first-page text. Later CRL pages and signature text
were machine-extractable. These checks establish source-content identity,
**not qualified independent FDA cycle adjudication**.

## Three dates must stay distinct

1. FDA document **signed/action date:** May 15 2020 or March 22 2024.
2. Publisher-reported **public outcome announcement:** May 15 2020
   (FDA/Deciphera), or March 25 2024 (Regeneron).
3. **First public availability of the FDA PDF bytes:** still unknown.

The observed HTTP Last-Modified headers on October 28, 2026 were
`Tue, 19 May 2020 12:25:55 GMT` for ripretinib and
`Sun, 25 Oct 2026 16:42:34 GMT` for odronextamab. **Neither header is
an independently verified first-publication date.** Do not treat the
recent 2026 modification time of the CRL archive as if it had been
publicly available before the March 2024 decision, and do not treat
the May 2020 modification of the approval PDF as evidence of its first
publication.

The source audit register is
`new-platform/backend/app/research_sources/hop_fda_original_byte_capture_receipts.json`;
its validator is `hop_fda_original_capture_receipts.py`. The
authenticated read-only `GET /api/internal/hop/public-outcome-disclosures`
now includes source PDF byte fingerprints in
`originalPdfCaptureResearch`. No raw PDF bytes are served by that API.

The optional offline
`verify_source_artifact_zip(archive_bytes, receipts)` verifies actual ZIP,
PDF, source URL and provenance JSON bytes against the committed SHA values.
The runtime receipt register alone validates **metadata structure only**;
a plausible but false hash is not independently authenticated until the
matching original artifact is read and hashed.

## Remaining prediction-critical work

- Obtain durable authorized archival storage beyond the temporary
  14-day GitHub artifact (the artifact may expire or be removed earlier
  under repository policies).
- Independent qualified reviewer reconciliation of each **exact FDA
  submission/review cycle**, original and revised PDUFA target dates
  and full application history.
- Verify first-public decision-label time, separate from signature,
  later PDF publication or disclosure-page timestamp.
- Construct a prespecified **complete FDA cohort denominator** with both
  approvals and nonapprovals, withdrawals and delays, and preserve an
  untouched, related-program-disjoint test partition.
- Reconstruct frozen predecision science/clinical information so the FDA
  action cannot leak into model features.

**Model eligibility remains 0; independently backtested real cases 0;
calibration and actual FDA PASS/FAIL accuracy are not measurable.**
The receipts do not enable scanner scheduling, sheets, database mutations
or trading.
