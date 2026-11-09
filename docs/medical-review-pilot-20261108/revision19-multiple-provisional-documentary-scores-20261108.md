# MAIN Revision 19 — three provisional research-document readiness indices

**Evidence snapshot:** November 8, 2026. **Pilot only:** ACACIA-HCM, NCT06081894, protocol CY 6033.  
**Branch:** `feature/medical-stage4-verified-method-matrix-20261108`; PR #965 **DRAFT**.

## What was implemented

Expanded the first working provisional research score from Revision 18 to **three** distinct, explicitly source-scoped research-document checklists. Each computes a transparent `observed / 5` count from five predeclared documentary checkpoints. **These are not independent 0–5 scientific efficacy/safety grades or FDA prediction probabilities.**

| Assessment / Method 1 | Provisional documentary score | Confirmed public evidence availability | Unresolved data |
| --- | ---: | --- | --- |
| 5.1 — pivotal efficacy source-document readiness | **3/5** | Exact ClinicalTrials.gov NCT and protocol identity; authenticated public CTIS Amendment 04 PDF with captured SHA-256; peer-reviewed pivotal abstract with both co-primary estimates | Final locked SAP; original primary missingness and sensitivity analyses |
| 4.2 — endpoint-design documentary readiness | **3/5** | Dated sponsor explanation of endpoint redesign; captured amended dual-primary CY 6033 protocol; peer-reviewed numerical co-primary endpoint report | Final locked hypothesis-testing graph and SAP; independently assessed clinically important difference and indication-specific FDA endpoint acceptability |
| 5.3 — safety-reconciliation documentary readiness | **2/5** | Peer-reviewed original pivotal LVEF and serious-event counts; later sponsor SEC disclosure of serious heart-failure adverse events | HF serious-event `11/1` versus `12/3` source/window definitions; interruption denominators; independently assessed AE coding, causality and reversibility |

Each criterion that lacks a verified source earns *no source-readiness point*, **not a clinical failure**. Counting equal documentary checkpoints is solely a reproducible workflow measure; it is not a validated scientific grading rubric and has **no direct or indirect route to a regulator probability**.

The code is in `new-platform/frontend/lib/pilot-research-readiness.ts`. Two additional explicitly authored source-bound checklists are in the existing `acacia-pilot-prediction-workup-20261108.json` research snapshot. The PREDICTIONS pilot workup now shows all three, each with an expandable five-rule explanation, source link for observed criteria, and gaps. Only source-observed criteria are counted. All other trial positions remain unscored by these research checklists.

## Explicit guards and remaining scope

- **Exact NCT only.** The existing pilot identity, original source URL and SHA-256, known primary estimands and safety numerators/denominators must match the saved snapshot.
- **Missing research documents cannot be promoted.** The source-readiness function explicitly pins missing SAP, independent FDA endpoint-adjudication, HF event reconciliation, interruption denominator reconciliation, and AE assessment as **NOT_VERIFIED**. A source-state mutation without a new verified methodology invalidates the provisional output instead of granting a point.
- **Clinical ledger remains unmodified.** This change creates **zero official 0–5 method grades**, zero reviewer signoffs, zero verified phases, and no FDA forecast.
- **Counts do not overlap:** three research-document checklists across three method positions are distinct from 18 mapped research handoffs, 782 other unexamined method positions, and **zero independently clinically graded positions in the full 800**. Do not average or total the three checklist scores into an efficacy or benefit-risk rating.
- **No automation of independent clinical adjudication.** Actual clinical evidence examination and reviewer credentials require authorization and original documents; no fake human reviewer records are generated.
- **Other 28 FOCUS trials:** not scored by these pilot-only source checklists. Existing 29-trial source runs preserved.
- **Current regulator categories:** APPROVAL / CRL / DELAY = ABSTAIN; certainty = NOT_VALIDATED; accuracy = NOT_CALIBRATED. The original label for obstructive HCM does not establish any ACACIA nonobstructive-HCM FDA filing or PDUFA date.
- **Production and isolated Render unchanged.** GitHub draft branch and Vercel preview only. Do not deploy any clinical grading backend based on these counts.

## Reference sources

- [ClinicalTrials.gov exact ACACIA-HCM record](https://clinicaltrials.gov/study/NCT06081894).
- [Original CTIS Amendment 04 PDF capture and hash receipt](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398). SHA-256: `853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8`.
- [Peer-reviewed primary trial report](https://pubmed.ncbi.nlm.nih.gov/42663312/), KCCQ-CSS 3.0 (95% CI 0.5–5.5) and pVO2 0.67 (95% CI 0.22–1.11).
- [May 6, 2025 Cytokinetics endpoint-redesign disclosure](https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Reports-First-Quarter-2025-Financial-Results-and-Provides-Business-Update-05-06-2025/default.aspx).
- [Cytokinetics November 4, 2026 SEC Form 10-Q](https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm), serious-HF events 12/3 and planned (not verified filed) nHCM supplemental application.
- [Circulation secondary responder study](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/), 11/1 serious-HF events with unresolved comparison to later sponsor counts.

## Verification checklist

Run `npm run typecheck && npm test && npm run build` in `new-platform/frontend`, backend `pytest` and retirement checks in GitHub CI. New tests verify exact 3/5 and 2/5 documentary counts, source tampering failure, missing SAP locks, different denominators, FDA abstention, noninclusion in the official clinical ledger, and correct UI labels. Check Vercel exact-commit READY state before reporting preview completion. PR stays DRAFT.
