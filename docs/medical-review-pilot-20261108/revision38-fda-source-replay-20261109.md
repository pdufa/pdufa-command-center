# MAIN Revision 38 — fresh public FDA action-source recapture

**Date:** November 9, 2026. **Scope:** Draft PR #965, research-only isolated development branch. No production, trained model, reviewer-score writes or trading instructions.

## What changed

The earlier FDA FY2024–FY2025 source-selected worklist contained 412 candidate action rows in a GitHub Actions artifact with a 14-day retention period. Its source counts were real public-research observations, but the worklist was not a complete FDA application review-cycle census and was not durable.

Revision 38 adds a branch-only GitHub Actions workflow that re-fetches **current public FDA source exports** with the existing, bounded Drugs@FDA and openFDA CRL collectors, then computes a fresh candidate worklist using the existing code. The raw exact-byte source JSONs and the derived worklist are together retained in one GitHub Actions artifact for 90 days, subject to GitHub repository limits. Each output includes SHA-256 source fingerprints, current FDA export dates, source quantities, and a verified candidate-file hash.

The derived candidate count may differ from the October 2026 worklist count of 412. Do not represent the earlier 412 rows as the current count without a successful fresh collection.

## What the output is *not*

The combination of ultimately approved Drugs@FDA products and selectively publicized CRLs is **selection biased**. FDA annual original filing-year totals cannot be the denominator for action-year publication candidates. The resulting rows are source leads, not independently verified regulatory outcomes. Missing data include complete original NDA/BLA filing roster (including pending, never-approved and withdrawn submissions), exact original-versus-supplement review cycles, independent FDA action/publication clocks and frozen prior-to-decision scientific features.

The workflow rejects any source or output marked as training eligible or independently graded, and never computes a numerical FDA probability, outcome accuracy, or approval rate. A successful software test proves the audit checks function, not clinical validation.

**Next scientific step:** independently construct a complete consecutive filing-year application census and adjudicate its action history across all outcomes, with separate dates for event, public disclosure and features. Preserve blinded chronological and program-family-disjoint validation sets. Do not use a selective CRL/approval survivor list to train the FDA prediction model.

**Storage:** GitHub Actions artifacts expire at the configured retention limit (90 days when allowed). Permanent offsite archival, legal rights, credential setup and regulated storage are separate infrastructure decisions requiring authorization.
