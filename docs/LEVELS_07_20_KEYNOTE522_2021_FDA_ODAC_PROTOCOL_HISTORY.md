# KEYNOTE-522 — February 2021 FDA ODAC protocol-history discovery

**Research discovery, not a blind score or a frozen artifact.**

## Pre-decision source identified
FDA/Merck Oncologic Drugs Advisory Committee briefing, February 9, 2021, high-risk early-stage triple-negative breast cancer:
https://fda.report/media/145654/ODAC-20210209-CombinedFDA%26MerckBackgrounder.pdf

The source is dated before the FDA decision of 2021-07-26. It includes **Table 8, Summary of Key Changes to the KEYNOTE-522 Protocol (Including Statistical Analysis Plan)**.

## Documented early protocol history
- Original protocol: **05-Dec-2016**.
- Amendment 01: **16-Dec-2016**; clarified paclitaxel/carboplatin dose-modification guidance and overdose definition.
- Amendment 02: **01-May-2018**; changed timing of efficacy IA1 to at least 500 surgery completions; added efficacy IA2 for pCR after approximately 800 surgery completions; revised assumed 36-month control EFS from 60% to 78% based on emerging CALGB40603 data and increased surgery dropout; resulting planned sample size rose from about 855 to about 1150.
- These are **reported historical amendments in a 2021 briefing**, not downloaded authenticated 2016/2018 amendment source files. Do not infer complete wording of the originals.

## Historical validity and leakage caution
- Publication date of the 2021 briefing is before 2021-07-26, but the retrieved copy and its content still require byte-level provenance and document authenticity checks.
- FDA briefing material may contain agency evaluations, interim regulatory assessments, and information that could contaminate an intended earlier cutoff. Establish the exact prediction cutoff **before** admitting any part of it.
- FDA approval decision and post-decision sources remain quarantined.
- The 2023 amendment 522-06 PDF is **not eligible** for the 2021 blind backtest.
- `historical_snapshot_verified=false`, `blind_eligible=false`, `accuracy_evaluated=false`.

## Next steps
1. Acquire the 2021 FDA briefing from the official FDA host if available; hash bytes, capture publication date, document version, and content type.
2. Independently corroborate original 2016 and 2018 amendment dates and locate earlier protocol/SAP source bytes.
3. Build a cutoff-specific evidence ledger; distinguish pre-February-2021 and pre-July-2021 information.
4. Extract Table 8 with page references and avoid any retrospective model score.
