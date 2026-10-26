# Historical FDA PDF evidence leads for original-application research

**Date:** October 25, 2026 · **Status:** Quarantined source-research data, not validated FDA decision outcomes.

The original NDA/BLA research program previously identified **101 evidence-search packets**: 84 groups for distinct unresolved FDA application IDs, plus 17 identity-ambiguous letter references. In total they cover 124 selectively published FDA letters. Those packets were private to the read-only FDA research workflow.

## Actual original-source PDF link reconciliation

Using the frozen 2026-10-21 published FDA CRL archive and an earlier
FDA PDF-byte probe from [source run 40232393298](https://github.com/pdufa/pdufa-command-center/actions/runs/40232393298), the research-only workflow
[40256743054](https://github.com/pdufa/pdufa-command-center/actions/runs/40256743054)
cross-linked the 101 private research packets by **exact SHA-256 of the original published letter row** to the older **official FDA document URL and full PDF SHA-256**. PDF files were **not fetched or rehashed again in this new step**.

| PDF lead coverage | Real research result |
|---|---:|
| Source-research packets covered | **101** |
| Packets whose every published letter has a previous PDF-byte check | **100** |
| Packets with no released or usable PDF | **1** |
| Partially linked packets | **0** |
| Published FDA letter references included | **124** |
| Referenced letters with previously confirmed PDF bytes | **123** |
| Referenced letters without a PDF lead | **1** |
| **Distinct prior-confirmed PDF files within these packets** | **122** |
| Full-PDF digests shared between multiple letter references | **1** |

The earlier, full FDA source PDF audit had **457/458** letter references with confirmed official PDF bytes and **364 distinct PDFs**. It is expected that the research packets use only a subset of that archive. The missing filename/source may not be inferred from the application number or document type; it remains pending document/source review. **One shared PDF in the packet subset cannot be assumed to represent one or two original FDA actions without inspecting and independently attributing its pages.**

## Files and source integrity

The new `app/hop_fda_prior_pdf_lead_join.py` and `scripts/enrich_hop_fda_private_pdf_leads.py` cross-check:

- Pinned official published CRL source-archive SHA-256, record count and PDF archive version
- All **458 source-row hashes**, **457 prior confirmed PDF links**, and **364 distinct full-document fingerprints** across the original audit corpus
- Official `download.open.fda.gov/crl/` links constructed **only** from previously published, validated filenames (never guessed)
- Exact source record identity and **one-to-one ownership** by the 101 private packets; repeated-letter PDFs retain source provenance
- Mandatory `model_eligible=false`, independent-review=false, unresolved review cycles, and null probabilities

The resulting enriched worklist remains in the **private CI runner directory**. It associates each selected FDA letter source hash with its historically observed official URL, document SHA-256 and original published metadata. The private per-letter links and packet mapping are **not uploaded**. Only the aggregate JSON is published in [research run artifact 12622846842](https://github.com/pdufa/pdufa-command-center/actions/runs/40256743054/artifacts/12622846842).

The resulting committed **aggregate**, without letter-level records, is `app/research_sources/hop_fda_prior_pdf_lead_coverage_20261025.json`. Real and synthetic regression tests pin coverage counts and check that changed digests, forged FDA hosts, repeated source IDs and claimed FDA approvals cannot be accepted.

The historical prior PDF-probe GitHub artifact has limited retention, so it should be treated as a time-limited reproducibility dependency until safely archived according to the project backup policy. Having a byte digest does **not** prove that the full original action-letter content has been independently adjudicated.

## Next scientific gate

Qualified independent reviewers need to check original document pages, effective FDA action dates, actual application and original-versus-supplement identity, and review-cycle chronology for each source. Separately construct a **complete NDA/BLA approval and nonapproval population** (not the selectively published CRL archive), reconcile all original actions with the predecision evidence cutoff, and validate a temporal held-out model. No approval rates, scientific probability estimates or retrospective accuracy may be calculated from these packets as-is.

**Verified original FDA review-cycle outcome labels: 0. Model-eligible records: 0. Prediction probability: unavailable.** Research draft only; existing GEM JR/GEM FS/FA presets, production scanners and trading functionality unchanged.
