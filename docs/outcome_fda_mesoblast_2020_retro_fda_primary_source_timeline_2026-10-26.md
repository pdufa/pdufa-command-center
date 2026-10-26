# Mesoblast RYONCIL BLA 125706 — original 2020 submission-to-CRL timeline (2026-10-26)

**Disposition: add ONE source-supported research timeline** without pretending that the signed September 2020 CRL was independently retrieved. This evidence is retrospective FDA regulatory-history documentation published with the 2024 approval materials, NOT a source available before September 2020 for prospective modeling.

## Primary FDA evidence independently checked

- FDA December 18, 2024 *Clinical and Clinical Pharmacology Review and Evaluation*, https://www.fda.gov/media/184952/download . Its executive summary (PDF page 8, zero-based 7) explicitly states that **Mesoblast submitted BLA 125706 on January 31, 2020** and that FDA issued a **Complete Response Letter on September 30, 2020**. Its regulatory chronology (PDF page 14, zero-based 13) independently repeats these exact dates. Both pages were rendered and inspected.
- FDA December 18, 2024 *Summary Basis for Regulatory Action*, https://www.fda.gov/media/185192/download, cover (PDF page 1, zero-based 0) lists **January 31, 2020 original receipt**, and the narrative confirms the **September 30, 2020 CRL**. The cover visibly misprints **127506/0**; the contemporaneous 2024 clinical review identifies **125706/0**, and FDA product registry, signed 2023 CRL and 2024 approval letter likewise identify **125706**. Preserve identifier discrepancy, do not invent a distinct 127506 application.
- FDA August 1, 2023 signed CRL https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf refers to deficiencies in the **September 30, 2020** CRL, independently corroborating the earlier action's existence and date.

**Missing:** original signed **2020-09-30 CRL**. The previously used research fixture linked to a guessed-looking original CRL download location (`https://download.open.fda.gov/crl/CRL_BLA125706_20200930.pdf`) that was **not retrievable/authenticated** in this pass. Replace that unverified direct-letter URL with the verified 2024 **FDA clinical review** and mark its role `fda_regulatory_history_summary`. Do not present that role as the contemporaneous signed 2020 letter.

## Structured research-only timeline

- `BLA:125706:ORIGINAL`, received **2020-01-31**, final FDA action **2020-09-30**, type `complete_response`.
- Submission receipt URL and final action corroboration URL both cite the FDA 2024 clinical review; additional review history source FDA 2024 SBRA. The original signed letter remains unverified and gets explicit open anomaly.
- FDA stated 2020 action due date September 30, 2020 in prior sponsor SEC filing; **do not encode that as an independently verified FDA PDUFA goal here**.
- Historical timeline certification remains false; source-publication date and pre-action feature as-of checks remain unverified. A post-2020 FDA review must not be mistaken for an as-of 2020 prediction feature.

## Impact on sampled counts

Before: **16 of 20 sampled FDA actions** linked to a source-supported structured timeline, across **8 of 10 sampled BLA identifiers**. This adds one timeline for an *existing* Mesoblast action, giving **17 of 20**, **8 of 10**; no new sampled FDA actions or applications created. Three selected actions remain without exact FDA submission start date: Atara/Pierre Fabre BLA 125745 (two CRLs) and REGENXBIO BLA 125840 (one CRL).

**Independent certification:** `independently_certified_review_cycles=0`; `complete_application_denominator_verified=false`; `model_eligible_records=0`; `prediction_probability=null`.

### Separate external corroboration (not sufficient for exact FDA received day)

- Atara SEC 2025 10-Q https://www.sec.gov/Archives/edgar/data/1604464/000095017025072040/atra-20250331.htm says **May 2024** original BLA submitted and **July 2024** accepted, but does **not** provide an exact FDA receipt date.
- Atara SEC 2025 10-Q https://www.sec.gov/Archives/edgar/data/1604464/000119312525276219/atra-20250930.htm says **July 2025** resubmission accepted by FDA, no precise receipt day. The January 2026 published FDA letter redacts the exact receipt reference.
- REGENXBIO Feb 2026 announcement https://regenxbio.gcs-web.com/news-releases/news-release-details/regenxbio-announces-regulatory-update-rgx-121-bla-mps-ii/ confirms FDA acceptance **May 2025**, not an exact receipt day.

These broad month-level corroborations are checkpoints only. **Do not fill missing `received_date` from a guessed day, approval-clock arithmetic, or the CRL date.**
