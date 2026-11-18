# 2026 PDUFA Level 1 executive report

**Status on November 18, 2026 — partial public-source reconciliation.** The full-year denominator is unresolved. The proposed count of 196 is provisional and has no verified row-level export in this audit. Some review goals and pending application identifiers are undisclosed or unavailable in the public records reviewed. The year is still open.

| Measure | Count |
| --- | ---: |
| Discovered goal-worklist rows after known aliases were removed | 96 |
| Verified application, supplement, review cycle, indication and goal date | 37 |
| Worklist rows blocked on verification | 59 |
| Verified goals with a clinical assessment | 23 / 37 (62.2%) |
| Verified goals with a clinical evidence blocker and no assessed phase | 14 |
| Verified goals with a directional clinical assessment | 13 |
| Clinical assessments across verified events and unresolved candidates | 36 |
| Clinical candidate assessments with identity-blocked prospective calls | 12 |
| Verified prospective freezes | 2, both INDETERMINATE |
| Verified historical FDA decisions | 35 (29 approvals and 6 CRLs) |
| Eligible historical Level 1 matches / comparisons | 0 / 0 |
| Historical Level 1 accuracy and calibration | Unavailable |
| Drugs@FDA submission-status rows reviewed for crosswalk | 332, with 306 still unmatched |
| FDA CRL letter references reviewed for crosswalk | 33, with 27 still unmatched |

The worklist contains leads with provisional dates and unresolved possible aliases. Its 96 rows therefore do not establish 96 unique PDUFA events. The status and letter crosswalks overlap with the worklist and with each other. Their counts cannot be added to obtain a PDUFA total. The Drugs@FDA export covers NDA and BLA originals plus efficacy supplements present in its 2026 snapshot. Other supplement classes and outstanding applications may require other FDA and sponsor documents. Discovery applied no market-cap cutoff. [Drugs@FDA data](https://www.fda.gov/media/89850/download) · [FDA CRL data](https://open.fda.gov/apis/drug/complete-response-letters/) · [Calendar timing archive](https://www.pdufa.bio/research/fda-decision-timing/fda-decision-timing-2026-v41.csv)

## Findings

- The audit keeps amended dates in the same FDA review cycle where the sources support that linkage. FDA lists Filspari S-006’s original January 13, 2026 goal and amended April 13 goal in the same clinical and statistical review. [FDA Filspari review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/216403Orig1s006Med,StatR.pdf)
- evERA is outcome-aware. FDA approved the advanced-breast-cancer combination on November 16 ahead of its December 18 goal. The pending November 30 lidERA early-breast-cancer candidate has a distinct indication and unresolved exact application identity. [evERA FDA approval](https://www.fda.gov/drugs/cancer-approvals/fda-approves-giredestrant-combination-everolimus-er-positive-her2-negative-esr1-mutated-locally) · [evERA filing acceptance](https://www.gene.com/media/press-releases/15100/2026-02-19/fda-accepts-new-drug-application-for-gen) · [lidERA filing acceptance](https://www.gene.com/media/press-releases/15115/2026-06-01/fda-accepts-new-drug-application-for-gen)
- Deramiocel and relacorilant for Cushing syndrome were frozen as INDETERMINATE. The Deramiocel freeze records the sponsor–FDA disagreement over the primary HOPE-3 analysis. The relacorilant freeze records uncertainty over whether the resubmission resolves FDA’s benefit-risk concerns. [FDA HOPE-3 assessment](https://www.fda.gov/media/193912/download) · [Capricor filing](https://www.sec.gov/Archives/edgar/data/1133869/000110465926125355/capr-20260930x10q.htm) · [Relacorilant prior-cycle CRL](https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf)
- The HARMONi research pilot was committed November 11 ahead of FDA’s November 13 CRL. Its CRL direction agreed with the decision, 1 of 1 in that separate pilot. The frozen artifact lacks a reconciled BLA number and explicit Level 1 model designation. The current Level 1 reassessment is outcome-aware. The legacy directional and October retrospective archives contribute zero eligible comparisons. [Frozen HARMONi pilot](https://github.com/pdufa/pdufa-command-center/blob/1e73b2e57ff24ac975919cd8debfcd2b69b5a648/new-platform/frontend/docs/2026-harmoni-first-prospective-forecast.md) · [FDA HARMONi CRL](https://download.open.fda.gov/crl/CRL_BLA761524_20261113.pdf)

## Downloads

- Event assessments and blockers — [CSV](assessments.csv) · [JSON](assessments.json)
- Drugs@FDA submission-status crosswalk — [CSV](fda-submission-status-crosswalk.csv) · [JSON](fda-submission-status-crosswalk.json)
- FDA CRL letter reference crosswalk — [CSV](fda-crl-letter-crosswalk.csv) · [JSON](fda-crl-letter-crosswalk.json)
- Counts, field-level missingness, source snapshots and blockers — [JSON manifest](completion-manifest.json)

A positive or negative assessment direction reflects the reviewed evidence and a qualitative uncertainty estimate. A blank field marks evidence that this pass did not establish. The JSON retains source retrieval timestamps and hashes where captured, traceable older predictions, and separate goal, FDA action and publication fields. Receipt hashes describe retrieved bytes or the labeled source excerpt. The dated export and its Git history retain the new prediction versions.

The production eligibility and display interfaces require their own verified roster contracts. This unrestricted research export remains a draft-branch artifact.
