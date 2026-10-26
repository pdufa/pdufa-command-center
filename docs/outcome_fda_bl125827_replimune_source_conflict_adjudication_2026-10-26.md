# Replimune BLA 125827 — FDA resubmission date conflict and reviewer disagreement (2026-10-26)

This supplements `docs/outcome_fda_bl125827_replimune_review_cycle_pass1_2026-10-26.md`, not a new independent application.

**Conflicting source statements:** FDA August 6 SBRA (https://www.fda.gov/media/194230/download) labels **April 10, 2026** the “First resubmission,” whereas the FDA April 10 CRL (https://download.open.fda.gov/crl/CRL_BLA125827_20260410.pdf) explicitly acknowledges an **October 9, 2025** amendment constituting a complete response to the July 21, 2025 action letter. April 10 is also the date of the *second CRL*. Preserve both statements as source-specific observations; flag `FDA_RESUBMISSION_RECEIPT_CONFLICT`. Do not overwrite October 9 with April 10 or count April 10 as a resubmission without further documentary support.

**FDA recommendation vs action:** FDA clinical review (https://www.fda.gov/media/194468/download) recommends Complete Response for the June 2, 2026 second resubmission due to efficacy evidence limitations. The FDA SBRA (https://www.fda.gov/media/194230/download) explains that Office of Therapeutic Products leadership recommended accelerated approval despite acknowledged uncertainties and with confirmatory study obligations. Final FDA approval letter (https://www.fda.gov/media/194128/download) grants accelerated approval August 6, 2026. Record separately: `clinical_reviewer_recommendation=complete_response`; `final_fda_action=accelerated_approval`. An internal recommendation is NOT a historical regulatory action endpoint.

**Chronology warning:** FDA SBRA and clinical memo list PDUFA goal August 2, 2026, four days before the August 6 approval. Preserve discrepancy and do not invent clock extension.

**Scope and gate:** BLA 125827 has two CRLs (July 21, 2025 and April 10, 2026) and one accelerated approval (August 6, 2026), **three action endpoints for one application**. `review_cycles_independently_certified=0`; `model_eligible=false`; `prediction_probability=null`; `complete_application_denominator_verified=false`.
