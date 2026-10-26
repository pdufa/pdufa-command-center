# OUTCOME — three-application FDA review-timeline crosscheck (2026-10-26)

**Evidence state:** visually inspected first pages of original FDA CRLs, signed FDA approval letters, and the cited SBRA/review memos. **Seven source-supported review timelines, not seven independently certified complete cycles.** All sampled records remain research-only and outside model/backtest populations.

## Rocket Pharmaceuticals — KRESLADI, BLA 125806

| Receipt | Final action | FDA primary evidence |
|---|---|---|
| 2023-08-01 | 2024-06-14 Complete Response | FDA SBRA https://www.fda.gov/media/191993/download and original CRL https://download.open.fda.gov/crl/CRL_BLA125806_20240614.pdf |
| 2025-09-26 | 2026-03-26 accelerated approval | SBRA and signed approval https://www.fda.gov/media/191723/download |

- The FDA SBRA cover lists both application and resubmission receipt dates, BLA 125806/0, and **PDUFA action due 2026-03-28** for the later review.
- The FDA signed approval letter explicitly links the 2025-09-26 complete-response amendment to the 2024-06-14 action.
- The original CRL was visually inspected and identifies `BL 125806/0`. The October 2024 incomplete-response milestone is **not** a third final-action endpoint.
- Open before certification: full amended-clock history, timestamped source availability, and comprehensive cohort inclusion.

## Ultragenyx — FAYUVI, BLA 125845

| Receipt | Final action | FDA primary evidence |
|---|---|---|
| 2024-12-18 | 2025-07-07 Complete Response | FDA SBRA https://www.fda.gov/media/195198/download and original CRL https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf |
| 2026-03-20 | 2026-09-17 approval | FDA SBRA and signed approval https://www.fda.gov/media/194921/download |

- The approval letter explicitly describes 2026-03-20 as a complete response to the **2025-07-07** prior action.
- **Preserve source-specific PDUFA date conflict**: SBRA cover `2026-09-19`; FDA clinical review cover `2026-09-18` (https://www.fda.gov/media/195731/download). Do not silently choose a single universal source-truth date. In the structured timeline, `pdufa_goal_date` takes the SBRA value only **with** conflict metadata retained. Neither due date is an action.
- Open before certification: goal discrepancy reconciliation, full clock/amendment details and pre-action source availability.

## Replimune — TUDRIQEV, BLA 125827

| Receipt | Final action | FDA primary evidence |
|---|---|---|
| 2024-11-21 | 2025-07-21 Complete Response | Original CRL https://download.open.fda.gov/crl/CRL_BLA125827_20250721.pdf; original receipt also in signed later approval https://www.fda.gov/media/194128/download |
| 2025-10-09 | 2026-04-10 Complete Response | Original FDA CRL https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf explicitly links complete-response amendment to 2025-07-21 action |
| 2026-06-02 | 2026-08-06 accelerated approval | Signed FDA approval https://www.fda.gov/media/194128/download explicitly links June 2 amendment to April 10 action |

- FDA second-resubmission clinical review https://www.fda.gov/media/194468/download prints receipt **2026-06-02**, **PDUFA goal 2026-08-02**, and *reviewer recommendation* **Complete Response**. The FDA signed agency approval letter dates the **final decision** 2026-08-06. This is **not** a third CRL or a reviewer-determined final FDA decision; retain both document roles.
- The signed approval came four days **after** the goal printed in that clinical review. Mark the discrepancy for later clock/extension audit; do not fabricate an extension, clock reset, or alternative goal.

## Safe modeling and counting

Existing research action fixtures cover **19 action endpoints / 10 distinct BLA identifiers**. The earlier structured module contained **4 source-supported timelines / 2 applications** (Abeona, Mesoblast). This pass supports another **7 / 3**, giving **11/19 sampled action endpoints linked to timelines** and **5/10 sampled applications** represented. These denominators are **selected research-only samples**, not a complete population of all submitted FDA applications, and cannot estimate approval frequency.

No action-level observation becomes training-eligible through date linking. Conditions remain: `independently_certified_review_cycles=0`, `complete_application_denominator_verified=false`, `source_publication_asof_verified=false`, `model_eligible_records=0`, `prediction_probability=null`. The immutable original FDA audit indexes are unchanged.
