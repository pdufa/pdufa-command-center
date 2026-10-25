# HOP Historical FDA Outcomes — Data Contract

This is a **curated input format**, not a populated historical database.
Do not create invented outcomes or infer FDA decisions from trial phases.

Each JSON array record requires:
- `case_id`: unique immutable decision/program identifier
- `indication`, `therapeutic_area`, `modality`: normalized, evidence-supported text
- `phase`: integer >= 3
- `decision_date`: YYYY-MM-DD official FDA decision date
- `outcome`: `APPROVED` or `COMPLETE_RESPONSE`
- `evidence_as_of`: YYYY-MM-DD date when the relevant evidence was available
- `source_url`: official FDA HTTPS URL

A source URL passing format checks is **not** proof of a verified decision.
Every imported case still needs independent source-content verification and
time-correct trial feature extraction. Approval probability must remain null
until leakage-controlled backtesting, calibration, and outcome adjudication.

Never treat example fixtures as actual FDA outcomes.
