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

## Semantic rules
- Treat one issuer–drug–indication regulatory program as commercial unit. Link one or more distinct NCTs and do not sum a drug's patient population once per NCT.
- Competitor inventory is normalized one-to-many; approved treatment identities use FDA application and label; pipeline treatments use exact NCTs and sourced phase. Do not silently label a pending candidate approved.
- Require owner NCT + ticker + indication + treatment line + eligible population before comparing, and explicit direct vs indirect basis. Duplicates are rejected; conflicting source evidence requires independent review.
- Do not infer numerical clinical superiority from p-values alone or rank therapies on cross-indication outcomes. For no confirmed comparable peer group, ABSTAIN.
- Nine primary assessment headings currently have no uniquely assigned original research field: #4, #11, #13, #14, #15, #16, #18, #19 and #20. That is distinct from the prior high-level count of seven wholly missing assessment topics, because two partially covered topics have relevant fields mapped to adjacent headings. Each zero-field heading needs its own additional research evidence. **Authoritative check:** read `18 Mapping and Sync!A5:F24`; every zero field remains NOT ASSESSED. Never infer complete coverage merely from creating a heading.
- Sources are primary FDA, ClinicalTrials.gov, peer-reviewed results, SEC and dated sponsor disclosures. Preserve source dates, denominators and uncertainty, and distinguish modeled from VERIFIED.

## Sync boundary
Google Sheets formulas work *within the workbook*. The production website does NOT currently read from or write to this Google Sheet; adding matching columns does not install integration.

For a future secure sync job:
1. Use an authorized service-account/Google API connection and an authenticated/authorized website source. Never put bearer tokens or private source credentials into a public spreadsheet formula.
2. Enumerate full validated NCT records, reject mismatched owners and unknown source dates, and materialize a stable program-key record snapshot.
3. Upsert `07` master by canonical program/NCT key, `13` evidence by program/field/source, `16` competitors by exact canonical comparator key, and `17` assessments by program/rank/source, without clearing manual review.
4. Read back every changed range and reconcile source counts, duplicates, scope and source-version timestamps. Fail closed instead of silently publishing partial records.
5. Never advertise live sync until that exact procedure is implemented, authenticated, scheduled and verified.
