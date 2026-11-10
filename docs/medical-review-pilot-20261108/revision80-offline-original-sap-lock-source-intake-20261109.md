# MAIN Revision 80 — offline original SAP, database-lock and unblinding source intake

**Date:** 2026-11-09 Pacific  
**Research scope:** NCT06153693, MLYS, Launch-HTN, the single provisional NDA cycle `mlys-lorundrostat`  
**Mode:** Local, research-only, fail-closed; not a source acquisition, scientific adjudication, or FDA prediction.

## Why this additional step exists

R75/R77 original journal and source-method reviews mapped printed signature-date imprints, H1–H7 hypotheses, and imputation assumptions. R78 mapped SEC/public readout chronology. R79 added the integrity and source-sequence verifier. **None of these records independently authenticate** what original SAP revision was in force before final database lock and before treatment unblinding. The trial sponsor's confidential audit trail is not present in this repository.

R80 installs a **usable offline intake path** for independently approved original source files and reviewers, without a public API or uploading confidential clinical-trial files into a public GitHub Action.

## Installed research-only command

- `new-platform/backend/scripts/intake_r80_original_sap_evidence_offline.cjs`
- Core verifier: `new-platform/backend/scripts/verify_r79_sap_lock_provenance_packet.cjs`
- Security/regression tests: `new-platform/backend/tests/test_r80_original_sap_intake_offline.cjs`
- Dedicated independent acceptance: [R80 source intake CI #42747844442](https://github.com/pdufa/pdufa-command-center/actions/runs/42747844442) **SUCCESS**, checking synthetic document-byte mismatches, signer/provenance errors, replays/invalid order and abstention on no credentials. A mock successful packet is **not** a real scientific signoff.

The operator would need these **original independently obtained files**, kept off GitHub and outside the public deployment: (1) controlled SAP 3.0 Amendment 2 bytes, (2) authorized final DB lock/audit record bytes, (3) first unblinded access/authorization audit bytes, (4) signed evidence packet binding hashes, NCT, event timestamps and controlled SAP version; (5) a **separately owner-approved external public-key registry** with a SHA-256 digest independently pinned in `MAIN_R80_OWNER_APPROVED_TRUST_REGISTRY_SHA256`.

The trust registry must **not** be generated, approved or pinned by the same untrusted source submitting the packet. Two different approved roles and organizations are required: sponsor source custodian and independent statistical reviewer. Keys are not built into the project. Private signing keys must **never** be shared with the project, pasted into ChatGPT or committed.

### Offline usage — only after genuine original evidence is lawfully obtained

The following illustrates the interface, not actual file paths or approved trust credentials:

```bash
export MAIN_R80_OWNER_APPROVED_TRUST_REGISTRY_SHA256="<digest independently approved and verified by the owner>"
node new-platform/backend/scripts/intake_r80_original_sap_evidence_offline.cjs \
  --packet "/secure/intake/verified-signed-packet.json" \
  --sap "/secure/intake/source-controlled-original-sap.pdf" \
  --lock "/secure/intake/final-database-lock-audit" \
  --unblind "/secure/intake/first-unblinded-access-audit" \
  --trusted-keys "/secure/owner-approved-trust-registry.json" \
  --report "/secure/output/metadata-only-intake-report.json"
```

**Without the separately approved digest and all original source files**, the real command returns a blocked receipt (not evidence). The acceptance workflow explicitly runs with the owner pin absent and checks `BLOCKED_OWNER_APPROVED_TRUST_ANCHOR_PIN_MISSING`. The JSON report is written with file permissions 0600; it never contains original sponsor files, source filenames, source bytes or signing secrets.

With independently verified source hashes, timestamps and valid signatures, the command **only certifies technical packet consistency**. It does **not** adjudicate whether the contents of the audit documents are authentic, that the signatures were legitimate corporate authorization, what source-controlled SAP was actually in effect, that the SAP predates the first true unblinding, or the safety/efficacy of the product. A qualified reviewer must inspect all such issues and independently sign a separate scientific assessment. Even a technically coherent packet remains **FDA ABSTAIN, clinical grade null, timing UNKNOWN**.

## Current original-source status is unchanged

| Requirement | Observed status |
| --- | --- |
| R79 seven original SAP/DB-lock/unblinding/source evidence requirements | **0/7 independently authenticated** |
| Original seven publisher PDF byte-SHA receipts | **0/7** |
| Owner-approved external trust anchors for actual sponsor evidence | **0** |
| Clinically signed independent scientific reviews | **0** |
| Independently replicated H1–H7 analyses | **0** |
| Original outcome-blind historical validation runs | **0** |
| Validated FOCUS application-level FDA forecasts | **0/23** |
| Authorized FDA approval/CRL forecast | **ABSTAIN** |
| Independently calibrated accuracy | **UNAVAILABLE** |

No POOL/FOCUS membership, canonical 29 NCT or 23 provisional cycles, production state, retired RAAS/GEM surveys, application forecast or deployment has been changed.

**Next scientific work requires authentic third-party source acquisition and qualified expert review.** No amount of additional mock key signing or code coverage should be counted toward completion of those scientific evidence requirements.
