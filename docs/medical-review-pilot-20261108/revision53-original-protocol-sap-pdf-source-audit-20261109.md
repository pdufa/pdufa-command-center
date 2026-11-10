# MAIN Revision 53 — Original current public protocol/SAP PDF evidence audit

Date: November 9, 2026. Draft PR #965, branch `feature/medical-stage4-verified-method-matrix-20261108`.

## Verified original public PDF results

[Final exact-source GitHub Actions run 42692763297](https://github.com/pdufa/pdufa-command-center/actions/runs/42692763297) **SUCCESS**. The original ClinicalTrials.gov current registry records for all **29 exact NCTs** were retrieved and their document fields were independently re-extracted from SHA-verified raw registry bytes. **23/23 PDFs were retrieved and passed exact byte SHA-256 and PDF-content checks**, including:
- 12 files carrying current study protocol content;
- 12 files carrying current statistical analysis plan content;
- 23 files total, because one file is a combined protocol/SAP;
- the attachments cover **12 of 29** currently indexed NCT records and map to the original **23 provisional application dossiers**. The remaining 17 registry records have no currently attached protocol/SAP here; other public/issuer sources may exist.

**Unmodified original registry responses, downloaded PDF binary bytes and page-linked keyword excerpts** are archived in [GitHub Actions artifact 13707049183](https://github.com/pdufa/pdufa-command-center/actions/runs/42692763297/artifacts/13707049183), expiring 2027-02-07. The first capture (#42692337663) verified 22/23; combined NCT04716231 `Prot_SAP_000.pdf` exceeded the initial 25MB collector limit. The limit was increased to a bounded 55MB without weakening SHA checks, then final capture verified **23/23**. Do not interpret earlier missing data as trial failure.

## Priority original source scientific review lead — Savara IMPALA-2

The exact official current record's linked original PDFs, both archived and byte-verified, are:
- [NCT04544293 protocol, `Prot_000.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf): title-page version 10.0 dated **October 9, 2024**, 134 PDF pages. PDF pages ~68–70 discuss the Week 24 DLCO primary endpoint, primary-analysis population and type-I error considerations. The protocol indicates the SAP should be finalized before final database lock and subsequent unblinding.
- [NCT04544293 SAP, `SAP_001.pdf`](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf): version 1.0 document heading dated **April 24, 2024**, 89 PDF pages. PDF pages ~25–27 describe Week 24 adjusted percent-predicted DLCO primary testing, a sequential testing and alpha-splitting hierarchy, Hochberg secondary-family methods, including regional adaptations, and further secondary endpoints. Its interim-analysis and protocol-departure sections remain review items.

These are **PDF document headings and current public source text**, not independently verified first-public dates, originally signed and unblinded-data-protected versions, or a concluded SAP/protocol consistency review. A document-dated SAP precedes the later cited protocol version; only a detailed amendment chain can adjudicate which specifications were prospective at trial readout. No efficacy/CMC or FDA decision conclusion is made.

## Protected workflow and limitations

Implementation:
- `new-platform/backend/scripts/collect_focus_protocol_pdf_text_r53.py`
- `new-platform/backend/tests/test_focus_protocol_pdf_text_r53.py`
- `.github/workflows/main-r53-focus-public-protocol-sap-pdf.yml`

The collector permits **only exact filenames and NCTs in the independently re-extracted original registry record**, only public `cdn.clinicaltrials.gov/large-docs/...` HTTPS PDFs, bounded file sizes and pages, no unverified redirects, SHA and byte-count checks before parsing, no duplicate NCT IDs, and no production/model/reviewer writes. PDF sections are page-anchored **search leads**, not validated efficacy or statistical interpretation.

The source-only workflow is on a **draft feature branch**, not default-branch scheduled production. Other independent Track A/B research workflows are unchanged.

Current standing: **29 trial research rows, 23 application dossiers, 23 verified current protocol/SAP PDF binaries, 0 independently verified locked pre-readout SAPs, 0 signed scientific grades, 0 validated FDA forecasts, 0 real independent historical backtests, measured accuracy unavailable**. Train/predict/release remain BLOCKED. This cannot guarantee any 100% prediction accuracy.

## Next scientific work

1. Reconstruct original prospectively available protocol/SAP *version histories* and exact public chronology; prioritize SVRA, CAPR and COGT. R52 internal history API returned HTTP 403 and should not be retried as a bypass; source alternatives include standard public record-history UI captures and dated issuer/regulatory publications.
2. Independently reconcile pivotal Week 24 and secondary effect estimates, primary/secondary hierarchy, family-wise multiplicity, intercurrent event/missing-data methods, original amendments and safety exposure by treatment arms with page-cited signed versions; produce documented review exceptions, not unverified grades.
3. Independently build consecutive historic original NDA/BLA filing-cycle census including unapproved, withdrawn/pending and repeat reviews; source-label separated original predecision evidence and blinded holdouts before any real prediction-versus-outcome accuracy measure.

