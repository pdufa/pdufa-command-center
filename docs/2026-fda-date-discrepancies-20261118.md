# FDA primary-source date discrepancies requiring reconciliation (2026-11-18)

## Pimicotinib (Pimjetmi)
- FDA novel approvals list gives **2026-11-13**.
- FDA Oncology Approval Notifications gives **2026-11-10**.
- Sources:
  - https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2026
  - https://www.fda.gov/drugs/cancer-approvals/oncology-cancerhematologic-malignancies-approval-notifications
- Status: **DATE_CONFLICT_UNRESOLVED**. Do not select one as the canonical action date without checking Drugs@FDA approval history / approval letter. Neither date is evidence of a PDUFA goal date.

## Giredestrant + everolimus (Wilserdly)
- FDA reports approval on **2026-11-16**, **four weeks before the FDA goal date**.
- Source: https://www.fda.gov/drugs/cancer-approvals/fda-approves-giredestrant-combination-everolimus-er-positive-her2-negative-esr1-mutated-locally
- Status: **FDA_ACTION_CONFIRMED_PDUFA_DATE_NOT_EXACTLY_VERIFIED**. Do not use 2026-11-16 as PDUFA date or infer an exact calendar day from 'four weeks'.
- FDA confirms evERA Breast Cancer NCT05306340: ESR1-mutant subgroup HR 0.38 (95% CI 0.27–0.54); median PFS 10 vs 5.5 months; OS immature. Safety signals include stomatitis, pneumonitis and bradycardia warning.
- Existing Level 1 assessment remains retrospective, not blind.

## Dataset handling
- Keep source-specific dates alongside their URLs until conflict is resolved.
- Never count novel-drug approval entries as complete PDUFA events.
- Do not mark either record as eligible for a validated historical blind-accuracy denominator based on these sources alone.
