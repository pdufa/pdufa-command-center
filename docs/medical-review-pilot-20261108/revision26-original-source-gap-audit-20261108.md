# MAIN Revision 26 — original Phase III evidence gaps, actual public-source retrieval

**Pilot:** ACACIA-HCM / NCT06081894 / CY 6033.
**Public-source audit date:** November 9, 2026 UTC (November 8 Pacific).
**Release:** isolated draft PR #965 only; no reviewer-write authorization, no backend or production redeployment.

## Concrete source-access results

A newly installed standard-library-only runner `scripts/medical/acacia_public_source_gap_reconciliation.py` independently attempted to access four exact public research sources:

| Exact public source | Retrieval observed in GitHub Actions #42555289486 | Scientific scope |
| --- | --- | --- |
| Official ClinicalTrials.gov exact study `/api/v2/studies/NCT06081894` | **RETRIEVED** | Trial ID PHASE3 matched; public large-documents response **did not list an SAP**, which does **not** establish absence elsewhere |
| Cytokinetics [October 12, 2026 sponsor safety disclosure](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx) | **RETRIEVED** | Original public sponsor explanation confirms two treated serious HF events associated with LVEF under 50%, ten additional HF serious events not associated with LVEF reduction, and three placebo cases: **2 + 10 = 12 vs 3** |
| NEJM [original pivotal article](https://www.nejm.org/doi/10.1056/NEJMoa2603021) linked protocol supplement | **HTTP/NETWORK UNAVAILABLE** to automated checker | A protocol supplement URL was attempted; no bytes authenticated, **not evidence the document does not exist** |
| NEJM linked supplementary appendix | **HTTP/NETWORK UNAVAILABLE** to automated checker | An appendix URL was attempted; no bytes authenticated; not a completed SAP/sensitivity analysis review |

**Unresolved:** The independently reported 11/1 serious-HF count in the subsequent analysis must not be equated to the sponsor 12/3 total until definitions, case coding, analysis windows and populations are reviewed. Even an accessible protocol supplement is **not automatically a dated final locked SAP**. Exact full sensitivity results and adjudicated event data remain missing from the verified research state. No clinical-science grade is created.

## Verified audit and provenance

[GitHub Actions audit #42555289486](https://github.com/pdufa/pdufa-command-center/actions/runs/42555289486) **SUCCESS**. Its ten offline safety tests passed and a research-only JSON receipt was archived (artifact **13646647829**, 90-day retention), with source SHA-256 fingerprints and audit receipt digest `74215ff89653cb4f3549ec74d0d446d55680f1b0659f7fcc8915a756aad5f86c`. No downloaded source PDF or full sponsor HTML was stored in the artifact. A network error is recorded as unavailable rather than "not found."

The audit workflow is `.github/workflows/main-acacia-source-gap-audit.yml`, scoped only to the draft trial research branch. It has contents read permission only, runs on relevant research source changes or explicit manual dispatch, and does not alter the default-branch nightly monitor or source ledger.

## Connected to the 18-position research queue

`new-platform/frontend/lib/acacia-phase3-review-queue.ts` now carries dated source-gap provenance notes and exact audit run IDs for 12 relevant evidence handoffs:

- **SAP/statistical gaps:** assessment headings 4.2, 4.3, 5.1, 5.2, and 8.2 (10 method positions).
- **Safety reconciliation:** 5.3/L1 and 5.3/L19 (2 method positions).

These notes appear individually inside the expandable iPhone PREDICTIONS queue and also in the authenticated, read-only CSV export. The review queue links the actual archived audit, sponsor October 12 original disclosure, and official trial registry. It explicitly warns that it is a dated source check, not a continuously refreshed final SAP review.

**Scientific count unchanged:** 18 source-mapped leads; 5 prior bounded documentary/research calculations; 13 source leads not yet analyzed; 782 without source handoff. No authorized clinical grades **0/800 pilot**, no medical phase reviewer signoff, FDA prediction **ABSTAIN**, accuracy **NOT CALIBRATED**.

## Next original-source research actions

Find an original dated final locked CY6033 SAP and signed analysis amendments, recover the original primary sensitivity/missingness analyses and CONSORT accounting, reconcile sponsor 12/3 versus secondary 11/1 HF SAE definitions and exposure denominators, then obtain independent qualified medical evidence review before publishing 0–5 grades. A later expanded fetch can try permitted alternative publisher/registry sources but must not pretend an unreachable PDF is missing globally.
