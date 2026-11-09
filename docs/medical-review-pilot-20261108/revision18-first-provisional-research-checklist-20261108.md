# MAIN — Revision 18: first provisional research score for ACACIA-HCM

**Trial**: ACACIA-HCM / NCT06081894 / CY 6033. **Research snapshot**: November 8, 2026.  
**Branch**: `feature/medical-stage4-verified-method-matrix-20261108`; **draft** PR #965.  
**Output status**: a bounded *documentary research-readiness index*, not an official scientific method grade or regulator probability.

## Actual first numeric research index

`5.1 / Method 1` has a **3/5 provisional documentary-readiness checklist** calculated by the deterministic, validated-source-aware `evaluatePilotReadiness` function from five explicit yes/no research gates:

| Check | Result | Evidence/restriction |
| --- | --- | --- |
| 1. Exact NCT and CY 6033 identity crosswalk | Research source observed — +1 | [Sponsor registry](https://clinicaltrials.gov/study/NCT06081894), linked to EU protocol. Not independent human phase review |
| 2. Original signed-version protocol captured and hash recorded | Research source observed — +1 | [Original CTIS Amendment 04 capture](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398) SHA-256 `853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8` |
| 3. Peer-reviewed primary numeric efficacy and confidence intervals publicly accessible | Research source observed — +1 | [NEJM pivotal report as indexed by PubMed](https://pubmed.ncbi.nlm.nih.gov/42663312/), KCCQ-CSS +3.0 (95% CI 0.5–5.5) and pVO₂ +0.67 (95% CI 0.22–1.11) |
| 4. Final dated, locked and authenticated SAP independently inspected | **NOT VERIFIED** — no point counted | Missing final locked statistical analysis plan and detailed graph |
| 5. Complete original primary sensitivity and missing-data appendix/CSR independently audited | **NOT VERIFIED** — no point counted | Missing full original pivotal sensitivity and estimand analyses |

**Calculation:** three publicly observed *documentary checks* of five = **3/5**. Each criterion has equal one-point checklist weight purely for transparency, **not** because of a scientifically validated efficacy-weighting scheme. Neither the zero-point missing checks nor the three positive ones encode failure/success of treatment, safety, study integrity or FDA approval.

The UI shows this under **FIRST PRELIMINARY RESEARCH SCORE**, expandable to all five rules, source links, missing data and research date. It is intentionally **not written** to the separate 800 method clinical-score ledger. No confidential data, official grades or reviewer credentials were introduced.

## Safeguards

- Applies **only** to NCT06081894, assessment `5.1`, scientific method `1` (document extraction/source authentication).
- Public registry link, PubMed reference, CTIS protocol artifact and exact content hash are pinned. Incorrect/missing identity, protocol receipt, unrecognized gates, attempted fake SAP completion or clinical-grade events **withhold the provisional figure**.
- This is a human-curated source-state snapshot and reproducible checklist arithmetic, **not autonomous AI review of the whole source corpus** or a validated grading model.
- Research readiness must never be presented as **clinical confidence, 3/5 efficacy, 60% approval chance or a calibrated accuracy estimate**.
- Live independent method grades remain **0/800 pilot**, verified clinical phases **0/29**, FDA regulatory outcomes `ABSTAIN`, accuracy `NOT_CALIBRATED`.
- Research evidence leads remain **18/800** for the pilot; the other 782 positions are not examined. The new research checklist score measures a different quantity and does **not** mean one independent method is fully graded.

### Next steps

After draft engineering tests pass, expand comparable **phase-specific research-readiness checklists** with source anchors for other *individually appropriate* methods; retain `null` where the evidence doesn't support even a provisional checklist. Keep all official 0–5 science grades and FDA probabilities behind independently authorized review and empirical validation gates. Production and isolated Render service settings unchanged.
