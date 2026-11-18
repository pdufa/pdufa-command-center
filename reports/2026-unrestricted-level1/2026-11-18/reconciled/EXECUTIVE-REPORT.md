# 2026 PDUFA Level 1 assessment checkpoint

**November 18, 2026. Full-year reconciliation remains open.** The unrestricted worklist spans January through December and includes private and public companies across market capitalizations. The 196 estimate is provisional. Public FDA action files do not enumerate every review goal, and the calendar year remains open.

| Measure | Count |
| --- | ---: |
| Pinned baseline rows recovered | 96 of 96 |
| Integrated worklist records | 99 |
| Verified 2026 cycles | 66 |
| Unresolved in-scope leads | 30 |
| Duplicate worklist records | 0 |
| Outside cohort | 3 |
| Verified cycles with a Level 1 assessment and documented gaps | 66 |
| Verified cycles with every requested field populated | 0 |
| Verified cycles with phase, trial ID, endpoint, effect size, statistical analysis and safety fields populated | 41 |
| Outcome-aware retrospective assessments | 64 |
| Frozen prospective assessments | 2 |
| Eligible blind Level 1 comparisons | 0 |
| Historical blind accuracy | Unavailable |

The 59 inherited leads now comprise 27 verified, 30 blocked and two excluded. Post-recovery work promoted lirafugratinib, garetosmab, brepocitinib and oveporexton, excluded enlicitide from the 2026 goal cohort, and confirmed supplement numbers for the still-blocked Ultomiris and Inluriyo leads. [Lead ledger](lead-reconciliation.csv) · [Original recovery artifact](../reconciliation-recovery.json)

Lirafugratinib retains the original September 27 and later September 25 sponsor-reported targets. FDA approved it September 23. The FDA document explaining the discrepancy remains unavailable. Enlicitide has a February 2027 goal and a July 2026 approval. Oveporexton has a recorded August FDA action and a November DEA scheduling publication that governs the statutory approval date. [Original sponsor disclosure](https://elevartx.com/2026/03/30/elevar-fda-acceptance-lira/) · [Later sponsor disclosure](https://elevartx.com/2026/09/22/elevar-conditional-acceptance-lyrfigtu/) · [Enlicitide FDA review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220848Orig1s000RiskR.pdf) · [Oveporexton FDA letter](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220860Orig1s000Approv.pdf)

The follow-up resolved two calendar placeholders. FDA review packages establish August 29 for rusfertide, approved August 28, and September 25 for tavapadon, approved the same day. FDA labels also supplied pivotal evidence for Afrezza and Vyvgart. The Afrezza label confirms the pediatric noninferiority endpoint was missed, so the outcome-aware assessment is INDETERMINATE despite the known approval. Merck confirmed the ifinatamab deruxtecan BLA withdrawal. Its exact application number remains unresolved. FDA labeling identifies the Rhapsido supplement. Its exact PDUFA date remains unresolved. [Rusfertide review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220605Orig1s000RiskR.pdf) · [Tavapadon review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/220415Orig1s000RiskR.pdf) · [Afrezza label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/022472s029lbl.pdf) · [Vyvgart label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/761195s016lbl761304s018lbl.pdf) · [Merck withdrawal](https://www.merck.com/news/ifinatamab-deruxtecan-biologics-license-application-for-certain-patients-with-previously-treated-extensive-stage-small-cell-lung-cancer-voluntarily-withdrawn/)

No verified cycle lacks a recorded judgment. All 66 have a documented evidence or calibration gap. The export contains 21 verified cycles without a trial ID (two not applicable to the specific assessment and 19 unresolved) and 16 without a populated statistical-analysis field. These counts overlap.

The 66 verified cycles comprise 57 approvals, seven complete responses and two pending decisions. Clinical field counts can include explicit limitations. Numerical confidence remains blank because the cohort has no validated calibration. [Coverage](coverage.json) · [Row-level blockers](blocker-manifest.json)

Resume with the 30 rows in the blocker manifest. Crosswalk pending applications to an exact FDA docket and obtain original acceptance or amendment disclosures for decisions with unknown goals. Revisit the unjoined FDA action and CRL records in a dated year-end refresh. [FDA submission crosswalk](../fda-submission-status-crosswalk.csv) · [FDA CRL crosswalk](../fda-crl-letter-crosswalk.csv)

- [Assessment CSV](assessments.csv) and [assessment JSON](assessments.json)
- [Lead reconciliation CSV](lead-reconciliation.csv) and [lead reconciliation JSON](lead-reconciliation.json)
- [Completion manifest](completion-manifest.json)
- [Historical accuracy report](HISTORICAL-ACCURACY.md)
- [Interface compatibility report](INTERFACE-COMPATIBILITY.md)
- [Test report](TEST-REPORT.md)

FDA labeling added exact trial identities, numerical efficacy, statistical analysis and safety findings for olezarsen and sotatercept. The assessments remain outcome-aware. [Olezarsen label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/218614s004lbl.pdf) · [Sotatercept label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/761363s012s016s017lbl.pdf)


## Evidence and reconciliation recheck

The current Drugs@FDA download had the same SHA-256 digest as the prior archive. The ledger records 57 individual URL checks across the 30 unresolved leads and the shared FDA archive check. Two URL fetches timed out. All 30 rows retain explicit unresolved reasons. The FDA archive identifies the Truqap CAPItello-281 approval as NDA 218197/S-004 and the first-line Jaypirca approval as NDA 216059/S-006. The exact goals remain unverified. The Pimjetmi FDA novel-approvals index and application action record carry different dates, which remain visible in the ledger. None of the rechecks established a new fully verified application cycle. [Reconciliation ledger](lead-reconciliation.json)

FDA labeling supplied exact trial IDs for 13 previously missing events and filled six previously empty statistical-analysis fields. Two separate-pivotal-trial fields are marked NOT_APPLICABLE with bridging or device-supplement explanations. The two frozen prospective assessments and their cutoffs are unchanged. The 66 verified records now have an explicit NOT_CALIBRATED status. [Assessment JSON](assessments.json) · [Coverage](coverage.json)
