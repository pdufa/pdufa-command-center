# Scientific Review Packet — one-click, checksum-verifiable dossier

The isolated Scientific Assessment service now generates a single **read-only JSON scientific review packet** for each exact archived ClinicalTrials.gov trial. It is an exportable work file for scientific reviewers, **not** independent adjudication, an FDA decision, a clinical result score or a future approval probability.

## Use

1. Open the [isolated Scientific Assessment panel](https://pdufa-scientific-assessment-review.onrender.com/scientific-assessment/batches).
2. Enter the existing internal review API key. Inspect an archived trial, such as `NCT02142738` (KEYNOTE-024) or `NCT04280705`.
3. When the source record and evidence-ledger integrity are available, select **Download 20-stage review packet (JSON)**.
4. Review the local JSON file or import it into an analyst's worksheet. Its filename is `NCT########_scientific_review_packet.json`. The internal API key is never included in the filename, URL, or JSON.
5. Verify the packet's `packetIntegrity.digest` against a SHA-256 hash of the body **excluding** `packetIntegrity`, encoded as UTF-8 JSON with sorted keys and compact separators. This is an accidental/tamper detection checksum, not an authenticated digital signature or source notarization.

The packet is also available via authenticated same-origin **GET** `/api/scientific-assessment/review-packet/NCT########`. The endpoint requires the normal internal API key and connected storage, and returns an attachment with `Cache-Control: no-store, private` and `X-Packet-SHA256` for independent comparison. The packet will not export from a missing exact NCT, corrupt gzip/SHA-256 archive, mismatched NCT, or a tampered source-ledger revision.

## Packet contents

- Exact NCT, historical archive retrieval date, source URL, SHA-256, and validated identity.
- **Twenty investigation stages** with registry field paths and an explicit missing-evidence inventory. Not independently scored.
- Registry-reported efficacy and adverse-event values with analysis identities, p-values, intervals, safety groups and source paths; no automatic significance or benefit–risk conclusions.
- **Two separate evidence grades**: analysis input readiness (coverage rubric) and critical scientific reluctance until independent protocols, published results, replication, and FDA/CMC documents have been adjudicated. Neither grade measures success/failure of a therapy.
- The versioned, checksum-checked source evidence ledger, preidentified document links and their "not adjudicated" flags.
- **Source reconciliation review tasks**. For KEYNOTE-024, eight questions include explicit criteria for prospectively locked SAP, first-line PD-L1 population, primary PFS and interim versus late OS cutoffs, crossover, safety numerator/denominator attribution, exploratory QoL multiplicity, FDA S-8 versus S-12 historical indications, and independent corroboration. Other archived trials receive four generic external-source verification questions.
- Each review question has `resolutionCriteria`, `criteriaSatisfied=0`, `reviewerAttestation=null`, `resolved=false` and an empty list of `resolutionEvidence`. **No review question is marked completed by the existence of a URL or a prior publication.**
- Explicit `scientificConclusion=null`, `fdaApprovalProbability=null`, `tradingEnabled=false`.

## Integrity and limitations

The source packet is produced **only from checksum-verified local trial archive plus separately validated ledger entries**. It does not fetch arbitrary URL content, invoke a live scan, or create new data rows. The reviewer must obtain and inspect actual dated protocol and SAP files, publications, regulatory correspondence, primary study tables and contradictory findings. A source review is not considered complete until it has been independently documented outside this automated source-coverage flow.

The SHA-256 hash only protects *consistency of the exported packet*. It cannot prove that third-party medical claims are authentic or clinically sound. No cryptographic reviewer signature exists yet. An analyst should not treat the packet as a prospective FDA forecast, trading recommendation or regulatory submission.

Review staging uses the isolated `feature/scientific-assessment-v1` branch only; there is no deployment to production scanners, GEM JR/GEM FS/FA restriction presets, brokerage systems or automated source import schedulers.
