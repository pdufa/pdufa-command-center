# MAIN Revision 34 — ACACIA safety uncertainty research

Exact NCT06081894, CY 6033, evidence snapshot November 8, 2026. Draft PR #965 only.

Original [pivotal results](https://pubmed.ncbi.nlm.nih.gov/42663312/) provide LVEF below 50% 27/258 versus 2/259, and any serious AE 52/258 versus 38/259. The [October 12 sponsor report](https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx) reports 2 HF SAE events with low LVEF plus 10 without (12 treated total), versus 3 placebo. The [secondary ACACIA paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/) separately reports 11 versus 1 and prints a treatment-interruption line of 14 (2.7%). 14/258 is 5.43%; no original denominators or corrections are available to reconcile this. Sponsor 12/3 is internally consistent but not directly comparable to published 11/1 without case definitions, time-at-risk and observation-window reconciliation.

| Source | Counts treated/control | Unadjusted difference (pp) | RR | Exploratory approximate 95% RR interval |
|---|---|---:|---:|---|
| Pivotal LVEF below 50% | 27/258 vs 2/259 | +9.69 | 13.55 | 3.26–56.40 |
| Pivotal serious AEs | 52/258 vs 38/259 | +5.48 | 1.37 | 0.94–2.01 |
| Sponsor serious HF | 12/258 vs 3/259 | +3.49 | 4.02 | 1.15–14.06 |
| Secondary paper serious HF | 11/258 vs 1/259 | +3.88 | 11.04 | 1.44–84.91 |

Calculation: RD = 100×(a/258-b/259); RR=(a/258)/(b/259); log RR standard error = sqrt(1/a−1/258+1/b−1/259), approximate 95% interval exp(log RR±1.96×SE). These source-specific exploratory calculations are not formal causal effects or adjudicated clinical grades. With sparse events and differing outcome definitions they are especially uncertain. No multiplicity correction, regulatory forecast or validated benefit-risk determination.

The new research-only safety-reconciliation module, provisional mobile panel and source-tamper tests are installed on the isolated draft. Actual clinical grade remains UNASSIGNED; approval, CRL and delay ABSTAIN; accuracy NOT CALIBRATED. Obtain original SAE event definitions and original locked SAP before independent signoff. No production deployment or reviewer writes authorized.
