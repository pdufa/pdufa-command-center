# Priority regulatory source triage — 2026-10-27

Source: `main:data/pdufa_source_report.json`, `latest_run_id=40443182030` (2026-10-26 Pacific), read-only inspection.

## Reconciled totals
- All due: 1121; verified 994; unresolved 22; conflicted 2; unavailable 93; not applicable 10.
- Required findings due: 986; **24 required issues** exposed in `required_issue_examples`.
- Required issue breakdown: 1 FDA PDUFA target with final decision unresolved; 2 SEC issuer/ticker identity conflicts; 20 SEC financing closing evidence gaps; 1 FINANCIAL cash/runway accession gap.
- Missing required source families: FDA, SEC, FINANCIAL.
- ISSUER marked COMPLETE; MARKET COMPLETE WITH WARNINGS. This does not override overall PARTIAL status.

## Priority sequence
1. **Regulatory outcome:** `IONS|BEPIROVIRSEN_CHB_20261026`: source confirms target date, not final approval/refusal. Independently retrieve dated FDA action document and adjudicate application/review cycle; leave outcome `UNKNOWN` until authoritative confirmation.
2. **Identity conflicts:** `REGISTRY:QNCX` and `REGISTRY:TBPH`: SEC response did not identify requested ticker. Check authoritative issuer CIK-to-entity identity and effective ticker date; do not silently relabel or merge.
3. **SEC financing closure (20):** require company-matched dated filing and explicit closing statement, and independently establish post-Phase-3 financing order. A filing index, keyword, or public offering announcement alone does not establish a second financing sequence.
4. **FINANCIAL:** `BLTE|TINLAREBANT_STGD1_20270212`: require current nonnegative USD cash fact with SEC filing accession, date and entity match; do not impute cash runway.
5. Retain 93 unavailable source checks as unavailable; do not convert to verified or claim full coverage.

## Decision safety
No evidence gap may become an inferred PASS or FAIL, verified historical parallel, trade authorization, or complete source coverage. Keep existing GEM JR/GEM FS/FA associations unchanged.

## Next operational evidence
Inspect upstream nightly dispatcher trigger event and notification delivery receipts; observed full runs alone do not prove schedule trigger or SMS/email delivery.

No production mutation performed.
