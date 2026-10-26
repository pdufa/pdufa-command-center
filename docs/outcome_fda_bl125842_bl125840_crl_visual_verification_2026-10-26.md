# OUTCOME: original FDA CRLs verified visually — BLA 125842 and 125840 (2026-10-26)

**Disposition:** add two research-only action endpoints; do not declare complete review cycles or model eligibility.

## Capricor — deramiocel

- FDA original letter: https://download.open.fda.gov/crl/CRL_BLA125842_20250709.pdf
- Directly inspected FDA PDF **page 1**, not merely a secondary report. Header prints `Our STN: BL 125842/0`, `COMPLETE RESPONSE`, `JULY 9, 2025`, `Capricor, Inc.`, and identifies deramiocel.
- FDA's July 2026 primary regulatory-history presentation: https://www.fda.gov/media/193912/download confirms original BLA submitted **December 31, 2024**, CRL July 9, 2025, **December 29, 2025 incomplete resubmission**, and **February 20, 2026 new resubmission**. The incomplete resubmission is *not* a new final action or independently certified cycle.
- Fixture: `BLA:125842:CYCLE-UNVERIFIED-2025`, `2025-07-09`, `complete_response`. Original CRL cannot establish a post-resubmission final outcome.

## REGENXBIO — clemidsogene lanparvovec

- FDA original letter: https://download.open.fda.gov/crl/CRL_BLA125840_20260207.pdf
- Directly inspected FDA PDF **page 1**. Header prints `Our STN: BL 125840/0`, `COMPLETE RESPONSE`, `February 7, 2026`, `REGENXBIO, Inc.`, and identifies clemidsogene lanparvovec.
- The CRL documents a nonapproval action for the reviewed BLA; no later action is inferred.
- Fixture: `BLA:125840:CYCLE-UNVERIFIED-2026`, `2026-02-07`, `complete_response`. FDA registry linkage beyond the published STN is not independently certified.

## Counts and safeguards

These **two distinct BL identifiers** were absent from the prior 17-action / 8-application research fixtures. With the additions, **19 distinct sampled final-action endpoints spanning 10 BL application identifiers**. These are *not* 19 independent applications, an exhaustive cohort, or a reliable approval base rate. All source *publication* timestamps are unknown and kept null. No prediction or backtesting authorization.

Priority identity documentation `15/17`; identity open `2/17`; independently certified complete review cycles `0/17`; model-eligible priority records `0/17`. Historical published audit indexes left unchanged.
