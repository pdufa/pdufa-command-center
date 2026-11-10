# MAIN Revision 31 — isolated PostgreSQL acceptance and synthetic key-recovery gate

**Scope:** ACACIA-HCM / NCT06081894; six outstanding original source categories, 18 mapped scientific method leads. **Release:** draft PR #965 only, no production or Render deployment, no persistent evidence import.

## The real PostgreSQL gate now passes

[**GitHub Actions #42562929833**](https://github.com/pdufa/pdufa-command-center/actions/runs/42562929833) completed **SUCCESS** on feature branch commit `e242944f61a77c6be064024a0560a4d0ef3e4dcc`, testing a **disposable PostgreSQL 16.6 service in GitHub Actions**. The test database `pdufa_vault_ephemeral` uses a synthetic test account and a localhost-only DSN; strict gating rejects remote hosts, alternate database names, non-test users, and an unset opt-in. This test never connects to live Neon or Render.

The actual PostgreSQL engine, not an SQLite emulation, accepted the additive vault schema using native `BYTEA`, survived a repeated idempotent initialization, and had its correct database trigger created once. Two independently versioned synthetic original-document bytes were encrypted with AES-256-GCM, received proper authenticated-data and source SHA-256 receipts, and survived connection disposal/reconnect. A test-only independent offline wrapping key successfully restored a synthetic source encryption key, allowing the saved ciphertext to be verified without returning plaintext. Wrong keys were rejected. PostgreSQL triggers rejected ordinary UPDATE, DELETE and TRUNCATE. Duplicate digest and reused declared-version insertion requests were rejected without changing the two existing receipts. The verified source and receipt chain remained intact; **0 clinical grades and FDA ABSTAIN**.

## Installed components

- `.github/workflows/main-medical-vault-postgres-acceptance.yml`: pinned branch- and repo-scoped, read-only GitHub permissions, disposable PostgreSQL 16.6 service. Test-only credentials are in the workflow and intentionally not production secrets; no Render or Neon keys are passed.
- `new-platform/backend/tests/test_medical_original_evidence_vault_postgres.py`: actual PostgreSQL DDL, native trigger, encrypted byte readback, source/declared-version constraints, hash-chain audit, connection persistence, and synthetic offline recovery.
- `new-platform/backend/app/medical_original_evidence_key_recovery.py`: no-IO, in-memory backup-envelope utility using independent AES-256-GCM wrapping key, distinct from the vault encryption key, with authenticated domain/label binding and fingerprint check. Does **not** generate, store, transfer or back up production credentials.
- `new-platform/backend/tests/test_medical_original_evidence_key_recovery.py`: random AES-256 material, nondeterministic nonce, wrong-key, wrong-label, tampering, and no-secret-in-envelope tests.
- `new-platform/frontend/app/predictions/assessment/PilotEncryptedEvidenceVaultStatus.tsx`: cites successful disposable PostgreSQL acceptance while explicitly preserving the status **STAGED / NOT ACTIVE**, source documents deposited **0**, and clinical grades **0/800**.

## What this proves — and what it does not

This is a **tested storage implementation**, not an active medical repository. The isolated Render service `pdufa-medical-intelligence-preview` is still on its existing branch with auto-deploy **OFF**. No production/service application keys, recovery wrapping keys, database grants, KMS account, escrow vault, cross-vendor backup or nonproduction Render deployment have been provisioned. Source files have not been ingested. The test-run key wrap is a **synthetic recovery drill only**, not a verified backup of a real key. Neon branchable object storage remains unavailable in the project's AWS us-west-2 region; no additional project or bucket was created.

**Remaining activation gates:**

1. **Separate migration and runtime PostgreSQL authority.** The current vault initializes schema through the application connection. Before real activation, use separately authorized migrations, restrict the runtime DB user, and validate least-privilege SELECT/INSERT and no UPDATE/DELETE/TRUNCATE/DDL. An owner/superuser can alter triggers; append-only triggers are not a defense against an owner.
2. **Actual key custody.** Independently generate the source AES key and a separate recovery wrapping key in trusted secret-management systems; establish dual-control restore and tested offsite backup. The sample wrapper is not a production KMS or automatic key rotation scheme.
3. **Production-quality evidence screening.** Confirm legal document-storage rights, malware scanning, source issuer/version provenance, data classification and encryption-retention policy. No PHI or confidential source datasets; connected project is not HIPAA-enabled.
4. **Document storage and disaster recovery.** Assess storage growth and PostgreSQL quota, encrypted DB backups and external receipt checkpointing, corruption/recovery workflows and retention.
5. **Manual isolated backend approval only.** Verify current Render database isolation, configure appropriately scoped credentials and perform a canary with a genuinely public authorized test document before enabling the feature flag. Do not add a public browser upload or dashboard secret.
6. **Independent scientific review remains separate.** The source vault cannot assign scientific method grades; a qualified reviewer must independently verify original evidence before append-only clinical score events can be authorized.

**Scientific prediction state unchanged:** 18 research-only source-mapped positions, 782 not mapped, 0/800 official scientific grades, FDA prediction **ABSTAIN**, calibrated accuracy **NOT_CALIBRATED**.

The [previous Revision 30 runbook](revision30-encrypted-original-evidence-vault-20261108.md) describes the initial vault design and Neon storage limitation.
