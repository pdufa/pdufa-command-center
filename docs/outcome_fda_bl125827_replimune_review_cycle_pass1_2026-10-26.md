# Replimune TUDRIQEV BLA 125827 — review-cycle evidence pass 1 (2026-10-26)

**Scope:** source-bounded chronology and internal FDA review recommendation disagreement. NOT complete cycle certification or model eligibility.

## FDA primary sources
- FDA August 6, 2026 SBRA: https://www.fda.gov/media/194230/download — **BLA 125827/0**, original receipt **November 21, 2024**, first resubmission **April 10, 2026**, second resubmission **June 2, 2026**, action due **August 2, 2026**, and committee **accelerated-approval recommendation**.
- FDA April 10, 2026 original CRL: https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf — **BL 125827**, CRL dated April 10, 2026; acknowledges **October 9, 2025** amendment as complete response to **July 21, 2025** action letter.
- FDA second-resubmission clinical review: https://www.fda.gov/media/194468/download — confirms **July 21, 2025 CRL** and **April 10, 2026 CRL**, June 2, 2026 resubmission, August 2, 2026 PDUFA goal. **Clinical review recommends Complete Response**, not approval.
- FDA final approval letter: https://www.fda.gov/media/194128/download — accelerated approval August 6, 2026, TUDRIQEV (vusolimogene oderparepvec-wtpg), STN BL 125827.
- FDA product listing: https://www.fda.gov/vaccines-blood-biologics/tudriqev — FDA confirms accelerated approval; postmarketing confirmation required.

## Source-attributed regulatory events
| Date | Event | Evidence |
|---|---|---|
| 2024-11-21 | Original BLA receipt | FDA SBRA |
| 2025-07-21 | CRL #1 | FDA 2026 CRL and clinical review |
| 2025-10-09 | Complete-response amendment | FDA 2026 CRL |
| 2026-04-10 | CRL #2 | FDA original CRL |
| 2026-06-02 | Second resubmission | FDA SBRA and clinical review |
| 2026-08-02 | PDUFA goal (not outcome action) | FDA SBRA |
| 2026-08-06 | Accelerated approval | FDA final approval letter |

## Mandatory anomalies
1. **First resubmission date conflict:** SBRA labels **April 10, 2026** as 'First resubmission', but the April 10 CRL itself calls **October 9, 2025** the complete-response amendment. Preserve both source-specific statements; the SBRA value may be an action date transcribed into a receipt field. Do not silently normalize.
2. **Review disagreement:** second-resubmission clinical reviewers recommended a **Complete Response**; final FDA action was **accelerated approval**. The clinical recommendation is **not** the regulatory outcome label. Preserve as `clinical_review_recommendation=complete_response`, `final_regulatory_action=accelerated_approval`. Do not collapse into a single yes/no scientific consensus.
3. **PDUFA chronology:** final approval August 6 occurs after the FDA-documented August 2 goal. Record the dates; do not infer the cause or a clock extension without documentary evidence.
4. **Multiplicity:** the original identity queue includes **two Replimune source-letter records**; they refer to **one application** and distinct CRL actions. Never count as two independent applications.

## Gate
`fda_action_endpoints_documented=3` (two CRLs, one approval), `complete_review_cycles_adjudicated=false`, `complete_application_denominator_verified=false`, `model_eligible=false`, `prediction_probability=null`. Audit source export unchanged.
