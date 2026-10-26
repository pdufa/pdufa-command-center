# OUTCOME — FDA-source-verified research fixture expansion (2026-10-26)

**Research only**; primary agency letters checked including the first-page PDF rendering. This report supplies independent evidence for five new events, not approval-probability training observations.

## New observed action endpoints

| FDA BLA | Date | FDA final action | Recipient on original document | Primary FDA letter |
|---|---|---|---|---|
| 125743 | 2022-02-25 | Complete Response | Green Cross Corporation | https://download.open.fda.gov/crl/CRL_BLA125743_20220225.pdf |
| 125743 | 2023-12-15 | Approval | GC Biopharma Corp. | https://www.fda.gov/media/174897/download |
| 125745 | 2025-01-15 | Complete Response | Atara Biotherapeutics Inc. | https://download.open.fda.gov/crl/CRL_BLA125745_20250115.pdf |
| 125745 | 2026-01-09 | Complete Response | Pierre Fabre Pharmaceuticals Inc. | https://download.open.fda.gov/crl/CRL_BLA125745_20260109.pdf |
| 125734 | 2023-06-28 | Approval | CellTrans Inc. | https://www.fda.gov/media/169921/download |

## Identity/review-cycle safeguards

- The Green Cross and GC Biopharma agency letters both explicitly print **BL 125743/0**, but name different recipients. They are two action endpoints under **one** application, not two approval denominators.
- The January 2026 Pierre Fabre letter explicitly cross-references the January 2025 Atara FDA action, and both identify **BL 125745/0**. They are two CRL endpoints under **one** application; the exact redacted intervening resubmission date is **unknown**.
- The CellTrans letter verifies the June 2023 approval and the original May 2020 BLA receipt; the FDA's separate SBRA describes a December 2022 resubmission. The research fixture labels the approval submission **CYCLE-UNVERIFIED** rather than claiming a certified resubmission sequence.
- Source *publication/availability timestamps* are not established from action dates and remain `None` in research fixtures: this intentionally blocks all retrospective `check_asof` selections.
- None of these letters proves the absence of other FDA actions. No complete cohort denominator, complete review-cycle boundaries, validated prediction model, or probability can be inferred.

**Counts after expansion:** 17 sampled final-action endpoints over 8 distinct application identifiers (prior 12 over 5, plus 5 endpoints and 3 applications); fully independently certified review cycles **0/17 priority records**, priority identity documentation **15/17**, model-eligible priority records **0/17**.

### Source lookup artifacts and deliberate exclusions

StemCyte BLA 125764 has a **November 20, 2024 approval letter** (https://www.fda.gov/media/183774/download) but Purple Book lists **November 21, 2024** (https://purplebooksearch.fda.gov/index.cfm?blaNo=125764&event=productdetails). Keep the conflict open; do not quietly select an action date in the research fixtures. Chiesi's unreleased identity and DBV BLA 125713 remain open.
