# Orladeyo NDA 219776: extension-versus-final-action adjudication gate

**Research only. No independent adjudication, original-byte retention, historical forecast, or trading signal.**

## Source observed
FDA original approval letter: https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219776Orig1s000ltr.pdf

The FDA letter says:
- The NDA was received **March 12, 2025**.
- A **major amendment dated June 11, 2025** extended the goal date by **three months**.
- The application **was approved**, effective on the date of the approval letter.
- The FDA electronic signature records **December 11, 2025 at 04:12:45 PM**.

The letter itself is evidence of an FDA-acknowledged goal-date extension and of a final approval. It is **not** proof that the extension was publicly knowable at any particular historical prediction cutoff. The electronic signature timestamp is **not** the public publication timestamp.

## Required separate event rows

| Event | Current evidence | Remaining verification |
| --- | --- | --- |
| Original PDUFA target | Not independently established | Obtain contemporaneous original target-date notice, cycle and publication clock |
| Major amendment | FDA approval letter references June 11, 2025 | Obtain amendment notice and determine whether/when extension was publicly knowable |
| Revised PDUFA target | FDA approval letter says three-month extension | Obtain exact original/revised target dates and contemporaneous revision evidence |
| Final FDA action | Approval stated in original FDA letter | Retain original PDF bytes and hash; independently verify application/cycle and public posting |
| Historical prediction cutoff | Registry-supplied claim only | Verify exact cutoff and exclude all later documents from model features |

## Prediction-label contract

A formal goal-date extension and eventual approval **can both be true for the same review cycle**. Store them as separate dated regulatory events. Do not overwrite the extension event with the final approval or count them as two independent application outcomes.

If the prediction target is the **first FDA regulatory event at or before the original goal date**, an extension can be the relevant event *only if* the date revision was formally established and the protocol defines it as such. If the target is the **ultimate action on the application cycle**, the final approval is the outcome and the extension is timeline context. Choose and freeze the target definition **before** backtesting.

Do not infer an extension merely because an original target date passed. Do not classify a delayed decision as CRL without an actual complete response action.

## Current gate
- Original PDF retained with SHA-256: **NO**
- Exact original/revised goal-date notices independently verified: **NO**
- Public posting clocks independently verified: **NO**
- Independent adjudication: **NO**
- Eligible for historical accuracy calculation: **NO**
- Readiness: **NOT_READY / ABSTAIN**

Source inspected through a public FDA PDF reader; direct original-byte download from the execution environment failed due to DNS resolution. This record is a research lead and must not be promoted to verified outcome data.
