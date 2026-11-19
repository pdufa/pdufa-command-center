# Cytisinicline 2026 backtest: chronology correction and outcome-exposure quarantine

**Research date:** 2026-11-19. **Integrity status: CASE EXPOSED TO OUTCOME INFORMATION DURING RESEARCH. NOT ELIGIBLE FOR THIS REVIEWER'S BLIND DIRECTIONAL LOCK.**

## Historical pre-decision source facts (safe for an independently clean reviewer)

- Achieve Life Sciences' **2025-09-03** announcement states FDA accepted the cytisinicline smoking-cessation NDA and assigned a **June 20, 2026 PDUFA target date**. https://ir.achieverx.com/news-events/press-releases/detail/238/achieve-life-sciences-announces-fda-acceptance-of-cytisinicline-new-drug-application-for-treatment-of-nicotine-dependence-for-smoking-cessation
- The same announcement explicitly names **ORCA-2 and ORCA-3** as the pivotal phase 3 trials supporting the application.
- The repository ledger's **2026-05-21** date is consistent with a **30-day-before-goal research cutoff**, not the actual FDA PDUFA target. Preserve both fields distinctly; do not overwrite the cutoff with the goal date.
- The 2025-09-30 10-Q corroborates the FDA goal date, both pivotal trials, and ORCA-OL long-term safety program: https://www.sec.gov/Archives/edgar/data/949858/000119312525268074/achv-20250930.htm
- A **2026-03-31** 10-Q contains manufacturing/regulatory risk discussion published before the May 21 cutoff: https://www.sec.gov/Archives/edgar/data/949858/000119312526218177/achv-20260331.htm . **Do not automatically promote its contents into a blind source packet without a separate unexposed reviewer and original filing timestamp check.**

## Contamination incident

During external research on 2026-11-19, the investigator encountered **post-decision 2026 SEC filings and news describing the actual FDA action**. These were not intentionally used to generate a prediction, but their discovery means **the present investigator cannot attest outcome non-exposure for this case**. Do not write the post-decision outcome, or a directional prediction derived from it, into a scientific review packet. Keep post-decision source URLs and actual outcome in a separate outcome-only evidence store after an independent blind prediction has been locked.

## Repository controls

- Event: **PDUFA26-TIMING-025**, cytisinicline, smoking cessation, provisional NDA218995 original cycle.
- Research cutoff: **2026-05-21**.
- Historical PDUFA target: **2026-06-20**, supported by the 2025-09-03 sponsor announcement.
- Pivotal studies: ORCA-2 NCT04576949 and ORCA-3 NCT05206370, original published reports independently authenticated in previous evidence review.
- Exposure flag for this investigator: **OBSERVED** (not NOT_DOCUMENTED).
- Prediction state: **NOT_ISSUED / NOT_LOCKED**.
- Scoring state: **NOT_SCORED**.

## Required next steps

1. Assign an independently **outcome-unexposed** scientific reviewer for this event, or exclude it from the prospective-style blind accuracy denominator.
2. Supply only version-pinned sources first public by **2026-05-21**; independently verify NDA identity and all other clinical/regulatory criteria.
3. Freeze and hash the evidence packet, record reviewer attestation and lock a prediction with timestamp.
4. Only after that, an independent scoring role may unblind the outcome and score.
5. If an unexposed reviewer cannot be established, label this case **retrospective/exposed**, not a valid blind success or failure.

**Accounting:** No new preliminary scientific reviews or directional locks. Cumulative preliminary narrative count remains **22/89 candidates, 132 level narratives**. This note documents a **newly observed exposure** and a **PDUFA-goal-versus-cutoff clarification**, not prediction accuracy.
