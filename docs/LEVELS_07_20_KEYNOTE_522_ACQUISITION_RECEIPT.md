# KEYNOTE-522 public-source acquisition receipt (discovery only)

This receipt records actual GitHub Actions acquisition output; it is **not** a historical pre-decision snapshot and **not** blind-eligible evidence.

## Acquisition run

- Workflow run: https://github.com/pdufa/pdufa-command-center/actions/runs/43985548642
- Artifact: https://github.com/pdufa/pdufa-command-center/actions/runs/43985548642/artifacts/14285182062
- Branch: `plan/isolated-levels-7-20-20261116`
- Commit: `e5da730c98536cfc8e37a8e2bf63f4d5e715843d`
- Workflow result: success; artifact includes four files (two source responses, two JSON metadata records).
- Artifact retention: 14 days. Preserve separately before expiry if needed for research.

## Acquired sources

| Source | Actual retrieval time (UTC) | Bytes | Source SHA-256 | Classification |
|---|---|---:|---|---|
| https://pubmed.ncbi.nlm.nih.gov/32101663/ | 2026-11-17T00:11:16.911481+00:00 | 5,591 | `bb12a2c083d6bf5e29e65bca22ca3e74ddf4726e4ae92fea459d71b4906a6206` | Discovery only |
| https://www.merck.com/news/merck-announces-phase-3-keynote-522-trial-met-dual-primary-endpoint-of-event-free-survival-efs-in-patients-with-high-risk-early-stage-triple-negative-breast-cancer-tnbc/ | 2026-11-17T00:11:17.577587+00:00 | 161,523 | `9b78005dd18cab2b67889a88ecb96c50b8ae8e00b492e629d5fb522284e01bfe` | Discovery only |

The original NEJM PDF at `https://www.nejm.org/doi/pdf/10.1056/NEJMoa1910549` returned HTTP 403; no PDF bytes were acquired. The PubMed hash differs from the earlier run because the fetched response bytes differ; never assume two live HTML responses are byte-identical.

## Validation limits and required follow-up

1. Download and inspect the artifact bytes. The CI log establishes successful acquisition and hashes, but does not itself establish clinical content validity or the absence of later edits in the present-day HTML.
2. Extract publication dates and clinical endpoints from the acquired bytes; verify against independent authoritative sources and identify any post-decision additions.
3. Obtain a legitimate full clinical publication or alternate full-text archive, and hash the exact bytes actually retrieved.
4. Locate and authenticate point-in-time archived copies dated before the 2021-07-26 FDA decision. Present-day retrieval is not proof of historical availability.
5. Keep post-decision FDA outcomes quarantined from any blind prediction input. Do not produce prediction scores or backtest accuracy until eligibility gates pass.

No production activation, merge, or deployment is authorized by this receipt.
