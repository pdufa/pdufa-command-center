# MAIN Revision 35 — official ACACIA prior-version endpoint verification

Date: November 8, 2026 Pacific. Research-only draft PR #965.

**Why this matters:** the official [NCT06081894 record history](https://clinicaltrials.gov/study/NCT06081894?tab=history) lists outcome measure changes on May 15, 2025 (v27, following v26 on January 11), January 29, 2026 (v29), and August 3, 2026 (v30). A change-category index does not by itself prove exactly which endpoint definitions changed, clinical integrity problems, or FDA approval prospects. The independent original-version text and date crosswalk are the appropriate data.

This revision strengthens the existing exact-NCT public ClinicalTrials.gov history runner. A comparison of original v26/v27 measures is allowed **only** after official index date and original version text validation, without relying on retrieval of all later v29/v30 documents. It records explicit added/removed original measures, original descriptions, time frames, and enrollment as research evidence, while keeping the full 4-version completeness separate.

The exact research-branch-only GitHub Actions workflow now activates when its own script/tests/workflow change, runs six offline guard tests, retrieves originals from `www.clinicaltrials.gov`, and archives source bytes and a receipt without credentials. A failed external API read yields **NOT_VERIFIED**, not an invented one-to-two change or a claim that the SAP is missing everywhere. This workflow is not a production/nightly task and does not alter the source ledger.

Pending actual run results, the official **version-change category** and secondary one-to-two endpoint lead remain distinct. The original CY 6033 final locked SAP is still **not authenticated**, no independent phase reviewer has signed, scientific grades 0/800 for the pilot, FDA approval/CRL/delay ABSTAIN, accuracy NOT_CALIBRATED.

Actual release requirements after retrieval: verify the original signed protocol/SAP amendment chronology against database lock/unblinding, exact 36-week estimands, multiplicity graph and signed reviewer work before any method quality grade; do not treat a historical wording change as misconduct or a prediction.

## Live execution outcome — HTTP 403; source-text gate NOT cleared

[Exact-commit GitHub Actions run 42569226522](https://github.com/pdufa/pdufa-command-center/actions/runs/42569226522) completed **SUCCESS** at 2026-11-09 05:46 UTC. Its six synthetic guard tests passed and a research receipt artifact was uploaded. **Source acquisition did not succeed:** the official undocumented `www.clinicaltrials.gov/api/int/studies/NCT06081894?history=true` endpoint returned HTTP 403, as did direct original v26, v27, v29 and v30 history-version routes. This is an access restriction, **not proof that the original versions do not exist**.

Accordingly, actual research receipt flags remain `originalV26V27ComparisonVerified=false`, `originalV26V27Status=NOT_VERIFIED`, `sourceVersionCompleteness=false`; **no 1→2 original primary-outcome change** was established by fetched official text. The record-history page remains evidence only for a change in the *Outcome Measures* category on May 15, 2025, not the full before/after definitions. Do not upgrade the third-party indexed comparison to authenticated historical proof.

Alternative source caution: a third-party longitudinal version compilation on Hugging Face was identified but it is gated and has explicit **noncommercial restrictions**, including quantitative trading/commercial analysis. It was not accessed, imported, used for model training, or introduced into the repository. Such a route requires separate rights or a directly retrieved, rights-compatible official historical source. No user sign-in, credential sharing or IP-allowlist bypass was attempted.

Next valid route: obtain specific original source-version documents through the public study record's version-history browser or a licensed archival source, verify exact original bytes and submitted/post dates, then apply this tested comparison to authenticated data. Until then, NO scientific integrity verdict or FDA probability is released.
