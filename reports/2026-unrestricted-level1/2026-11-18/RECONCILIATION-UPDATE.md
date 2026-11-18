# November 18 reconciliation update

**Status: partial.** This update recovers the reconciliation ledger after the managed workspace went offline. The published assessment CSV and JSON in this directory retain the prior 37-cycle snapshot. The supplemental ledger preserves changes and primary source links for the next integrated export.

## Coverage and completion

| Measure | Count |
| --- | ---: |
| Prior worklist leads individually dispositioned | 59 |
| Inherited leads newly verified | 21 |
| Inherited leads still blocked | 37 |
| Device PMA excluded | 1 |
| Newly discovered verified cycles | 2 |
| Additional lead with target moved to 2027 | 1 |
| Total worklist records, including exclusions and moved target | 99 |
| Distinct verified 2026 public-source review cycles | 60 |
| Verified cycles with an assessment or explicit clinical evidence gap in the locally validated export | 60 |
| Full-year denominator | Unresolved |

Kresladi and Avlayah are the two independently sourced additions. Mitapivat moved from November 1, 2026 to February 1, 2027. The edotreotide review maintained a single NDA cycle across its March and June goals and ended in a June 26 CRL. FDA action dates and sponsor announcement dates are distinct. [Kresladi filing](https://www.sec.gov/Archives/edgar/data/1281895/000114036125038030/ef20057000_ex99-1.htm) · [Avlayah FDA review](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761485Orig1s000RiskR.pdf) · [Mitapivat filing](https://www.sec.gov/Archives/edgar/data/1439222/000143922226000131/agio-20260930.htm) · [Edotreotide CRL](https://download.open.fda.gov/crl/CRL_NDA216900_20260626_Redacted.pdf)

The 37 in-scope blockers are listed individually in the ledger. Pending applications without a disclosed FDA number and approved applications with only an action date require different evidence. Obtain the exact application identity from a public FDA docket or the exact review goal from an original FDA or sponsor document. The calendar remains open and public records lack a universal inventory of pending or undisclosed deadlines. The 196 figure remains provisional.

## Historical accuracy and prospective freezes

- The local revised audit counted 58 verified historical actions and two original prospective INDETERMINATE freezes. The new retrospective reviews are outcome-aware.
- Eligible blind Level 1 results were 0 correct, 0 incorrect, 0 comparisons. Accuracy and calibration are unavailable. The separately documented HARMONi research pilot remains distinct from the Level 1 denominator.
- Numerical confidence is unavailable for these judgments. Repo policy requires a validated basis for numerical approval probabilities. The earlier prospective artifacts remain pinned to their original versions.

## Production interface check

| Interface | Existing contract | Compatibility finding |
| --- | --- | --- |
| PAST | `app/past/page.tsx` expects a Level 4 historical queue row with event key, ticker, cutoff and nullable blind prediction and score. | Application-cycle identity and an actual FDA action cannot substitute for that queue contract. Outcome-aware rows cannot populate the blind prediction field. |
| POOL | `app/pool/page.tsx` uses the paginated `FunnelWorkspace` PoolItem/ReviewItem contract. | Application-level rows can supply company, product and indication after mapping. An application ID cannot become a trial roster ID or imply POOL membership. |
| FOCUS | `app/focus/page.tsx` verifies exact NCT membership in the saved roster and checks versioned evidence runs. | One FDA application can map to several NCTs or have no exact NCT. Eligibility, source snapshot and membership need independent checks before an adapter could render it. |
| ASSESSMENTS | `app/LevelOneFocusScores.tsx` uses a five-category registry-document rubric. `lib/focus-assessment-chart.ts` expects frozen prospective or historical-locked prediction records. | Application-level qualitative directions cannot substitute for document coverage scores or calibrated probability fields. The two indeterminate freezes are abstentions for binary metrics. |

This was a read-only source and schema review. The draft contains research artifacts and leaves production inputs and eligibility untouched.

## Verification and recovery

The revised local snapshot validator passed on 99 worklist rows and 60 verified cycles. A separate connector-side check confirmed 59 unique inherited ledger entries with a disposition and source links. The broader Python discovery encountered a legacy `smoke_test.py` missing-file collection error. The CI-scoped Python retry and full frontend run did not return final results before the workspace went offline. The baseline's 124 Python and 12 focused frontend passes remain documented in the prior report.

Resume by retrieving `reports/2026-unrestricted-level1/2026-11-18/reconciled/` and the local validator changes from the original workspace if it returns. Validate the CSV/JSON parity and immutable freeze fields, verify the newly drafted quantitative clinical edits against the original sources, and commit the integrated export. If the workspace cannot be restored, rebuild those files from the pinned [baseline](https://github.com/pdufa/pdufa-command-center/tree/238802e66be16934473b2e68ec683c428cddc32d/reports/2026-unrestricted-level1/2026-11-18) and the recovered ledger. Then reconcile the 37 blocked leads and append a year-end refresh.

- [Recovered ledger CSV](reconciliation-recovery.csv)
- [Recovered ledger JSON and blocker manifest](reconciliation-recovery.json)
- [Baseline assessment CSV](assessments.csv)
- [Baseline assessment JSON](assessments.json)
