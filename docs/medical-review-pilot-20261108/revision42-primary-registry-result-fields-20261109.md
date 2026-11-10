# MAIN Revision 42 — Original ClinicalTrials.gov outcome-field extraction for FOCUS 29

**Date:** November 9, 2026. **Scope:** Priority #979 clinical evidence review; #980 historical model research stays separated. Development branch and draft PR #965 only. No clinical/medical reviewer writes or production rollout.

## Work performed

- Added a read-only, NCT-identity-verified original ClinicalTrials.gov v2 study download and source SHA-256 receipt for **all 29 canonical FOCUS trials**, retaining **23 provisional FDA application groups** unchanged. Versioned research artifact captures current public registry bytes, not a historical before/after submission time series.
- Parses the current registry **resultsSection.outcomeMeasuresModule** for individual reported **primary** outcome tables, treatment-group names, denominators, source-reported measurements, time frames, reported p-values and confidence interval field values when those fields exist. All values are represented **as reported**, without model fitting or efficacy significance claims; no comparisons are invented for tables without an original analysis.
- Missing registry results are explicitly called **NO_CURRENT_REGISTRY_RESULTS_SECTION**, not failed efficacy, and an outcome table with no primary entries is classified separately. Clinical results might exist in a peer-reviewed publication or sponsor disclosure despite no resultsSection in the registry.
- Archives both exact original public registry JSON and metadata/structured summary in a time-limited GitHub Actions artifact. This allows later reproducibility and independent verification. No source bodies are silently copied to production or scientific grade ledgers.
- Synthetic tests ensure exact-NCT identity checks, SHA matching, source-reported measurements and p-values, no FDA/clinical promotion, 29/23 manifest preservation, and altered-source rejection.

## Gates not completed by collection

Registry posted results do **not** establish that an endpoint was prespecified in the final locked SAP, that a multiplicity-adjusted statistical test is valid, that complete safety and CONSORT data reconcile, that sponsor CMC manufacturing deficiencies are absent, or that the FDA application/indication cycle is independently confirmed.

Clinical method grades **0 new**, qualified reviewer signatures **0**, true historical out-of-time FDA backtests **0**, calibrated FDA probability **unavailable**. Official approval, CRL and review-delay predictions **ABSTAIN** for all pending applications. Existing 2026-11-09 qualitative application research leans remain dated, untouched research interpretations.

## Next scientific handoff

After source acquisition, pin the actual registry evidence receipt and actual primary outcome table counts; cross-map each posted primary endpoint to its corresponding `23` application-research dossier and any registered SAP/protocol evidence. Independently confirm 1) trial primary endpoint identity and significance with prespecified hierarchy; 2) missing or post-data registry publication; 3) adverse events and original trial population; 4) sponsor/FDA review-cycle source; and 5) qualified reviewer signoffs before promoting any scientific grade or FDA forecast. Do not train with the selected 412 FDA action research leads as if they formed a complete NDA/BLA cohort.

Evidence-handling limits: GitHub Action archives expire (configured max 90 days when allowed); they are not permanent or regulated repositories, and are not proof of original public availability before historical FDA decisions.
