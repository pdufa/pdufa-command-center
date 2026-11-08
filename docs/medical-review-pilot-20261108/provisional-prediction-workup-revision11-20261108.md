# MAIN — ACACIA-HCM first prediction workup (research hypothesis, not a validated forecast)

**Research snapshot:** 2026-11-08. **Exact NCT:** NCT06081894. **Protocol:** Cytokinetics CY 6033 (nonobstructive HCM, *not* MAPLE/SEQUOIA obstructive HCM).  
**Preview data:** `new-platform/frontend/data/acacia-pilot-prediction-workup-20261108.json`. **Rendered panel:** `PilotPredictionWorkup.tsx` above the live scientific assessment ledger.

## First scientifically grounded directional synthesis

**Conditional efficacy case exists. FDA outcome remains INDETERMINATE / ABSTAIN, not a calibrated recommendation.** The [NEJM pivotal report](https://pubmed.ncbi.nlm.nih.gov/42663312/) randomizes 258 to aficamten and 259 to placebo. Week 36 placebo-adjusted differences: KCCQ-CSS **+3.0 points (95% CI 0.5 to 5.5)** and peak VO₂ **+0.67 mL/kg/min (95% CI 0.22 to 1.11)**. Sponsor reports p=0.021 and p=0.003 against separately allocated 0.025 initial primary testing thresholds in its [August 28 public release](https://www.sec.gov/Archives/edgar/data/1061983/000119312526372456/cytk-ex99_1.htm). Thus statistical primary evidence is favorable. This does **not** establish validated clinical meaningfulness, correct implementation of all multiplicity/sensitivity procedures, approval probability, or sufficient safety.

Safety is **not neutral**. From the NEJM randomized denominators:
- LVEF under 50%: 27/258 **10.5%** aficamten vs 2/259 **0.8%** placebo; descriptive absolute difference **+9.69 percentage points** (unadjusted; descriptive, not clinical risk inference).
- All-cause serious adverse events: 52/258 **20.2%** vs 38/259 **14.7%**; descriptive absolute difference **+5.48 percentage points** (unadjusted; event timing and adjudication unknown).
- [November 4 SEC 10-Q](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm) reports heart-failure SAE 12/258 **4.7%** vs 3/259 **1.2%**; descriptive difference **+3.49 points**, but a different same-trial peer-reviewed report describes 11/1; preserve that discrepancy.

The exact **nonobstructive-HCM application was still planned**, rather than documented as accepted, in the issuer's 2026-11-04 disclosure. Do not import the 2026-11-14 PDUFA for MAPLE obstructive-HCM. **No approval, CRL, or review-delay probabilities can be calibrated from one trial's partial clinical readout.**

## Position-specific research mapping, not grades

The installed engine uses **8 layers × 40 assessment groups × 20 method definitions = 800 method positions** per trial. This source snapshot maps **15 candidate source leads** to positions inside the catalog's **11 critical Phase III assessment headings**:

| Assessment heading | Mapped method research positions | Open gating evidence |
| --- | --- | --- |
| 4.1 Randomization | L1 | actual allocation/concealment, blinded conduct |
| 4.2 Endpoint clinical meaning | L1, L2 | validated clinical importance, amendment lineage |
| 4.3 Estimands / missingness | L1 | final signed SAP and sensitivity analyses |
| 4.4 Sample/power | L1 | 516 vs 517 original CONSORT accounting |
| 4.5 Conduct | L1 | deviations, amendments and monitoring |
| 5.1 Pivotal efficacy | L1, L12 | final SAP re-analysis and clinical effect-size |
| 5.2 Secondary/multiplicity | L1 | complete graphical alpha recycle and LAVI |
| 5.3 Integrated safety | L1, L19 | HF SAE 11/1 vs 12/3, site-v-core LVEF, event windows |
| 5.4 Subgroups | L1 | interaction CIs, multiplicity and missingness |
| 8.1 Benefit–risk | L1 | independent integrated review |
| 8.2 Contradictions | L1, L5 | final source reconciliation and explicit red-team adjudication |

Method identities follow the actual catalog: L1 is **Document extraction and source authentication**; L2 is hypothesis reconstruction; L5 is critical challenge; L12 is multi-method adjudication; L19 is independent reproducibility audit. A mapped source **only** identifies a plausible investigation target; **no candidate position has a signed reviewer event or grade**. Do not count these 15 leads toward the reviewed-method total. The other 785 positions are not thereby marked inapplicable or failed. Phase-reported PHASE3 still requires an authorized independent phase-review event.

## Forecast scenarios (not ranked)

- **Approval is possible** *if* reviewers agree pivotal benefit is clinically and statistically sufficient, acceptable LVEF monitoring mitigates safety risk, CMC/label are adequate, and the indication-specific sNDA is filed/accepted.
- **CRL is possible** *if* efficacy sufficiency, safety, statistical robustness, labeling, manufacturing or other review standards are not satisfied following a filing.
- **Review delay is possible** *if* a filed application needs additional analyses, major amendments, inspections or clinical follow-up. No ACACIA-HCM nHCM PDUFA date is established as of this snapshot.

These counterfactuals are not scores, probabilities, certainty grades or current FDA actions. **Current release state remains ABSTAIN**.

## How prediction accuracy must eventually be established

1. Define **historical labeled, dated, indication-specific applications** rather than a convenience sample of positive published trials; include approved, CRL, withdrawn, not-filed, and delayed outcomes with valid temporal definitions.
2. Apply the **same 40 × 20 method catalog** phase-first on source information available **before each prediction timestamp**; prohibit post-decision leakage, same-drug indication mixing, and unverified data imputation.
3. Separate retrospective training, calibration and chronologically forward holdout; prevent repeat sponsors/indications from leaking across splits where possible.
4. For a calibrated outcome model, pre-specify and report **Brier score / multiclass log loss / calibration by probability bucket / class recalls**, with denominators, uncertainty intervals and coverage of abstentions. Accuracy claims require blinded holdout performance and continuous recalibration; a high confidence label is not a validation substitute.
5. Only after signed method reviews, phase verification, completed source-integrity gates, meaningful independent calibration and appropriate model validation may the final UI show **approval / CRL / delay probabilities** and measured accuracy.

## Remaining scientific work

29/29 FOCUS source packets captured; **29 phases await independent review**, **1,160 assessment groups await independent completion**, **23,200 individual method positions await independent grading** and **29 final calibrated predictions are absent**. The first pilot is a source-rich research prototype with **15 specifically mapped method leads, no graded methods, 1 missing locked SAP and seven high-level evidence questions still open**.

No source receipt, production app, isolated Render database, 29-trial roster, reviewer phase ledger or actual FDA prediction has been modified by this workup.
