# FDA published-letter PDF page sampling — disjoint second batch

**Oct 25, 2026 — draft research only.**

The initial source PDF research sample processed the first **8 distinct** FDA
PDF fingerprints from a pinned set of **122** PDF files. A follow-up
research run selected source fingerprints with sorted indices **8–15**
(zero-based), with an independent private worklist output. The runner fetched
the actual source PDF bytes and required an exact SHA-256 match to the prior
FDA probe; this is **document fidelity**, not review-cycle adjudication.

Official source research [run 40260518347](https://github.com/pdufa/pdufa-command-center/actions/runs/40260518347)
and aggregate [artifact 12623719450](https://github.com/pdufa/pdufa-command-center/actions/runs/40260518347/artifacts/12623719450)
recorded:

| Measure | Batch 1 (indices 0–7) | Batch 2 (indices 8–15) | Combined |
|---|---:|---:|---:|
| PDFs re-downloaded, exact SHA-256 rechecked | 8 | 8 | **16** |
| PDF pages examined | 46 | 54 | **100** |
| Pages without extractable text | 9 | 10 | **19** |
| Candidate application-ID matches | 8 | 8 | **16** |
| Download or parsing failures | 0 | 0 | **0** |

The code accepts an explicit `--offset` and `--limit`, checks boundaries
and chooses unique full-PDF SHA-256s in deterministic sorted order. It includes
a selection fingerprint in each report, and the nonoverlapping second batch
was verified as a different set of PDF fingerprints from the first. It never
publishes specific letter URLs, application IDs, individual source hashes,
or page hints from the private runner directory in the public artifact.

The new pinned machine-readable source observation is
`new-platform/backend/app/research_sources/hop_fda_page_candidate_second_batch_20261025.json`.
Synthetic tests cover nonoverlapping sample windows, unsafe offsets,
excessive sizes, spoofed URLs, source hash mismatches and forged label flags.
The actual source-index regression checks 8 additional PDFs, 54 pages and
their aggregate continuity with the first run.

### What remains

Nineteen PDF pages in the combined 16-file sample have no extractable text
and may be scanned pages, blank pages, or extraction failures. They need
visual examination; missing text is **not** a missing FDA decision. A
candidate application number on a page does not establish whether the
underlying letter concerns an original NDA/BLA application, an amendment,
supplement, withdrawal or rescinded action. Original decision dates and
review cycles require independent page-level adjudication, plus a separate
complete historical approval/nonapproval population and temporal validation.

**Independently adjudicated FDA review cycles: 0. Model-eligible records: 0.
Historical approval rate and predictive accuracy: unavailable.** The work
is in an unmerged draft PR and does not change the production scanner,
GEM JR/GEM FS/FA preset associations, or trading functions.
