# MAIN — Revision 17: pilot research handoff integrity and safety accounting QA

**Research checkpoint:** 2026-11-08 Pacific / 2026-11-09 UTC  
**Exact trial:** ACACIA-HCM / CY 6033 / NCT06081894  
**Branch:** `feature/medical-stage4-verified-method-matrix-20261108`; **PR #965 remains DRAFT**

This revision preserves every earlier research/source record, including [Revision 16's original-source evidence packet](./revision16-source-packet/README.md). It does not enter a human reviewer phase event, mark a clinical method reviewed, calculate approval probability, or change the source roster.

## First pilot source work visibly reflected on PREDICTIONS

The prior pinned preview showed **15** method source leads even though Revision 16 had already documented **18** exact method handoffs. The pilot's dated research snapshot and display are now aligned to the preserved Revision 16 packet:

| Type | As of original packet | Meaning |
| --- | ---: | --- |
| Installed hierarchy | 8 layers × 40 assessments × 20 methods | 800 positions in a single NCT |
| Source-mapped research handoffs | **18** | Leads/candidate original evidence, not completed examinations |
| Other method positions | **782** | Remain unexamined |
| Research findings with source limitations | **9** | Source-preparation statements, not adjudicated clinical findings |
| Original source responses preserved | **7** | GitHub packet tracks URL, retrieval date, bytes, SHA-256 |
| Blocked original source retrievals | **1** | Japanese jRCT HTTP 403, not trial failure |
| Numerical grade recommendations | **0** | Not computed from incomplete/unreviewed evidence |
| Authorized clinical method grades | **0/800** | Explicitly withheld pending qualified human review |
| Clinically signed phase events | **0** | Registry-reported Phase III is not independent signoff |
| FDA approval / CRL / delay prediction | **ABSTAIN** | Accuracy NOT CALIBRATED |

The three research handoffs newly exposed relative to the older 15-lead UI snapshot are **4.3:L4** (secondary KCCQ-OSS missingness/estimand evidence), **5.4:L4** (small CMR paired-subset and generalizability), and **8.2:L4** (original FDA *obstructive-HCM* label is not an ACACIA *nonobstructive-HCM* approval or filing).

Exact original source receipts and hashes for the two November 6 presentations, the FDA original label and trial authority record remain in `revision16-source-packet/retrieval-manifest.json`. These are original public materials, but the HCMS presentations are *same-trial* secondary analyses and not independent replications.

## Reproducible descriptive safety arithmetic — no invented score

The pure, offline helper `new-platform/backend/app/medical_pilot_source_reconciliation.py` applies only bounded arithmetic to explicitly attributed counts and denominators. It never writes to medical grading tables, looks up reviewer credentials or releases an FDA estimate. Regression tests in `tests/test_medical_pilot_source_reconciliation.py` verify the behavior.

| Source and reported event | Aficamten | Placebo | Reconciliation question |
| --- | --- | --- | --- |
| [Circulation secondary responder-analysis safety section](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/): serious heart-failure events | **11** (4.3%) | **1** (0.4%) | Determine clinical coding, observation cutoff and safety population |
| [SEC Cytokinetics 10-Q, November 4, 2026](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm): serious heart-failure events | **12** (4.7%) | **3** (1.2%) | Confirm whether additional events, definitions, windows or corrections explain the source difference |
| Circulation secondary narrative: treatment interruptions following LVEF decline | **14 (2.7%)** printed | **1 (0.8%)** printed | If the randomized arm denominators were 258 and 259, arithmetic instead gives **5.4% / 0.4%**; **not proof** the percentages are erroneous, because the applicable denominators may differ |

**No source wins automatically.** The `11/1` versus `12/3` figures cannot be treated as a causal safety signal delta, coding mistake or FDA decision without a reconciled event definition and cutoff. The denominator flags are not signed corrections and cannot become grades. All-cause serious adverse events (52 vs 38) and LVEF threshold reductions (27 vs 2) represent **different event definitions**.

The later sponsor [October 12 heart-failure safety release](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx) and [published primary efficacy report](https://pubmed.ncbi.nlm.nih.gov/42663312/) remain available for full evidence review, including favorable and unfavorable findings. Positive Phase III primary statistics do not by themselves establish FDA approvability.

## Outstanding scientific gates (unchanged)

1. Independent qualified human verification of the *exact Phase III identity* using original ClinicalTrials.gov and CY 6033 Amendment 04 protocol; preserve original signed-off event only after authorization.
2. Obtain and authenticate the final signed and locked CY 6033 statistical analysis plan, primary endpoint sensitivity appendix, analysis-set denominator table, missing data and multiplicity hierarchy.
3. Reconcile discrepant serious heart-failure event counts, treatment interruptions, coding, baseline denominators, LVEF categories and adverse-event reporting windows.
4. Record reviewer-grade events only from independently examined original evidence with qualifications, provenance, limitations and revision trail. Source leads and research findings never auto-promote to scores.
5. Validate an exact nHCM FDA application/review cycle and calibrate a frozen historical model for APPROVAL/CRL/REVIEW_DELAY before releasing any probabilities or accuracy rating.

## Verification boundary

The independent signed-in preview connection for Revision 16 [passed all 800 method readbacks](https://github.com/pdufa/pdufa-command-center/actions/runs/42541830770); its original backend remained isolated on Render at deployment `dep-dbogvaoqr7gs73ava440`. Revision 17's branch code must pass independent backend/frontend CI and Vercel build; that **does not** retroactively verify a new signed-in iPhone session or activate a new backend release. PR remains DRAFT. No original evidence events, production records or medical scores were altered.
