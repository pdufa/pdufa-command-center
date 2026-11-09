# Blind 2026 historical FDA prediction challenge — INO-3107

## Original frozen blind call

**Research-only directional forecast: COMPLETE RESPONSE LETTER (CRL) LEAN.**

This report is a **retrospective blind reconstruction**, written in November 2026,
after the **original** October 30, 2026 PDUFA target date. It is **NOT** a
prediction made before that event and must never enter prospective prediction
accuracy, independently validated performance, model calibration or the SMMT
November 2026 live forecast's totals. The FDA outcome is intentionally
**SEALED / NOT CONSULTED** for this case. We have **not verified whether an
FDA action occurred on the originally scheduled date**. This preserves a
later user-controlled comparison without implying knowledge of the result.

No source released on or after October 30, 2026 was consulted to support the
forecast. The source base is a predecision SEC Form 10-Q covering June 30, 2026,
plus the original ClinicalTrials.gov study locator.

- Forecast ID: `BLIND-INO3107-2026-10-30-V1`.
- Company and ticker: INOVIO Pharmaceuticals (INO).
- Drug: INO-3107, DNA immunotherapy delivered using the CELLECTRA device.
- Exact trial: **NCT04398433**, an open-label, single-arm Phase 1/2 trial
  supporting the BLA; this is not a Phase 3 trial.
- Proposed indication: adults with recurrent respiratory papillomatosis (RRP).
- Application: INO-3107 BLA, accepted December 2025 for accelerated-approval
  review (company-reported). Exact FDA BLA application number not verified.
- Originally reported PDUFA goal: **October 30, 2026**.
- Predecision evidence basis: `INO 2026-06-30 Form 10-Q`, available during
  August 2026, before the originally reported target.
- Outcome: **HIDDEN; DO NOT OPEN FDA ACTIONS OR POST-ACTION ISSUER NEWS
  UNTIL USER EXPLICITLY REQUESTS COMPARISON**.
- The source cutoff is the August 2026 Form 10-Q, not an invented full medical
  dossier through October 29; late predecision developments are an evidence gap.

## Phase-first evidence review

| Evidence gate | Predecision finding | Limit |
|---|---|---|
| Phase & identity | Phase 1/2, NCT04398433 | No pivotal randomized Phase 3 for this BLA cited |
| Regulatory review | BLA accepted December 2025, October 30 2026 PDUFA target | Acceptance does not imply approvability |
| Regulatory pathway | FDA flagged potential accelerated-approval eligibility issue in file acceptance; July 2026 informal meeting did not resolve it publicly | Critical unresolved legal/scientific gate |
| Unmet need | RRP traditionally requires repeated surgeries | Another immunotherapy, PAPZIMEOS, had already been FDA-approved in August 2025 |
| Year 1 efficacy | 26/32 (81%) reduced surgery burden; 23/32 (72%) had 50–100% fewer surgeries | Single-arm, noncomparative, small sample |
| Year 2 follow-up | 14/28 (50%) required no surgery; 78% fewer mean annual surgeries (0.9 vs 4.1) | Different evaluable denominators, historical baseline, no randomized comparator |
| Existing therapy | PAPZIMEOS was approved before this review | FDA may require evidence of meaningful advantage relative to existing therapy |
| Safety | Sponsor characterized efficacy and tolerability positively | Independent adverse-event adjudication is not established |
| Trial statistical power | No randomized or contemporaneous control in pivotal evidence | Causal attribution and comparative-benefit proof uncertain |
| Manufacturing / device | Combination biologic and electroporation delivery device | FDA constituent-part review and CMC/inspection final clearance unknown |
| Confirmatory trial | FDA said design feedback forthcoming | Completion, enforceability and adequacy unverified |
| Independent validation | None completed | No calibrated probability or certainty percentage |

## Scientific/regulatory interpretation

**Support for approval:** repeated surgery is meaningful morbidity in RRP.
The reported durable reductions in surgical burden are promising, especially
the year-two surgery-free fraction. FDA acceptance of the BLA, prior
breakthrough designation, and completed mid-/late-cycle meetings and scheduled
inspections are positive process indicators.

**Support for CRL:** this application relies on a small, uncontrolled Phase 1/2
dataset with shifting follow-up denominators. PAPZIMEOS had become an
approved alternative, changing the accelerated-approval benefit standard.
Most importantly, the FDA had specifically raised accelerated-approval
eligibility as a preliminary issue, and the sponsor said it might lack enough
evidence for traditional approval if the accelerated pathway were unavailable.
Biologic/device manufacturing adds an unresolved application-specific review
dimension, but an unknown inspection result is not proof of failure.

**Frozen call:** lean **CRL**, primarily because unresolved accelerated-approval
eligibility and lack of a controlled comparative trial are potentially
decisive. This is not a claim of therapeutic ineffectiveness. A favorable
regulatory interpretation remains plausible. Numerical likelihood is
**NOT VALIDATED / NOT ASSIGNED**.

## Exact predecision sources

1. INOVIO Form 10-Q, period ending June 30, 2026, discussion of trial results,
   FDA review, accelerated-approval issue, competitor and device review risks:
   https://www.sec.gov/Archives/edgar/data/1055726/000105572626000023/ino-20260630.htm
2. Original clinical study registry: https://clinicaltrials.gov/study/NCT04398433

The 10-Q's management commentary is sponsor-reported and not a complete
agency review record. Detailed protocol, statistical analysis plan, raw
participant data, actual CMC clearance, FDA full correspondence, and
independent clinical signoff have not been recovered.

## Blind integrity / later scoring

- The **first Git commit** containing this dossier is the permanent frozen
  prediction record, authored **after** the historical decision target.
- The companion registry file is intentionally **blind-only** and has
  `actualOutcome: null`; it is **never merged into
  `fdaPredictionDecisionAudit.json`** nor the live overall prediction
  accuracy denominator.
- A later user-authorized outcome comparison should separately acquire
  an official FDA approval or CRL source, exact BLA review cycle,
  actual FDA action date, and whether the original target had been
  extended. It may then mark the blind retrospective call as matching
  or not matching; it still cannot become a prospective backtest.
- Do **not** silently open a result link, compare the case automatically,
  or rewrite the original prediction to fit the outcome.
- The SMMT prospective 2026 case stays intact and separate; FOCUS membership,
  original phase-first worklist and all existing predictions are unchanged.
