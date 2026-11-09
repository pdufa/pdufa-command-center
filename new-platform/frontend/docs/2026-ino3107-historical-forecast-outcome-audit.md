# Independent outcome comparison — INO-3107 historical blind forecast

**November 9, 2026 audit update.** The originally frozen historical challenge forecast at
[commit 6eacacd](https://github.com/pdufa/pdufa-command-center/commit/6eacacd2728ac265f1b4b23571e8edb1108d5afe)
called **CRL lean** for INO-3107 (RRP) with an original October 30, 2026 PDUFA target.
That forecast was created November 9, after the FDA action; it was deliberately
blind to the outcome at creation. It remains unchanged.

**Actual FDA action:** **ACCELERATED APPROVAL**, October 30, 2026, for **VOCERYQ**
(previously INO-3107), FDA **BLA 125825**.

**Comparison:** predicted CRL; actual accelerated approval → **NOT ACCURATE**.
Historical reconstruction score: **0 correct / 1 evaluated challenge**, not a
prospective model performance estimate. There is no validated confidence
percentage and the comparison is excluded from the production prospective
accuracy pie and competitive line.

## Official outcome evidence

1. FDA, *FDA Approves First Plasmid DNA-based Immunotherapy for Adults with
   Recurrent Respiratory Papillomatosis*, dated Oct 30, 2026:
   https://www.fda.gov/news-events/press-announcements/fda-approves-first-plasmid-dna-based-immunotherapy-adults-recurrent-respiratory-papillomatosis
2. FDA, VOCERYQ biologics record (STN 125825):
   https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/voceryq
3. INOVIO, contemporaneous Form 8-K reporting FDA accelerated approval:
   https://www.sec.gov/Archives/edgar/data/1055726/000119312526442648/d150457d8k.htm

## What the directional assessment missed

The predecision report put too much weight on the potential lack of
accelerated-approval eligibility, and not enough weight on FDA's authority
to accept an intermediate clinical endpoint reasonably likely to predict
benefit. The FDA specifically regarded reduced surgical burden as such an
endpoint, and required a confirmatory clinical study as a condition of
continuing accelerated approval.

This is an error analysis written **after** the actual decision and must not
be used to rewrite the original forecast or the previous evidence cutoff.

## Data separation

- Source freeze: `new-platform/frontend/data/blindHistoricalForecasts2026.json`
  (**unchanged**, retains the original sealed pre-comparison record).
- This adjudication: `new-platform/frontend/data/blindHistoricalOutcomeComparisons2026.json`.
- Live prospective record:
  `new-platform/frontend/data/fdaPredictionDecisionAudit.json` (**unchanged**).
- Next prospective SMMT HARMONi forecast is not scored by this outcome.
