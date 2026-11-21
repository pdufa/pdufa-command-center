# FDA OUTCOME: One primary reviewer with targeted escalation

**User-approved workflow (2026-10-25): one qualified primary reviewer for routine original FDA source investigation.** An independent second reviewer is **not assigned for every item**. Flag ambiguous, missing-source, incomplete, source-conflicting or unresolved action-cycle cases for second-source review or independent adjudication **if needed**.

The legacy independent A/B reviewer capability remains unchanged as an optional escalation path. No second reviewer was assigned, no historical FDA decision was independently verified, and changing the review workflow does **not** weaken model release gates.

## Prepared research workload

- **124** published-letter source references across **101** candidate research groups.
- **7** bounded primary-only files: 17 unresolved application-identity records first; six application-group batches of 20, 19, 20, 20, 20 and 8. No split of an application group.
- Every row includes source lock, historical FDA PDF lead and blank observation fields. The FIRST reviewer role is the **single primary**. The SECOND role is an *optional escalation tool*; two-reviewer archive code continues to exist for disputed work.
- Public artifact contains **counts only**. Source identities, PDF links, reviewer tokens and claim text remain private.
- Typed primary-review claim counts are explicitly **preliminary and not authenticated**. Only claimed source completeness is measured, not FDA regulatory accuracy. Source mismatch, ambiguous application, missing original FDA PDF, supplementary/unclear cycle, and incomplete records are rejected or escalated.

## Offline preparation (no Cloud/Drive transfer)

After the original FDA research collection produces its owner-only private FIRST handoff:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/prepare_hop_fda_single_primary_review.py \
  --prepare-primary-batches \
  --private-blank-first-json /private/blank_first_fda_identity_gap_review.json \
  --private-output-dir /private/new_primary_batches \
  --public-aggregate-json /private-public-separate/primary_review_preparation_counts.json \
  --as-of 2026-10-25
```

Only the seven PRIMARY JSON files go into the new restricted private directory. The command refuses unsafe/reused directories and writes files owner-only. It makes no FDA outcome labels.

After a reviewer is securely authenticated *outside this utility* and observations are collected in an access-controlled private completed-claims file, use:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/prepare_hop_fda_single_primary_review.py \
  --triage-primary-claims \
  --private-blank-first-json /private/blank_first_fda_identity_gap_review.json \
  --private-claims-json /private/primary_completed_claims.json \
  --public-aggregate-json /private-public-separate/primary_triage_counts.json \
  --as-of 2026-10-25
```

This produces aggregate counts of *awaiting*, *needs additional source review*, and *primary claim recorded but not independently confirmed*. No person is identified or authenticated by a typed token. It rejects forged FDA outcome flags and source mismatches, duplicate rows, unsafe claim text, invalid action dates, review cycles and publication class values.

## Encryption and access

The existing separately keyed FIRST/SECOND/CUSTODY encryption implementation and separate owner-only Google Drive folders are **preserved**. They are not automatically repurposed into a supposedly completed single-reviewer archive. A primary-only encrypted custody format, independent authorized primary and custodian key management, secure encrypted-only transfer, and off-runner recovery proof must be validated **before** private reviewer records are uploaded. The three original Drive staging folders remain private, unshared and empty until authorized.

## Scientific acceptance still blocked

A single person's observations are **not** independent verification. The pipeline may say **single-reviewed, provisional** only with the actual source review completed and authenticated under an approved workflow. The current collector does not authenticate the reviewer and no actual completed claims have been received. Original FDA review-cycle outcomes accepted as independent truth **0**; full original NDA/BLA approval **and** nonapproval denominator not established; leakage-free chronological calibration absent; FDA approval probability **null**, model-eligible **0**. The legacy A/B review remains available when a second reviewer is needed.

Preserve live nightly scans, GEM JR/GEM FS/FA, WT, credentials, backup/trading configuration and production prediction gates.
