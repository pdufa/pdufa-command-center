# FDA outcome research: actual source coverage baseline (2026-10-25)

**Status: research only; source coverage reconciled, regulatory outcomes and
complete denominator unverified.** This is an inventory of published evidence
materials, **not** a measurement of FDA approval probabilities or prediction
accuracy.

## Reconciled source inventory

| Source-level observation | Published index result | What the count means |
|---|---:|---|
| FDA CRL/published action letter references | **458** | Published *letter references*, not distinct applications or decisions |
| Official FDA PDF source references whose bytes were confirmed | **457** | Retrieval and PDF-byte checks, not verified action-date labels |
| Source references without a released, safely fetchable PDF | **1** | Remains unresolved; published status "Under Review for Release" |
| Distinct confirmed PDF documents | **364** | One document may contain multiple letter references |
| Shared PDF documents | **61** | Documents requiring attribution of separate original letter pages |
| Letter references in those shared PDFs | **154** | Human page-level review queue, not 154 FDA review cycles |
| Additional letter references beyond distinct PDFs | **93** | Duplication at the **document reference** level |
| References outside shared PDF groups | **303** | Confirmed PDF references not in shared groups |
| Published letters linked by application ID to Drugs@FDA export | **334** | Only an identity link, **not** a verified approval for that review cycle |
| Published letter identity-link review queue | **124** | 15 unresolved IDs, 2 ambiguous links, 107 not found in approved registry |
| Approval-centric Drugs@FDA application references | **29,416** | Includes 23,023 ANDA, 5,908 NDA, 485 BLA records; **not a complete decision denominator** |

These figures come from the committed official-source audit **indexes**;
the source collection archive is fingerprinted, but this new coverage
reconciliation does not re-fetch source documents or re-check their contents.

### Shared-PDF review categories

For the 154 **published letter references in shared PDFs** only:

- **53** have one provisional same-page application/date candidate (priority 3).
- **21** have multiple provisional same-page application/date candidates (priority 4).
- **75** have only application-ID page candidates, not corroborated date on
  that page (71 priority 5, 4 priority 1 multi-application records).
- **3** have no application token on extracted pages.
- **2** have too many candidate pages for narrow manual targeting.

The last five collectively have priority 6. Even a single provisional
candidate is **not** a verified letter page boundary or action date.

## Why predictive accuracy is still not measurable

The schema-only historical review-cycle CSV contains **zero** outcome rows
as of the committed template. The related single published historical approval
example in research staging is not a complete model-ready dataset. A collection
of published response letters is selectively sampled; an approval-centric
registry excludes some applications and cycles that never secured approval.

The required population is **unique historical original NDA/BLA
application-review-cycle decisions** in a defined period and population,
with both approvals and nonapprovals, original action dates and decision
identities independently adjudicated, plus dated public predecision features.
Some public correspondence may not represent final approval or nonapproval at
all. Do not mix ANDAs or original/ supplemental submissions without an explicit
study protocol. Do not infer that a Drugs@FDA registry match proves that a
published CRL was approved at the time of that specific letter.

Therefore, as of the committed audits:

- Independently verified application review-cycle outcomes: **0**
- Validated complete application decision denominator: **No**
- Model-eligible historical outcome records: **0**
- FDA approval rate: **Unavailable**, not 0%
- Out-of-time prediction accuracy or calibration: **Unavailable**
- Live prediction activation: **Not permitted**

## How to reproduce the snapshot

Run from the repository root:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/audit_hop_fda_cohort_coverage.py \
  --output-json /path/to/private/local/hop_fda_cohort_coverage.json
```

The audit cross-checks eight committed source indexes, including consistent
published-letter counts, PDF/document duplication, Drugs@FDA identity links,
shared-PDF page candidates, export dates and original archive hashes. It
fails closed on contradictory scientific clearance flags, and deliberately
returns a nonzero shell exit status even for internally consistent inventories.

**Next nonautomatable work:** obtain independent qualified adjudication of
individual original FDA letters, particularly the 154 shared-PDF references
and 124 identity-review items; reconcile action-date and review-cycle
history; separately reconstruct a complete FDA decision denominator and
calibrate a held-out time-forward predictive model. These review queues can
overlap and must not be added together as unique decisions.

**Scope protection:** No existing PIPELINE, GEM JR, GEM, WT, scientific
FS/FA preset association, scan, trading workflow, billing service or production
approval probability was changed. The work remains research-only until
separately approved and validated.
