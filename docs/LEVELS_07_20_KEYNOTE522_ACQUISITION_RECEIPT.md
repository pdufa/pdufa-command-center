# KEYNOTE-522 discovery-source acquisition receipt

Status: DISCOVERY_ONLY — NOT a frozen historical evidence snapshot, NOT blind eligible.

## Provenance
- Trial: NCT03036488 (KEYNOTE-522)
- Pre-decision publication: Schmid et al., NEJM (2020), DOI 10.1056/NEJMoa1910549, PMID 32101663
- Downloaded source: https://pubmed.ncbi.nlm.nih.gov/32101663/
- Retrieval timestamp (UTC): 2026-11-17T00:04:33.279047+00:00
- SHA-256 of downloaded source bytes: 9e5f3ccf98c736d66bad9829b0c7e05727b5ee371dad88778334f285a9b2a413
- Byte count: 5591
- GitHub Actions run: https://github.com/pdufa/pdufa-command-center/actions/runs/43984602724
- Actions artifact ID: 14285445456; artifact name: keynote522-discovery-source
- Artifact retention deadline reported by GitHub: 2026-12-01T00:04:33Z
- Source receipt derived from the completed job log and artifact listing, not a local rehash.

## Acquisition outcome
The initial NEJM PDF request returned HTTP 403. The workflow then downloaded the PubMed bibliographic record and its metadata. The successful job is **not** proof that the NEJM PDF was obtained. The SHA-256 above belongs to the downloaded PubMed record, not the NEJM PDF or the ZIP artifact.

## Scientific handling
The retrieved record was collected in November 2026, long after the 2021-07-26 FDA decision. It is useful for discovery, bibliographic identification, and source traceability, but cannot prove what a historical prediction engine could have retrieved before the decision. Do not use it as a frozen pre-decision snapshot, assign it a historical retrieval date, infer FDA outcome, or score a blind backtest from it.

## Next gates
1. Obtain a permitted copy of the original 2020 study and independently hash its actual bytes.
2. Verify the document is the intended publication and distinguish publication date from retrieval date.
3. Obtain genuinely time-stamped pre-decision source snapshots or archival evidence before claiming point-in-time eligibility.
4. Keep FDA decision and post-decision material in the outcome-only partition.
5. Complete pre-registered blind evaluation and independent adjudication before reporting prediction accuracy.
