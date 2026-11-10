# MAIN Revision 44 — SVRA IMPALA-2 phase-first scientific desk assessment

**Research information cutoff:** 2026-11-09, before the sponsor-announced Nov 22, 2026 FDA target action date. **Trial:** IMPALA-2, [NCT04544293](https://clinicaltrials.gov/study/NCT04544293). **Sponsor:** Savara (SVRA). **Product:** molgramostim inhalation solution, proposed MOLBREEVI. **Indication:** autoimmune pulmonary alveolar proteinosis (aPAP). **Dossier:** `svra-molgramostim`. **Class:** PRELIMINARY SCIENTIFIC DESK REVIEW; NOT INDEPENDENTLY GRADED OR SIGNED; no official FDA decision forecast or numerical certainty.

This additive workpaper follows the source-pinned R42 registry outcomes (posted current registry results section and 1 primary endpoint for this NCT). It has no effect on 29/23 FOCUS source membership, method grades, user-visible production forecasts, immutable review-history events, or retrospective/forward calibration. Its cutoff is explicit for a future predecision comparison, **but it is not a frozen, validated predecision model forecast** because no qualified outcome prediction is made here. Preserve as a research note.

## A. Phase before evidence

The current trial registry identifies exact NCT04544293 as a Phase 3 randomized comparison of once-daily inhaled molgramostim 300 µg versus placebo for aPAP. The primary publication describes a 48-week double-blind period, n=164 randomized (81 molgramostim, 83 placebo), followed by an open-label extension. The prior IMPALA Phase 2/3 study is a **different protocol and population**; do not count the open-label extension or another publication as an independent pivotal Phase 3 replication.

Original source links:
- [Original NCT registry](https://clinicaltrials.gov/study/NCT04544293) (R42 source run #42658620560, pinned exact JSON SHA-256 for 29 NCTs).
- [2025 NEJM primary Phase 3 report](https://www.nejm.org/doi/10.1056/NEJMoa2410542) and [PubMed record PMID 40834301](https://pubmed.ncbi.nlm.nih.gov/40834301/).
- [Sponsor current SEC 2026 Q3 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1160308/000119312526453535/svra-20260930.htm).
- [Sponsor April 15, 2026 FDA-review extension announcement](https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx).
- [Sponsor results exhibit filed with SEC](https://www.sec.gov/Archives/edgar/data/1160308/000119312526008301/d24211dex991.htm).

Phase status is sourced, **not yet independently phase-signed**.

## B. Endpoint-level source observations

| Scientific question | Evidence as reported | Preliminary interpretation (not a grade) |
| --- | --- | --- |
| Primary efficacy, lung gas transfer | At week 24, adjusted DLCO percent-predicted change: 9.8 percentage points molgramostim vs 3.8 placebo; between-arm estimated +6.0 points, 95% CI +2.5 to +9.4, P<0.001 (NEJM) | **Favorable reported primary endpoint**; independently verify complete analysis population, clinical meaningfulness, locked estimator and handling of missing values |
| Week 48 DLCO durability | Mean changes 11.6 vs 4.7, P<0.001 (NEJM; exact comparisons/estimates require source reconciliation) | Supportive **secondary** result, not an additional primary endpoint or independent study |
| Respiratory quality of life SGRQ Total, week 24 | -11.5 vs -4.9, P=0.007 (NEJM); lower is better | Favorable reported secondary with hierarchy-dependent inferential status |
| SGRQ Activity week 24 | Sponsor nominal P=0.0149, but **below the required prespecified hierarchical significance threshold was *not* achieved**; NEJM reports no significant between-group change under the analysis hierarchy | **Critical test gate:** nominal P<0.05 does not mean confirmatory success. Subsequent hierarchical secondary endpoints cannot be called formally significant |
| Exercise capacity / later SGRQ results | Sponsor presents nominal and exploratory numbers after hierarchy break | Research clues only; do not upgrade to confirmatory efficacy |
| Safety | NEJM describes broadly similar proportions with any adverse event or serious adverse event between study groups | SAE denominators, specific events, attribution, prior reports and complete safety updates not yet independently reconciled |

**Mandatory discrepancy explanation:** Sponsor presentations can list SGRQ Activity week-24 nominal P=0.0149 and peak-MET week-48 nominal P=0.0234. They explicitly footnote that these do not pass the prespecified hierarchical testing criterion. The NEJM primary report accordingly does not infer further secondary effects beyond the hierarchy stop. This is not a factual contradiction in P-value reporting; it is a **difference between nominal evidence and multiplicity-controlled inference** that a shallow model must not miss.

## C. Missing independent-method requirements

1. **Prespecification/multiplicity:** obtain the dated original protocol and final locked SAP; reproduce full gatekeeping sequence, boundary thresholds, all testing families, estimands and amendments. The sponsor exhibit describes hierarchical status, not an independent recreation.
2. **Analysis population:** reconcile the 164 randomized persons, ITT/analysis and safety sets, week-24/48 missing-data handling, rescue intervention, protocol deviations and dropouts from full CONSORT and supplementary appendix.
3. **Safety:** retrieve complete AE/SAE tables and original adjudicated narratives, exposure-adjusted denominators, treatment discontinuations and infection assessments, and inspect possible imbalance rather than assuming similar totals imply no individual harm.
4. **Clinical significance:** distinguish improvement in physiological DLCO from direct patient outcomes; verify SGRQ change interpretation and any prespecified clinically meaningful responder endpoint.
5. **Generalizability/independence:** rare-disease small sample (81 vs 83), site variation and prior IMPALA trial population must be separately audited. Open-label extension results lack the randomized placebo comparison after crossing over.
6. **Regulatory application:** sponsor Q3 2026 10-Q says BLA was formally filed in Feb 2026 with Priority Review; April 2026 major-amendment response extended FDA target action to **November 22, 2026**. Sponsor's statement that the extension notice did not cite efficacy/safety/manufacturing concerns is **not FDA confirmation that all such risks are absent**.
7. **CMC/label:** original manufacturing and label review, independent facility status and FDA reviewer documents not obtained in this workpaper. PDUFA date is a target, not evidence of probable approval.
8. **Authorized scientific adjudication:** review-grade method event requires original source version/ingestion receipt, authorized independent reviewer and immutable ledger append. This workpaper creates **no grade**, no regulatory probability, no signoff.

## D. Actionable next assessment slots (still ungraded)

| Research priority | Source status | Missing promotion proof |
| --- | --- | --- |
| Critical: Phase 3 trial identity / primary comparison | Current registry + NEJM publicly reported | Independent phase review, original protocol/SAP and source chronology |
| Critical: primary endpoint statistical validity | Week-24 DLCO original publication reports +6.0, 95% CI 2.5–9.4 | Original analytic set and independent replication |
| Critical: confirmatory secondary hierarchy | NEJM and sponsor SEC exhibit establish **stop at SGRQ Activity** | Full locked hierarchical graph and source-level replay |
| High: safety benefit–risk | Published safety overview | Complete arm counts, events, updated safety |
| High: BLA cycle / CMC / labeling | Sponsor SEC and April announcement | Independent FDA acceptance identity, CMC/label proofs |
| High: clinical generalizability | Baseline study description | Full analysis, subgroups, responder thresholds, deviations |

**R44 research-only directional summary:** published Phase 3 primary lung-transfer efficacy is favorable; the confirmatory secondary sequence has a material statistical stopping point; safety and regulatory/CMC confidence remain insufficiently verified. **FDA decision prediction:** ABSTAIN / NOT_VALIDATED. **Calibration:** NONE. Do not treat this as Level 20 achievement or a signed scientific-method grade.

Current project totals **unchanged**: 29 exact FOCUS trial records, 23 provisional application profiles; 12 current registry result-posting trials, 16 primary tables; 0 approved scientific grades and 0 calibrated FDA forecasts. No preview deployment or database write was performed by this desk assessment.
