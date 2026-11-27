# FDA pages with no extractable text — private visual review preparation

**October 25, 2026. Research-only, unmerged draft. Not an independent FDA regulatory decision review.**

The first two FDA published-letter PDF research samples included **16 distinct
hash-confirmed PDFs and 100 pages**, of which **19** returned no text through
the bounded pypdf extractor. A page without extractable text may be blank,
scanned, image-only, or nonstandard embedded PDF text. It cannot be taken as
missing FDA evidence, approval or nonapproval, and an OCR result would still
require visual verification.

This follow-up adds a **private PNG renderer** for those exact page numbers
in the *already source-hash-verified* research PDFs. It is limited to the two
previously selected eight-PDF batches (hash-sorted indices 0–7 and 8–15).

`app/hop_fda_pdf_page_candidate_sampling.py` now preserves the zero-based
no-text page indices in its **private** observation records. The isolated
research script `sample_hop_fda_published_letter_page_hints.py` uses
`app/hop_fda_visual_page_review.py` and PyMuPDF to render just those pages
as bounded PNG images when explicitly given a private target directory and
private manifest path. The prior entire-PDF SHA-256 must match the newly
fetched actual PDF bytes, and the PDF renderer's page count must match the
recorded count. Page indices are validated and deduplicated; oversized
images and malicious or inconsistent source metadata terminate the audit.

Each private manifest row records the immutable original PDF SHA-256,
zero-based page index, PNG file name, PNG SHA-256, raster dimensions,
and **human visual review completed = false**. It never sets FDA
original-decision-page verification or model eligibility.

**Privacy and access limitation:** the PNGs and detailed page mappings
are saved solely under
`runner.temp/.../private_original_tables/no_text_visual_images/`.
The only uploaded GitHub Actions artifact is
`public_aggregate_only/`, containing page render totals and scientific
quarantine flags. Private rendered images are **ephemeral CI files** and are
not automatically delivered to human reviewers or preserved as durable
review evidence. A separate access-controlled reviewer transfer procedure
would be needed before real human review.

The public count-only report can show how many no-text pages were found,
rendered and unable to render. This reports **image preparation**, not
human visual inspection, OCR, identification of an original action page,
FDA review-cycle outcome, trial evidence accuracy, or prediction readiness.

Reviewers will still need source-correct original FDA action pages,
proper independent identity verification, the complete NDA/BLA original
approval and nonapproval decision cohort, and point-in-time validation of
scientific predictor inputs. Do not count text-empty or visually rendered
pages as verified decisions.

**Gate remains:** independently adjudicated review cycles = 0;
model-eligible outcome records = 0; approval rates, probabilities and
predictive accuracy unavailable. Production, scanner jobs, GEM JR/GEM
FS/FA preset associations and trading remain unchanged.


## Actual source-rendering results

The real read-only
[workflow 40262315333](https://github.com/pdufa/pdufa-command-center/actions/runs/40262315333)
passed and emitted
[aggregate artifact 12625061538](https://github.com/pdufa/pdufa-command-center/actions/runs/40262315333/artifacts/12625061538).
Of the two nonoverlapping eight-PDF samples, all **16 exact-source-hash
checks passed**. All **19/19** pages without extractable text (nine in
batch 1 and ten in batch 2) were successfully rendered into **private PNG
bitmaps**, with **zero rendering failures**. The full sample examined
100 PDF pages. The PNG/image SHA-256 and page mapping manifest stayed in
private CI runner files and was not included in the aggregate artifact.

The source aggregate is pinned as
`app/research_sources/hop_fda_nontext_page_visual_render_20261025.json`.
Synthetic PDF tests validate pixel boundaries, real PNG output, source
file hash and page-index locks; a pinned-count regression checks both
actual FDA eight-document samples.

**Limits:** Bitmap creation is not visual reading. Because the private
runner files are ephemeral and deliberately excluded from artifacts, an
authenticated reviewer cannot yet retrieve these PNGs from this run.
Durable controlled review access and independent human page reading remain
unbuilt/unperformed. We do not claim that blank/unextractable pages contain
FDA actions or that any FDA approval/nonapproval outcome has been adjudicated.
