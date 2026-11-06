# Expanded authoritative-source recovery — 2026-11-06

## Scope and result

Started from main `9179cece401c5cd0a0d22ca9735d21b796e1ddd5`, reconciled against production (762 trials, 190 columns, 41 met / 7 failed / 3 nonbinary, 14 FDA-linked trials across 6 programs). The original user baseline predates two already-merged batches (#846 and #847); it was not reused as the current baseline.

This batch searched two company IR/science sites (Ionis and Savara), reviewed six issuer release/earnings documents and one scientific presentation, two full protocol/SAP documents, one PubMed abstract and six FDA documents. These counts exclude discovery-calendar pages, registry API batches and repeated URL checks. All 762 exact-NCT registry records were refreshed. Source validation and transport blockers are preserved in `phase3ExpandedSourceValidation20261106.json`.

The four screenshot avenues (BiopharmaWatch, FDA Tracker, Assyro, CheckRare) were read as discovery sources. No third-party calendar probability or unverified calendar outcome was imported. FDA Tracker enhanced content requires authentication. PMC full text encountered a CAPTCHA; the accessible PubMed abstract and official issuer/FDA sources provided alternatives. Several shell HTTP 403/503 responses were readable through the web reader; both access paths are recorded.

## Batch measurements

| Measurement | Result |
|---|---:|
| Companies searched in targeted IR batch | 2 |
| Issuer documents reviewed | 7 |
| Registry records recovered | 762 |
| Export trial rows newly enriched | 759 |
| Newly adjudicated endpoints | 5 PASS / 1 FAIL / 0 nonbinary |
| New normalized IR assessment records | 43 (42 documented facts, 1 interpretation flag) |
| New registered eligibility/geography facts | 1,488 |
| FDA-linked trial records | +6; cumulative 20 |
| Distinct linked FDA programs | +5; cumulative 11 |
| New numerical predictions | 0; cumulative 4 trials / 61 question slots |
| Endpoint totals | 46 met / 8 failed / 3 nonbinary |
| Unadjudicated endpoints remaining | 705 |
| Unscored assessment slots | 13,144 (previously 14,648) |
| Pending research including documented design interpretation | 14,621 |

BALANCE's 80 mg primary success preserves the failed 50 mg comparison and limits confirmatory secondary claims under the protocol hierarchy. CARDIO-TTRansform remains a failed primary endpoint despite a separate polyneuropathy approval for eplontersen. NEURO-TTRansform uses an external historical comparator. CORE and CORE2 retain separate trial-specific figures; pooled pancreatitis/safety findings are not assigned to individual trials. Savara's November 22, 2026 target is an issuer/SEC-reported extension as of the August disclosure; later FDA correspondence was not independently verified.

Protocol nominal dates and public-upload dates are stored separately. BALANCE/OASIS protocols became publicly posted in February 2025, after the reported readouts; they are historical documentation, not evidence available for a pre-readout prediction. Month-only FDA label dates retain month precision. Existing forecasts, RAAS calibration, Pipeline, and inactive GEM/GEM JR state are preserved.

Registry eligibility and listed sites document planned design, not actual participant demographics, recruitment, representativeness or adequate generalizability. Of the selected export facts, 1,477 therefore continue to require critical interpretation. The 762 raw records include trials whose richer pre-existing facts or frozen forecasts take precedence in the export. Zero documentary gaps for Q06 does not imply completed generalizability assessment.

## Question-level coverage

New facts below count persisted source records before export precedence; interpretation flags are excluded. Verified facts and observed outcomes overlap intentionally. Research includes remaining interpretation of registered design. Numerical entries remain exclusively the saved forecasts. No absence of a source has been reclassified as genuinely unavailable.

| Question | New facts | Verified facts | Numerical | Observed | Research pending | Not publicly available |
|---|---:|---:|---:|---:|---:|---:|
| Q01 | 6 | 357 | 4 | 57 | 401 | 0 |
| Q02 | 0 | 11 | 4 | 0 | 747 | 0 |
| Q03 | 3 | 363 | 4 | 0 | 395 | 0 |
| Q04 | 2 | 3 | 4 | 0 | 755 | 0 |
| Q05 | 1 | 3 | 4 | 0 | 755 | 0 |
| Q06 | 762 | 758 | 4 | 0 | 755 | 0 |
| Q07 | 0 | 755 | 1 | 0 | 6 | 0 |
| Q08 | 0 | 750 | 1 | 0 | 11 | 0 |
| Q09 | 0 | 760 | 1 | 0 | 1 | 0 |
| Q10 | 0 | 760 | 1 | 0 | 1 | 0 |
| Q11 | 2 | 601 | 1 | 0 | 160 | 0 |
| Q12 | 0 | 760 | 1 | 0 | 1 | 0 |
| Q13 | 2 | 3 | 1 | 0 | 758 | 0 |
| Q14 | 2 | 3 | 1 | 0 | 758 | 0 |
| Q15 | 2 | 2 | 1 | 0 | 759 | 0 |
| Q16 | 0 | 0 | 4 | 0 | 758 | 0 |
| Q17 | 2 | 613 | 4 | 0 | 145 | 0 |
| Q18 | 2 | 77 | 3 | 0 | 682 | 0 |
| Q19 | 1 | 2 | 3 | 0 | 757 | 0 |
| Q20 | 0 | 0 | 1 | 0 | 761 | 0 |
| Q21 | 1 | 3 | 1 | 0 | 758 | 0 |
| Q22 | 0 | 269 | 1 | 0 | 492 | 0 |
| Q23 | 2 | 306 | 1 | 0 | 455 | 0 |
| Q24 | 1 | 273 | 4 | 0 | 485 | 0 |
| Q25 | 0 | 761 | 1 | 0 | 0 | 0 |
| Q26 | 726 | 725 | 1 | 0 | 758 | 0 |
| Q27 | 0 | 356 | 1 | 0 | 405 | 0 |
| Q28 | 1 | 3 | 1 | 0 | 758 | 0 |
| Q29 | 6 | 358 | 1 | 57 | 403 | 0 |
| Q30 | 6 | 20 | 1 | 0 | 741 | 0 |

## Resumption and validation

`recover_phase3_population_geography.py` saves incremental batches, retries transport failures, verifies exact requested identities, records API batch URLs/content hashes, and resumes successful records. Refresh is explicit. `recover_phase3_ionis_savara_20261106.py` is idempotent. The company research queue and live company coverage retain unmatched trials and further investigation; registry matching is distinct from completed IR research.

Frontend full suite: 1,247 tests passed. Final focused route/CSV and provenance checks, TypeScript and production build passed. The first sandboxed build failed to parse TypeScript subprocess output; a network-enabled retry completed successfully. Three Python collector tests passed. Actual-route CSV validation checks all 762 unique identities, every 190-column row, all 30 question totals, no duplicate adjudications, and unchanged numerical prediction counts. URL validation is transport-specific and does not claim that a successful URL alone proves trial identity.

This is an incremental completed batch. Authoritative evidence discovery is not exhausted: 705 endpoints and substantial question-level scientific research remain. The resumed queue must continue through company disclosures, results-posted registries, publications and FDA records without treating unreviewed documents as confirmed facts.
