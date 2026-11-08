# MAIN — source identity and echocardiographic safety reconciliation, revision 10

**Pilot:** NCT06081894 / ACACIA-HCM / Cytokinetics / CY 6033 / symptomatic *nonobstructive* hypertrophic cardiomyopathy. **Date:** 2026-11-08. **Status:** source research and eligibility checks, **not** an independently graded clinical assessment, final SAP verification, or FDA outcome forecast. Additive to [revision 9 numerical audit](./safety-arithmetic-source-audit-revision9-20261108.md); original receipts and 29-trial rosters preserved.

## Critical source-identity firewall — wrong-trial SAP excluded

A targeted public search for the ACACIA-HCM **final signed statistical analysis plan** did not locate a verifiable copy of the correct study's locked SAP. A seemingly relevant openly indexed PDF titled [Statistical Analysis Plan](https://openaccess.sgul.ac.uk/id/eprint/117845/4/hoi240049supp2_prod_1730392582.19884.pdf) is explicitly a **supplemental** statistical plan for **protocol CY 6031, SEQUOIA-HCM, *obstructive* HCM**. It **must NOT** be imported as evidence for ACACIA-HCM / **CY 6033, *nonobstructive* HCM**. Search/PDF text establishes the protocol and indication identifiers; independent screenshot rendering of the PDF was unavailable (cache error), so this is a strict identity-exclusion finding, not a claim of complete visual inspection or document extraction.

The correctly matched [official EU CTIS protocol Amendment 04](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398) for CY 6033 remains the original verified 90-page protocol, SHA-256 `853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8`. It says that missing-data and sensitivity details appear in a **separate SAP**. It is not that finalized SAP, nor can a supplemental plan for an *obstructive*-HCM trial substitute for it.

**Intake rule for scientific evidence:** Match **exact NCT / sponsor protocol code / indication**, record trial cohort and source-document type, and reject cross-trial SAP substitutions **before** requesting any scientific method grade or FDA prediction.

## Newly supported numerical and methodological distinction

Three records must be preserved **as separately labeled results**, not averaged, silently changed, or assumed identical:

| Source | Observation | Evidence status |
| --- | --- | --- |
| [Circulation global responder analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/), safety narrative | Per-protocol interruption quoted as **14 (2.7%) aficamten** and **1 (0.8%) placebo**. | Arithmetic remains inconsistent if computed against 258 and 259 randomized patients: **14/258=5.4%**, **1/259=0.4%**. It may be a report, population, or text error, but that is not independently adjudicated. |
| [Circulation ACACIA-HCM echocardiography analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674599/), discussion | **7 aficamten patients (2.7%)** required treatment interruption due to low LVEF. | **7/258=2.7%**. This is a directly published, same-trial *second article* corroborating a distinct numerator, **not independent replication** or proof the first text should be corrected to 7. |
| [Open Source Cardiology detailed comparison](https://opensourcecardiology.org/doi/osc.2026.0037), narrative comparing site and core lab | Reports **5.4% vs 0.4%** core-laboratory LVEF under 40%, but says **7 (2.7%)** reached the *site-read protocol interruption* threshold. | **A plausible definition-level explanation:** core-laboratory LVEF event count may differ from site-read dosing interruption count. **Not independently confirmed against original trial safety tables and event-level listings**. Treat this as an analysis hypothesis to verify, not a proven reconciliation. |

[Original Cytokinetics trial-results disclosure](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Results-from-ACACIA-HCM-Presented-in-Hot-Line-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026-and-Published-in-The-New-England-Journal-of-Medicine/default.aspx) describes **LVEF under 50%** in 27/258 versus 2/259 and **serious heart-failure events** 12 versus 3; the published secondary responder paper gives 11 versus 1. Those are different endpoints from low-LVEF interruption and require their own event-coded, exposure-window reconciliation. No FDA safety conclusion can be inferred from numerical consistency alone.

## What changed in scientific readiness

**New useful evidence:** (1) Explicit wrong-trial SAP identification and prevention of protocol CY 6031 cross-contamination; (2) a second peer-reviewed paper directly reporting **7/258** site-read low-LVEF interruptions; (3) a clear source-definition hypothesis for why the first report says 14 with a mismatched percentage.

**Still NOT established:** final signed **CY 6033** SAP; trial-specific site-versus-core adjudication definition and denominator; 11/1 versus 12/3 HF serious-event windows; regulatory-version effective dates; full independent investigator phase reviews. The seven pilot high-level evidence questions remain open, although safety reconciliation is now better targeted.

## Recommended next reviewer evidence requests

1. Obtain original CY 6033 **locked final SAP** including two co-primary tests, missing-data/sensitivity rules and the full graphical alpha transfer.
2. Verify LVEF **core-lab versus site-read <40%** event tables and patient-level overlap. Confirm what 14 and 7 each denote and whether the published 14 (2.7%) narrative has a correction.
3. Obtain investigator-adjudicated HF SAE listing, censoring/time-at-risk rules for **11/1** versus **12/3**, and full CONSORT counts explaining **516 versus 517** participants across disclosures.
4. Obtain signed authorization for independent phase and scientific assessment review. No research memo automatically creates a score event.

**Balance:** Source packets 29/29; independently verified phases 0/29; independently reviewed assessment groups 0/1,160; independently graded methods 0/23,200; validated FDA predictions 0/29. Research-only source crosscheck and wrong-trial exclusion are complete, but the scoring/certainty gate remains `ABSTAIN` / `NOT_VALIDATED`.
