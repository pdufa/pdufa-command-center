# MAIN Phase-first source audit — revision 4: EU protocol discovery and jurisdiction reconciliation

**Date:** 2026-11-08 UTC  
**Exact trial identity:** NCT06081894 ↔ EU CT 2023-505797-15-00 ↔ Cytokinetics protocol CY 6033, ACACIA-HCM (aficamten, symptomatic nonobstructive HCM).  
**Record state:** RESEARCH_SOURCE_DISCOVERY_ONLY. No independent phase verification, method grades, reviewer signoff or regulatory forecast is claimed. This is additive to [revision 1 receipts](./receipts.json), [revision 2 Phase III handoff](./phase3-reviewer-handoff-revision2-20261108.md) and [revision 3 safety audit](./source-reconciliation-revision3-20261108.md).

## Confirmed location of a publicly listed Phase III protocol

- **Official EU CTIS trial listing:** https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en — European Medicines Agency public portal. The page matches both the sponsor, protocol code CY 6033 and indication, and records the application as therapeutic confirmatory / **Phase III**.
- **Cross-checked public document index:** https://ctis.eu/trial/2023-505797-15-00 — independently operated index of EU CTIS data (not the EMA). It lists 133 public trial documents, including `D1_2023-505797-15-00_Protocol_FP` (listed version AM4), `D1_2023-505797-15-00_Protocol_el_FP` (listed version AM4), `D1_2023-505797-15-00_Protocol_add_A_FP` (version A), and a protocol synopsis (AM3). The public index dates the AM4 posting to **March 9–10, 2026**, linked to a substantial-modification decision; prior AM3 and AM02 EU versions are indicated in its historical record.
- **Official PDF retrieval status:** **NOT OBTAINED / NOT CONTENT-VERIFIED.** The direct official CTIS public JSON endpoint could not be accessed using the current research tool; the file names are confirmed as listings, not personally downloaded, hashed, read or independently validated protocol contents. It is **not** established that the public AM4 protocol has the final locked pivotal statistical analysis plan (SAP). Do not promote a file listing to a verified source report.
- **EMA public document access:** On the official trial listing, use **Trial Documents** and locate the above `D1` protocol, or the public **Download clinical trial** facility if available. Save file identity/version and a cryptographic hash before evaluating any methods. Prior documentation has already shown the NEJM protocol/supplement download route inaccessible to this research session, so the EU source is a potentially useful alternative, not a completed review.

## Jurisdiction-specific registry interpretation

| Fact | Official EU CTIS source | U.S. ClinicalTrials.gov sponsor registry | Interpretation |
| --- | --- | --- | --- |
| Trial identity | EU CT 2023-505797-15-00, CY 6033, Phase III | NCT06081894, CY 6033, Phase 3 | Exact protocol matching identifiers support a *cross-registry identity match*. Neither record alone constitutes authorized reviewer certification of current phase. |
| Trial status | Participating EU countries reported **Ended**, with latest national trial-end dates through Feb 27, 2026 (a Poland end on Mar 4, 2025). | **ACTIVE_NOT_RECRUITING**, posted Sept 22, 2026 | **NOT AN INTRINSIC CONFLICT:** EU-country notifications and worldwide sponsor overall study status have different scopes, endpoints and as-of dates. Do not change the global row to COMPLETED from a regional end. |
| Enrollment | Public EU index shows 435 planned in the EU trial application, 175 in EU/EEA. | Global registry reports 500 estimated; published randomized sample was 517 | Geographies and planning/actual populations are **not equivalent denominators**. Record these separately and investigate sponsor amendments before treating them as contradictory. |
| Protocol amendments | Public EU index lists initial regulatory decision 2024-03-04, later modifications, and a public AM4 document after March 2026 | Registry version history available separately | Version chronology is a review lead; neither the approved clinical-trial application nor its amendment should be confused with a marketing authorization or FDA approval. |

Source links: official EU CTIS https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en ; public index https://ctis.eu/trial/2023-505797-15-00 ; U.S. record https://clinicaltrials.gov/study/NCT06081894 ; NEJM primary DOI https://www.nejm.org/doi/10.1056/NEJMoa2603021 .

## Phase-specific scientific method implications

1. **4.1 Study conduct/design:** Protocol AM4 is a potential original-source file for randomization, concealment, masking and sites, but **no contents independently inspected**.
2. **4.2 Endpoint changes:** Cross-check original, amended protocol, and pivotal co-primary endpoint date/version; no assertion of unchanged endpoints yet.
3. **4.3 Final SAP, intercurrent events and missingness:** **Still blocked.** A publicly listed protocol is not evidence that a signed/locked SAP is attached, complete, or pre-unblinding.
4. **4.4 Enrollment/power:** Keep global estimated enrollment 500, eventual randomized sample 517 and EU administrative plan 435 / EU-participant plan 175 as different fields until the original protocol/revisions explain the differences.
5. **4.5 Data integrity:** Compare EU substantial modifications with ClinicalTrials.gov record history; chronology and regulatory authorization do not prove clinical data integrity.
6. **5.1–5.4 and 8.1–8.2:** Review of pivotal estimands, multiplicity, safety and integrated benefit/risk remains subject to the original evidence and authorized independent adjudication. Safety discordances in revision 3 remain open.

## Verified research advancement and release control

**New:** A primary EU regulator page cross-validates exact Phase III trial identity; a publicly listed **AM4 protocol** and revisions are now locatable, and regional/end-status scope is explicitly reconciled.  
**Still missing:** Downloaded authentic versioned protocol bytes, original/final signed SAP, all appendices/sensitivity data, adjudicated safety line listings, named authorized independent reviewer, and accepted nonobstructive-HCM application/PDUFA evidence.

The present revision **does not** replace the isolated backend's saved original registry snapshots or change 29/29 source receipts. Independent phase verifications remain **0/29**; method grades **0/23,200** (0/800 pilot); scientific signoff **0**; FDA APPROVAL/CRL/REVIEW_DELAY **ABSTAIN**; certainty **NOT_VALIDATED**. The official EU trial application's clinical-trial authorization is not FDA approval of aficamten for nonobstructive HCM.

**Next independent-review instruction:** retrieve `D1_2023-505797-15-00_Protocol_FP` AM4 from the official CTIS public portal, verify source hash and amendment dates, locate standalone SAP if available, and compare the prespecified endpoints, safety rules and time cutoffs with the primary and secondary trial reports. When an authorized human reviewer independently verifies the phase and applicable documents, only then append immutable phase and method review events.
