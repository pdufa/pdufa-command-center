# Pipeline 20-benefit / 38-field research sheet contract

## Scope and provenance
- Original ranked assessments: user-owned Google Doc `PDUFA Post–Phase 3 Pipeline — Proposed Benefits Assessment (Ranked 1–20)`.
- Existing native Sheet: https://docs.google.com/spreadsheets/d/1FSRXFXc4u2KTpdyP-vSbWil-Fgtrj3ucELSk2kpQAG0/edit
- Website preview/production route: `/pipeline` (source: authenticated `/api/scope-funnel?view=pipeline`).
- Study only: U.S.-listed issuers, current sourced $300M–$10B market cap, exact pivotal post-Phase-3 program, public readout through PDUFA minus three calendar days. Historical/negative/mixed readouts remain distinct from prospective action dates. No GEM JR/GEM restrictions and no trading execution.

## Native Google Sheets layout (already added; do not recreate)
| Tab | Main schema | Behavior |
|---|---|---|
| 07 Competitive Master | A:AL = 38 original research fields; AM:AS = date, source and workflow helpers; row 4 headers | Canonical editable research field values; blank until corroborated |
| 13 Exact Trial Evidence | A:R = per-exact-NCT and field ID evidence | Source URL, date, method, caveats, verification status |
| 15 Ranked 20 Assessments | A:F = identity and timeline; G:Z = original assessments #1–20; AA:AC = approved, pipeline and comparative source summaries | Formula-linked to 07 + 13 + 16 + 17; no automatic outcome forecasts |
| 16 Competitor Inventory | A:AA = one parent NCT + approved product/competing trial per row | Competitor type E, direct/indirect L, comparator result M, source URL U, evidence status W, final identity check AA |
| 17 Assessment Evidence | A:T = one parent NCT + assessment rank + source per row | E assessment rank 1–20, M evidence state, N URL, T exact identity check |
| 18 Mapping and Sync | A:K = 20 original assessments and 38 field-to-assessment mapping | Documents 29 directly assigned research fields + 9 standalone identification/evidence fields |
| 14 Charts Dashboard | Five chart objects including the original 20-assessment mapping structure | Counts are structural or verified-source counts; blank/non-entry = no numeric conclusion |
| 19 Phase 3 Census Review | 741 pinned 2026-10-26 source pointers (375 registry completed); historical company and cap links | Never auto-promote a census record to qualified |
| 20 Registry Evidence Intake | A:X = one reviewed registry evidence CSV; Y = spreadsheet formula identity check | Import an authenticated per-NCT CSV; leave qualification NEEDS_REVIEW; independent reviewer sign-off required |
| 21 Batch Review Tracker | 30 source-locked 25-NCT batch links (final 16), A:K; imported-NCT counts from tab 20 | Zero imports is NOT zero trials; imported means human-reviewed evidence is still required |
| 22 Eligibility Gate Matrix | A:F historical 741 NCT source pointers; G:L, N:V, W:Y and AC manually supplied reviewed evidence; M and Z:AB formula gates; AD:AH reviewed registry intake links and historical status drift | Never infer qualified programs from historical cap, registry completion, or formula completeness; exact-source and independent validation required |

## Semantic rules
- Treat one issuer–drug–indication regulatory program as commercial unit. Link one or more distinct NCTs and do not sum a drug's patient population once per NCT.
- Competitor inventory is normalized one-to-many; approved treatment identities use FDA application and label; pipeline treatments use exact NCTs and sourced phase. Do not silently label a pending candidate approved.
- Require owner NCT + ticker + indication + treatment line + eligible population before comparing, and explicit direct vs indirect basis. Duplicates are rejected; conflicting source evidence requires independent review.
- Do not infer numerical clinical superiority from p-values alone or rank therapies on cross-indication outcomes. For no confirmed comparable peer group, ABSTAIN.
- All 20 assessment headings have defined inputs: 29 of the original 38 research fields are assigned to assessment topics, nine original fields remain separate identity/timeline/evidence controls, and nine additional research definitions address previously missing topics (47 definitions total). This defines what to research but DOES NOT populate real findings. **Authoritative check:** read `18 Mapping and Sync!A5:F24` and `12 Field Catalog!A5:I51`; missing evidence stays NOT ASSESSED.
- Sources are primary FDA, ClinicalTrials.gov, peer-reviewed results, SEC and dated sponsor disclosures. Preserve source dates, denominators and uncertainty, and distinguish modeled from VERIFIED.

## Sync boundary
Google Sheets formulas work *within the workbook*. The production website does NOT currently read from or write to this Google Sheet; adding matching columns does not install integration.

For a future secure sync job:
1. Use an authorized service-account/Google API connection and an authenticated/authorized website source. Never put bearer tokens or private source credentials into a public spreadsheet formula.
2. Enumerate full validated NCT records, reject mismatched owners and unknown source dates, and materialize a stable program-key record snapshot.
3. Upsert `07` master by canonical program/NCT key, `13` evidence by program/field/source, `16` competitors by exact canonical comparator key, and `17` assessments by program/rank/source, without clearing manual review.
4. Read back every changed range and reconcile source counts, duplicates, scope and source-version timestamps. Fail closed instead of silently publishing partial records.
5. Never advertise live sync until that exact procedure is implemented, authenticated, scheduled and verified.

## On-demand current registry evidence intake
1. On the signed-in Pipeline, open an exact NCT trial in a dossier or unresolved research table, expand Current ClinicalTrials.gov registry check, and click Check official registry now.
2. After the check succeeds, choose Download this trial’s registry evidence for Google Sheets review. The download re-fetches the fixed ClinicalTrials.gov API host and returns precisely 24 source-backed CSV columns A:X; it does NOT modify the workbook automatically.
3. Import/paste that CSV data row beneath the headings in `20 Registry Evidence Intake`, without overwriting Y's integrity spill formula. Do not replace prior reviewed NCT rows without reconciling version/source changes. The import contains original registry facts and pinned issuer/ticker references, but drug/indication and commercial rights are NOT independently confirmed.
4. Inspect the final Y column. It must reconcile the NCT + historical issuer with tab 19 and source link; a `REVIEW_REQUIRED` row remains pending. Human approval of registry facts is never equivalent to pivotal success, FDA approval, qualified Pipeline membership, price or current-market-cap validation.
5. Live website ↔ Google Sheets automatic sync remains NOT INSTALLED without secure Google auth and audited readback; this manual per-trial export is an interim review pipeline.

## Source-locked on-demand multi-trial registry batches
- In signed-in Pipeline, the "Current official registry · batch evidence export" area allows 5, 10, or 25 pinned NCT IDs per download; the offset advances by that batch size and never accepts user-supplied arbitrary NCTs.
- The server queries `https://clinicaltrials.gov/api/v2/studies` with `filter.ids` from the pinned 741-record October 26 census, validates *every* requested NCT and requires an exact full response. Missing IDs, redirects, duplicates, pagination or an API error cause HTTP 503 with **no partial CSV**.
- A batch is at most 25 records, with one 24-column A:X CSV header. Tab `21 Batch Review Tracker` has 30 convenient links for the 25-record workflow; the last covers 16.
- Import CSV **data rows only** into `20 Registry Evidence Intake` columns A:X, preserving Y's array validation and any existing reviewed NCT rows. Do not copy the CSV header as a new data row, overwrite the formula in column Y, or let a repeated export introduce duplicate NCT rows.
- Status `IMPORTED — SOURCE REVIEW REQUIRED` indicates only that each NCT appears in the intake. It does not represent independent verification, qualified commercial programs, PASS probability, competitive advantage, a trade decision, FDA approval or fresh stock prices.
- No automated Google Sheets credential is configured on the website. These links are manual, signed-in exports—not live website-to-Google Sheets synchronization or a background scan.

## 22 Eligibility Gate Matrix audit requirements
- The matrix preserves all 741 historical NCT IDs without editing historical source fields. It never overwrites the canonical Pool, research master, competitor inventory or original 20 assessments.
- Evidence gates: (1) currently verified U.S. listing and dated issuer source, (2) current market cap $300M–$10B with sourced value checked within seven days, (3) original public pivotal Phase 3 results release with date and source, (4) exact NCT-to-drug-to-indication match with source, (5) documented commercial rights, (6) independent reviewer approval. FDA PDUFA date is optional and tracked separately for the PDUFA − 3 research cutoff; it is never inferred from registry completion.
- The **result is documentation readiness, not real-world eligibility certification**. A fully filled, independently reviewed row says `DOCUMENTATION COMPLETE — EXTERNAL SOURCE AUDIT REQUIRED`; the user must verify source accuracy and all original claims separately.
- The workbook reports disqualifying clues like not US-listed, out-of-band cap, not pivotal, mismatched drug indication and absent commercial rights as **REVIEW** items, not authoritative no-pass decisions without audited source.
- Columns AD:AH read from the manual registry-intake tab 20, enforce unique-NCT lookup and expose status drift versus dated registry snapshot; manual Sheet edits are not synchronized to website.
- The Charts Dashboard has an evidence-gate distribution chart and counts for historical NCTs and imported registry rows. A blank source is not counted as an adverse result, zero market cap, absent drug, or zero eligible programs.
- In the website trial dossier, `Eligibility proof checklist · 7 gates` uses the authenticated research snapshot, NOT the Google Sheet's latest manual reviews. The Sheet link is a handoff, not an active sync or record certification.
