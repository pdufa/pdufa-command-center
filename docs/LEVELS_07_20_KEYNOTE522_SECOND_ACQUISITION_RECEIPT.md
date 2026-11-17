# KEYNOTE-522 acquisition run 43997152857 — verified outcome

Run: https://github.com/pdufa/pdufa-command-center/actions/runs/43997152857
Branch: `plan/isolated-levels-7-20-20261116`
Commit: `36658f54566250c2fb8ef80e13676955331d57be`
Job: `collect-keynote522` (success)
Artifact: https://github.com/pdufa/pdufa-command-center/actions/runs/43997152857/artifacts/14290880947
Artifact ID: `14290880947`; ZIP digest `489c97c37d5c8a5525f1f1fa4bcf266337a3c4488f05f63a919083df619612fa`.

## What was actually acquired
- The original NEJM PDF request failed. **No original journal PDF was acquired.**
- Europe PMC bibliographic JSON fallback: 1,261 bytes; subject PMID `32101663` verified; metadata hash and byte count validated by workflow. Retrieval 2026-11-17T01:39:02.912805Z.
- Merck 2021-05-13 pre-decision sponsor press-release HTML: 161,523 bytes; SHA-256 `9b78005dd18cab2b67889a88ecb96c50b8ae8e00b492e629d5fb522284e01bfe`; retrieval 2026-11-17T01:39:03.062335Z.
- Content-check report confirms both sources' SHA-256 and byte-count matches, subject markers, claimed publication dates before 2021-07-26, and **retrievals after** the decision.
- Five files uploaded (two sources, two metadata sidecars, content-check report). ZIP artifact size 39,798 bytes.

## Interpretation
- Two additional source bytes and provenance records are now available as a downloadable research artifact.
- This is a **discovery-only** acquisition. Neither the 2020 PDF nor an independently authenticated pre-2021 frozen snapshot has been obtained.
- `blind_eligible=false`, `historical_snapshot_verified=false`, `accuracy_evaluated=false`. No scoring or FDA prediction should be inferred.
- A sponsor press release is a separate pre-decision publication, not a substitute for primary trial paper or FDA source verification.

## Next
1. Find a legally accessible full original 2020 article and record its raw bytes/hash, or explicitly document access restrictions.
2. Verify point-in-time archived captures independently of 2026 retrieval timestamps.
3. Compare trial endpoint numbers against the source bytes, retain outcomes in a quarantined partition, then consider blind evaluation.
