# MAIN — ACACIA-HCM final SAP and pivotal-results reconciliation, revision 6

**Research cut-off:** November 8, 2026 (UTC). **Exact study:** NCT06081894 / CY 6033 / EU CT 2023-505797-15-00.  
**Status:** PUBLIC SOURCE AUDIT, **NOT** independently authorized clinical review, trial grade or FDA prediction.  
**Prior source of truth:** [Original CTIS Amendment 04 protocol captured and SHA-256 verified](./authenticated-am4-original-protocol-revision5-20261108.md); [source discrepancies](./source-reconciliation-revision3-20261108.md). No historical receipt is overwritten.

## Final SAP availability — official registry audit

The isolated, credentials-free public-source audit in [GitHub Actions run 1](https://github.com/pdufa/pdufa-command-center/actions/runs/42526366023) queried official `https://clinicaltrials.gov/api/v2/studies/NCT06081894` and separately attempted the historical-version endpoint.

- The current public study record returned **exact-NCT identity verified**; **no public resultsSection** and **zero large study-document records** in the response. Accordingly, no separately posted SAP was present **in this API response** as of the check. This does not prove that a private SAP does not exist or that results were never submitted.
- An attempt to retrieve detailed version history from `/api/int/studies/NCT06081894/history` returned an HTTP error. That endpoint is not part of the documented public API; its failure is not evidence that the registry has no history. The browser-accessible record-history page remains the appropriate source for official historical review.
- [CTIS public study source](https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en): a complete 90-page protocol Amendment 04 was captured in the prior revision. Its 133 indexed CTIS public-document records showed protocol titles and other documents, but no title explicitly denoting **final statistical analysis plan**. A search of titles is not an exhaustive search of document contents or another jurisdiction's records.
- [NEJM publisher](https://www.nejm.org/doi/10.1056/NEJMoa2603021): lists protocol and supplementary appendix; public direct downloads had not succeeded previously. No final locked SAP has been obtained or read.
- [ClinicalTrials.gov official study-document policy](https://clinicaltrials.gov/policy/faq#fr_8): protocol and separate SAP are ordinarily submitted alongside required trial results. The absence of public results helps explain why an SAP may not yet be publicly attached; **do not assume this exact trial's statutory reporting deadline or exemption without its applicable-study review**.

**Controlled conclusion:** `FINAL_LOCKED_SAP_NOT_OBTAINED`. This is **a document gap, not failure of the trial**, and not authorization to manufacture an SAP or a method score.

## Source-supported planned-vs-observed efficacy comparison

| Measure | Original protocol Amendment 04 (2025-10-28) | Public study results (2026-08-28) | Evidence interpretation |
| --- | --- | --- | --- |
| Co-primary endpoints | KCCQ-CSS and peak VO₂, change from baseline to Week 36 | Both reported statistically significant | Source-matched endpoint definitions; no independent SAP signoff |
| Familywise type I error | Graphical multiplicity, two-sided familywise α=0.05 | Sponsor states initial two-sided α=0.025 for each co-primary | Plausibly nested within the graphical plan; **full graph and recycling sequence still require final SAP** |
| KCCQ-CSS | Study design assumed approximately 5-point placebo-adjusted effect | Difference +3.0 points; 95% CI 0.5 to 5.5; p=0.021 | Statistically below reported 0.025 testing threshold, **smaller than power assumption**; a design assumption is not a validated FDA clinical-importance cutoff |
| Peak VO₂ | Power design describes difference of approximately 1.0 mL/kg/min | Difference +0.67 mL/kg/min; 95% CI 0.22 to 1.11; p=0.003 | Statistically below reported 0.025 threshold; magnitude and patient relevance need separate interpretation |
| Left atrial volume index (LAVI) | Predefined secondary endpoint subject to multiplicity plan | Week-36 difference -1.30 mL/m²; p=0.058 | Not significant at conventional 0.05, nor independently confirmatory; this may constrain downstream alpha recycling |
| Time to first cardiovascular event | Secondary endpoint | Week-36-to-extended event analysis p=0.678 reported | Descriptive/nominal p only; **do not treat it as a tested confirmatory endpoint after hierarchy stopped** without final SAP |
| Independent trial review | Phase III sponsor protocol | Published randomized analysis in same trial | Source facts can be checked, but clinical review signoff is still missing |

**Primary external records:** [SEC 2026-08-28 8-K exhibit with exact dual-primary and secondary data](https://www.sec.gov/Archives/edgar/data/1061983/000119312526372456/cytk-ex99_1.htm), [NEJM article](https://www.nejm.org/doi/10.1056/NEJMoa2603021), [sponsor full results](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Results-from-ACACIA-HCM-Presented-in-Hot-Line-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026-and-Published-in-The-New-England-Journal-of-Medicine/default.aspx), [issuer 2026-11-04 10-Q](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm).

## Endpoint chronology and versioning caveat

A [third-party change log for NCT06081894](https://dashboard.datalookout.com/trial/NCT06081894) has indexed a **May 2025 transition from one to two primary registry outcomes**, and an enrollment target increase from 420 to 500. This is a **research lead only** until the **original ClinicalTrials.gov record versions and protocol/SAP amendment dates are independently checked**. It should NOT be called post hoc manipulation, an FDA objection or a proven protocol deviation. Sponsor protocol Amendment 04 is dated 2025-10-28, preceding publication of the clinical results. The amendment's existence and dated methods alone do not prove its final analysis implementation.

## Safety and benefit-risk remain open

The [secondary responder full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) reports **11 vs 1** serious heart-failure events, while [October sponsor HFSA disclosures](https://www.globenewswire.com/news-release/2026/10/12/3379213/0/en/cytokinetics-announces-additional-data-from-acacia-hcm-presented-at-the-hfsa-annual-scientific-meeting-2026.html) report **12 vs 3**. No definitive reconciliation was found. The 10-Q independently acknowledges efficacy, safety and clinical-importance review uncertainty and says a **nHCM** supplemental NDA was **planned in Q4 2026**, not yet established as filed/accepted in these references. Approved obstructive-HCM use is a different indication.

## Machine-readable next-action gates

- **Priority A:** obtain *final locked SAP*, verify document hash, date, original alpha graph, endpoint-change lineage and missingness algorithms.
- **Priority B:** retrieve dated prior ClinicalTrials.gov versions and earlier EU protocol amendments, compare May 2025 primary-endpoint changes to pre-lock document approvals.
- **Priority C:** reconcile source-specific heart-failure SAE counting windows and treatment-interruption denominators before safety grading.
- **Priority D:** independent authorized phase and clinical evidence adjudication. Only afterward may immutable phase/method review events be appended and calibrated FDA probability work begin.

**Controlled status unchanged:** 29/29 original saved trial source packets; independent phase verifications **0/29**; independently scored method positions **0/23,200** (pilot 0/800); clinical signoffs 0; FDA APPROVAL/CRL/REVIEW_DELAY `ABSTAIN`; certainty `NOT_VALIDATED`. The preview's source-handoff interface is read-only; production, roster and previous evidence receipts are unchanged.
