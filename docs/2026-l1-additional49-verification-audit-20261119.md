# Verification audit — additional 49 candidates (2026-11-19)

Source: `data/backtest/blind_inputs/2026-l1-additional49-candidates-75-to123.csv`

## Structural audit
- 49 rows, 49 unique case IDs, 49 unique archive positions.
- 49 populated ticker and drug/event names.
- 49 application identities marked UNVERIFIED; 49 evidence statuses MISSING.
- **Do not interpret archive position uniqueness as application uniqueness.**
- **No blind predictions generated.** Do not feed this verification report to a blind worker: public retrospective sources may disclose outcomes.

## External source spot checks (3/49)
- BLIND100-075 / VERA / Trutakna (atacicept): FDA BLA 761486, Vera Therapeutics, IgA nephropathy, PDUFA goal 2026-07-07, as listed in FDA integrated review. Candidate drug/sponsor match confirmed. Evidence packet remains unverified. Source: https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761486Orig1s000IntegratedR.pdf
- BLIND100-076 / VRTX / Casgevy: FDA supplement STN 125787/457, Vertex Pharmaceuticals, expansion to ages 2–<12 in SCD/TDT; FDA approval letter dated 2026-07-01. Candidate product/sponsor match confirmed, but candidate row does not specify indication or supplement number; event match provisional pending archive event mapping. Source: https://www.fda.gov/media/193444/download
- BLIND100-077 / UNCY / Oxylanthanum carbonate: Sponsor confirms FDA NDA resubmission accepted and new PDUFA goal 2027-03-25. Candidate product/sponsor match confirmed, but 2026 vs 2027 review cycles MUST be kept distinct. Historical 2026 event identity not fully verified from source packet. Source: https://ir.unicycive.com/news/detail/128/unicycive-therapeutics-announces-fda-acceptance-of

## Outstanding
46 other rows have not received external source checks in this audit. All 49 need exact application/supplement, indication, goal date, original cutoff and source packet, independent outcome-free evidence chronology and duplication audit. No row is certified ready for genuine blind prediction.
