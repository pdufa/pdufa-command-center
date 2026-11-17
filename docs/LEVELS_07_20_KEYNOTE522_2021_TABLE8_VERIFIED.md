# KEYNOTE-522 — Table 8 body verified in acquired 2021 briefing

## Acquisition and exact location
- Research workflow: https://github.com/pdufa/pdufa-command-center/actions/runs/44005494633
- Downloaded PDF and extracted full text: https://github.com/pdufa/pdufa-command-center/actions/runs/44005494633/artifacts/14294381213
- Acquired PDF SHA-256: `d60e17a8b819637cc959b55c12b24f562081b349dd75994e2a45859c881e3903`.
- The workflow found **Table 8 on PDF page 49** (the actual table body), and extracted PDF pages 48–51 to `briefing-amendment-table-pages.json`.
- Title: *Summary of Key Changes to the KEYNOTE-522 Protocol (Including Statistical Analysis Plan)*.

## Confirmed amendment entries
1. **Original protocol 05-Dec-2016.**
2. **Amendment 01 16-Dec-2016:** clarified dose modifications for paclitaxel/carboplatin and added inadvertently omitted overdose definition.
3. **Amendment 02 01-May-2018:** changed efficacy IA1 timing to >=500 surgery completions; added pCR IA2 after approximately 800 surgery completions; revised event-free survival assumptions and planned enrollment (refer to full extracted page for precise wording).

## Methodology safeguards
- A February 2021 briefing supports the assertion that these earlier amendments were described by February 2021. It does **not** establish that their original full texts were available to the public in 2016 or 2018.
- For a pre-February-2021 prediction cutoff, this briefing is not an admissible input, even though the amendments are dated earlier.
- For a July 2021 cutoff, review the 2021 briefing's publication provenance and individual content for any outcome or regulatory leakage before inclusion.
- The 2023 amendment 522-06 is explicitly quarantined.
- `blind_eligible=false`; `historical_snapshot_verified=false`; `accuracy_evaluated=false`.

## Next
Extract the **complete** Table 8 text into a normalized dated amendment ledger, then locate independently published pre-decision protocol/SAP versions and verify publication timestamps.
