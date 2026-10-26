# OUTCOME — FDA action-event schema v1 (2026-10-26)

**Status: specification only, not a deployed database or model.** Defines an auditable event-level representation for source-backed FDA histories while preventing the CRL-publication collection from becoming a biased training cohort.

## Entities and keys

- `source_document`: `document_id` (sha256 of original bytes), `url`, `publisher`, `document_type`, `publication_date`, `effective_action_date`, `retrieved_at`, `original_text_identifier`, `extraction_status`. Publication and action dates are distinct.
- `application`: `application_key` (regulatory type + canonical FDA number), `source_published_identifier`, `sponsor_at_event`, `product`, `indication`, `crosswalk_evidence_document_id`.
- `submission`: `submission_key` (application_key + original/supplement number + resubmission sequence), `received_date`, `accepted_date`, `submission_class`, `source_document_id`.
- `regulatory_action`: `action_key` (application_key + submission_key + FDA action date + action type), `action_type` (approval, accelerated_approval, complete_response, other), `final_agency_action`, `source_document_id`, `supersedes_action_key`, `correction_flag`.
- `review_cycle`: `cycle_key`, `submission_key`, `start_event_key`, `end_action_key`, `pdufa_goal_date`, `goal_source_document_id`, `boundary_certification`, `missing_action_check`.
- `source_conflict`: `conflict_id`, `field`, `source_a_document_id`, `source_a_value`, `source_b_document_id`, `source_b_value`, `resolution_status`.
- `model_gate`: `application_key`, `complete_denominator_verified`, `cycle_boundaries_verified`, `feature_asof_verified`, `action_sources_verified`, `model_eligible`, `reason_codes`.

## Mandatory rules

1. **One published letter is not necessarily one application or one action**: Samsung's two Original 2 BLAs and Genentech's three submission targets require a separate letter-to-target many-to-many bridge.
2. **One application can have multiple action endpoints**: Mesoblast and Replimune have multiple CRLs and later approval; do not count each as an independent application in denominator.
3. **Final action precedence**: an FDA reviewer recommendation is not an FDA final action. Keep both with different document roles (Replimune).
4. **Date conflicts remain visible**: StemCyte approval date and Ultragenyx PDUFA goal must be stored as source-specific values, not silently collapsed.
5. **An incomplete response is not an FDA complete response action**: Rocket's 2024 incomplete response does not constitute a new review-cycle endpoint.
6. **No future-data leakage**: prediction features must have source publication or effective timestamps on/before the selected as-of date. Later FDA approval cannot backfill pre-action evidence.
7. **No CRL-only denominator**: build full approval/nonapproval application inventory independently; no training, backtesting or probability until coverage audited.
8. **Fail closed**: `model_eligible = complete_denominator_verified AND cycle_boundaries_verified AND feature_asof_verified AND action_sources_verified`; missing or contradictory evidence means false. `prediction_probability=null` unless eligible and model independently validated.

## Minimal validation fixtures (not executed)

- Abeona: 1 application, 2 actions (2024 CRL, 2025 approval), 2024 FDA-verified resubmission.
- Mesoblast: 1 application, 3 actions (2020 CRL, 2023 CRL, 2024 approval).
- Replimune: 1 application, 3 actions (2025 CRL, 2026 CRL, 2026 approval); review recommendation != final action.
- Rocket: 1 application, 2 actions; incomplete response is not an additional endpoint.
- Samsung: 1 letter, 2 targeted Original 2 submissions; Original 1 references are not automatically targeted.
- Genentech: 1 letter, 3 CR-targeted submissions across 2 NDAs.
- All priority records: `model_eligible=false`, `prediction_probability=null` until independently audited.

**Current status:** priority identity documentation **15/17**; identity open **2/17**; independently certified complete review cycles **0/17**; model eligible **0/17**. This schema does not change those counts.
