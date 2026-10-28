# FDA FY2023 approval-only historical cycle sequences

This research increment collects **four named historical applications**
from the official FY2023 PDUFA Performance Report (Appendix A, PDF pages
zero-indexed 82–83, printed appendix pages A-72/A-73):
https://www.govinfo.gov/content/pkg/CMR-HE20_4000-00195429/pdf/CMR-HE20_4000-00195429.pdf

The report is dated April 18, 2024, in its transmittal cover. That **does
not certify the first public release date**. The 2026-10-28 source research
snapshot date is stored separately. Report PDF bytes have not been
independently captured/hashed as part of this increment.

## Historical trajectories selected

| Product (sponsor) | Source-reported sequence | Prior CR cycles | Final 2023 action |
| --- | --- | ---: | --- |
| NGENLA / somatrogon-ghla (Pfizer Ireland) | CR → AP | 1 | AP |
| LANTIDRA / donislecel-jujn (CellTrans) | CR → AP | 1 | AP |
| RYKINDO / risperidone (Shandong Luye) | CR → CR → AP | 2 | AP |
| YCANTH / cantharidin (Verrica) | CR → CR → CR → AP | 3 | AP |

The four named eventual-approval applications have **11 observed review-cycle
rows**, including **seven earlier Complete Response actions** and
**four eventual approvals**. These are reported *sequence observations*,
not individually verified dated FDA regulatory actions. The source
lists approximate months in FDA review and sponsor response intervals,
with rounding; it does not establish precise letter dates or the exact
NDA/BLA and review-cycle identifier for each action.

## Critical selection-bias rule

**Appendix A is an approval-only cohort.** It includes applications
that were approved in FY2023, sometimes following older CRLs. It excludes
applications that remained unapproved, withdrawn, pending, or otherwise
absent from FY2023's approval list.

Therefore:

- 7 / 11 is **not** a true historical CRL or nonapproval rate.
- 4 / 4 eventual approvals is **not** an FDA approval probability.
- A previous CRL is not proof a future resubmission will be approved.
- Including only eventual winners introduces survivorship and hindsight
  selection bias. It cannot support calibrated PASS/FAIL model training.
- A repeated product name across indications or dosage forms may denote
  distinct applications; do not merge without exact original unit identity.
- The report is compiled after the historical decisions. Reconstructed
  predictions may use only evidence available *before* each action.
- The FDA's FY2024/2025 original filing totals (129/157, reported in a
  versioned source registry) are annual **filing** aggregates, not
  interchangeable with the FY2023 **approved application** list or with
  individual review-cycle decisions.

These examples are useful for **historical-parallel research** and for
designing source-integrity rules, **not** for calculating an approval
base rate.

## Implementation

- Research source register:
  `app/research_sources/hop_fda_approval_survivor_sequences.json`
- Fail-closed auditor:
  `app/hop_fda_approval_survivor_sequences.py`
- Authenticated read-only HOP endpoint:
  `GET /api/internal/hop/public-outcome-disclosures`, field
  `approvedSurvivorSequenceResearch`

Every input must preserve report identity, source page, sequence order,
reported CR/AP action codes and rounded review/sponsor durations. The
auditor refuses to create exact application IDs, effective action dates,
source publication certificates or independent training labels from
unreviewed metadata.

**Verified model-ready historical FDA cycles: 0. Independently backtested
cases: 0. Actual out-of-time accuracy, calibration and approval probability:
unavailable.**

Next priority: independently enumerate a **complete fiscal-year filing
cohort** (including still-unapproved and nonbinary cases), establish exact
NDA/BLA application and review-cycle identities, obtain original action
documents, freeze decision-time science evidence, and then run
program-disjoint out-of-time evaluation. No new production scanning,
spreadsheets, database writes or trading are enabled.
