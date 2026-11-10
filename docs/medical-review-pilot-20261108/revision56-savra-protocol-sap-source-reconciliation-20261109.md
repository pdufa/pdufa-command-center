# MAIN R56 — Savara IMPALA-2 exact-source protocol/SAP review exceptions

Observed November 9, 2026. Draft PR #965, independent current-FOCUS Track A. **Not a clinical reviewer signoff or FDA outcome forecast.**

## Immutable source evidence and actual run

[Completed GitHub Actions source verification #42698835077](https://github.com/pdufa/pdufa-command-center/actions/runs/42698835077) **SUCCESS**; 14 synthetic source-integrity/safety tests pass, retired-system audit passes. Original two public trial PDF source binaries were restored from [R53/R54/R55 exact original research archive #13710081166](https://github.com/pdufa/pdufa-command-center/actions/runs/42696796318/artifacts/13710081166), not downloaded from an unverified third party.

Current source:
- NCT04544293, Savara molgramostim trial SAV006-05, linked to provisional application `svra-molgramostim`.
- [Current ClinicalTrials.gov attached protocol v10.0, document date 2024-10-09](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf), exact SHA-256 `0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849`, 134 PDF pages.
- [Current ClinicalTrials.gov attached SAP v1.0, document date 2024-04-24](https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf), exact SHA-256 `2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888`, 89 PDF pages.
- Actual output [R56 page-cited review queue artifact 13710841464](https://github.com/pdufa/pdufa-command-center/actions/runs/42698835077/artifacts/13710841464), expires 2027-02-07; JSON file `SVRA_ORIGINAL_PROTOCOL_SAP_RECONCILIATION_R56.json`, research receipt SHA `78344f41e53e6ff9fb3fd13115caa1d740d0185832e9badde280204cd7d7b0ac`.

## Source-verifiable review findings — not statistical conclusions

Ten page-linked review leads; **six explicit or apparent reconciliation issues**:

| ID | Observed source pages (one-based physical PDF) | Reason for subsequent scientific review |
| --- | --- | --- |
| DLCO_MANEUVER_AVERAGING_RULE | Protocol PDF p.51, SAP pp.12 and 65 | Protocol describes mean of **two best efforts**, SAP describes mean of **all acceptable efforts**; SAP itself calls this out. Check original overreader rules and validation before assessing impact. |
| MULTIPLICITY_SCHEMATIC_AND_HOCHBERG | Protocol p.70, SAP pp.25 and 65 | Both describe type-I error control and alpha splitting; SAP specifically says hypothesis-testing schematic and alpha labels required correction. Verify exact hypothesis graph and prespecified sequence, not just keyword agreement. |
| SAFETY_ADR_VS_TREATMENT_RELATED_AE | SAP p.65 | SAP explicitly changes reporting from serious ADRs to serious treatment-related AEs; confirm definitions and safety coding across protocol amendments, exposure periods, and FDA safety review. |
| EQ5D_INDEX_VS_DOMAIN_SUMMARIES | SAP p.65 | SAP describes replacing EQ-5D index/5-digit health-state summary with individual domains; this is a reporting-method change, not proof of primary endpoint failure. |
| HOSPITALIZATION_EXPLORATORY_ENDPOINT_REMOVED | SAP p.65 | SAP documents removal of the hospitalizations exploratory endpoint; confirm study amendment governance and where disclosures occur. |
| OXYGEN_REST_DURATION_ASSUMPTION | SAP p.65 | SAP states a change to assumed rest time for daily oxygen-use derivation; review derivation/recorded sources. |

Three additional alignment leads are indexed (full/safety analysis populations, primary Week 24 DLCO model, control-based missing-data imputation) with physical page citations. The tenth item flags document chronology: protocol PDF v10 dated **later** than current attached SAP v1 (protocol p.2 and SAP p.1). **Neither printed document date establishes when that version became public or when blinded data were locked and treatment codes unblinded.** An apparent rule discrepancy can be corrected or adjudicated only after original prior versions, amendments, protocol-deviation logs and signed SAP evidence are located.

## Engineering validation and protections

Added:
- `new-platform/backend/scripts/reconcile_svra_original_protocol_sap_r56.py`
- `new-platform/backend/tests/test_svra_protocol_sap_reconciliation_r56.py`
- `.github/workflows/main-r56-svra-protocol-sap-review.yml`

The workflow is read-only on the draft feature branch. It restores the pinned successful original R53/R54/R55 source artifact, recomputes SHA-256 on both full PDFs, verifies their current registry document-date receipts, requires exact public URLs/NCT and 29/23 source membership, then checks each review phrase against the page stated in the PDF. An absent or changed source quote FAILS the run instead of fabricating a conclusion. The initial CI test caught a local archive filename-versus-public-filename mismatch, which was fixed; final independent run #42698835077 passed all 14 targeted tests and generated the review artifact.

No signed efficacy or benefit-risk findings, model training, clinical grade writes, FDA probability, forecast promotion, production mutation or historical accuracy calculation. **Independently validated application predictions: 0/23; historic independent blind backtests: 0.**

## Next evidence/clinical analysis work

1. For Savara, retrieve authenticated earlier protocol/SAP versions and first-public dates; reconcile the two-versus-all DLCO rule and multiple-testing schematic with the original readout and FDA filing evidence.
2. Independently review Week 24 primary estimand, actual test statistic, statistical-method implementation, secondary gating, MMRM sensitivity checks and clinical importance, then AE arm denominators, seriousness and discontinuations. Record reviewer decisions only with document/time stamps and confidence/unknowns.
3. Extend the same source-anchored contradiction workflow to the other 11 NCTs with current attached PDFs and all 23 application packets. For the remaining 17 trials, source recovery needs alternate legitimate publication/regulatory materials.
4. In parallel, build unbiased consecutive historical original NDA/BLA filing cycles and time-frozen predecision evidence for real blind FDA action backtesting, before any measured accuracy or calibration claim.

Daily schedule still **not live on main**, draft PR not merged, and independent historical Track B remains separate.
