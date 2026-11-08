# Three-provider encrypted PDUFA recovery — installation plan

**State (2026-11-08): PREPARATION ONLY. No scheduled backups or remote cloud copies are verified.**

Approved destinations:
1. Amazon S3 — independent primary off-site copy.
2. Backblaze B2 — independent secondary off-site copy.
3. Apple iCloud Drive — third encrypted archive, synchronized from a user-controlled Mac/Windows computer.

The same encrypted archive must be copied byte-for-byte to all three. iCloud Drive synchronization is NOT a replacement for backups with retention/immutability. Verify remote Apple synchronization separately.

## Scope, established from the live project

Source-of-truth inventory includes:
- Neon PostgreSQL project `pdufa-new-persistent-db` and relevant databases on its default branch.
- Every independently confirmed active Render PostgreSQL database, including those described in `docs/RENDER_DATABASE_RECOVERY_RUNBOOK.md` after current inventory reconciliation.
- Applicable POOL/FOCUS Google Sheets exports and evidence datasets, full research provenance, historical read-only records, immutable prediction and assessment history.
- Git source at an exact commit, required application/research artifact manifests, non-secret configuration, deployment definitions, cron/workflow definitions and restore instructions.
- Any additional persistent object storage/assets discovered through the deployment inventory.

**Do not omit a data source simply because a user interface does not display it. Do not call a backup full or recoverable until each source has a verified dump and an isolated restore test.** Never include access tokens, DB passwords, private keys, .env files, cloud credentials or API secrets in the archive. Record separately which secrets must be re-provisioned.

Preserve read-only historical material; do not re-enable retired analysis/workspaces or modify POOL/FOCUS membership.

## What the new utility does

`scripts/replicate_recovery_archive.py` only accepts an existing `.age` encrypted file and checks its header. A header check **does not validate the recipient, encryption strength or ability to decrypt**. Confirm encryption/decryption by a separate isolated recovery rehearsal.

- `clouds`: uploads that exact file to both S3 and B2, then checks remote object length and recorded SHA-256 metadata; metadata checks alone are NOT proof that downloaded contents match.
- `verify-clouds`: downloads both uploaded objects and checks actual SHA-256. Does not imply database restore success.
- `icloud`: copies the same bytes into an EXISTING local iCloud Drive folder, checks local SHA-256, never overwrites conflicting files, and labels Apple remote synchronization as unverified until separately checked.

Cloud upload uses `boto3` (not installed by this commit). B2 is accessed through its S3-compatible endpoint. Store access keys in a secure job environment, never in command-line arguments, README, Git commits, or web assets.

## Account setup still required

**Amazon**: create/use a private versioned S3 bucket, configure Object Lock where supported and appropriate, least-privilege upload/verify access, retention/lifecycle policy, and region. Consider a separate read-only restore identity. Verify object-lock behavior using a test object.

**Backblaze**: create/use an independent private B2 bucket, configure its own retention/Object Lock and restricted application key, obtain the exact bucket region and S3 endpoint. Do not reuse AWS credentials. Verify retention using a test object.

**Apple**: identify a Mac or Windows computer signed into the owner's Apple Account and with iCloud Drive active, plus an existing PDUFA backups directory. Configure a local agent to retrieve the finished encrypted archive, stage it with `icloud`, and verify that it appears in iCloud Drive on a second signed-in Apple device. Apple does not provide an S3-compatible backend for a server cron job.

**Encryption**: store the `age` private decryption key separately from all three copies, plus an offline recovery key backup. Test decryptability in isolation. Encrypt before uploading.

## Environment variables for cloud replication

These values belong only in the authorized secret store of the actual backup-runner, not in repository files:

```text
PDUFA_AWS_BACKUP_BUCKET
PDUFA_AWS_BACKUP_REGION
PDUFA_AWS_BACKUP_KEY_ID
PDUFA_AWS_BACKUP_SECRET
PDUFA_B2_BACKUP_BUCKET
PDUFA_B2_BACKUP_REGION
PDUFA_B2_BACKUP_KEY_ID
PDUFA_B2_BACKUP_SECRET
PDUFA_B2_BACKUP_ENDPOINT
```

Do not paste secret values into a chat or issue.

## Manual usage after provisioning

```sh
python -m pip install boto3
python scripts/replicate_recovery_archive.py clouds --archive /private/pdufa-recovery-20261108.age --date 2026-11-08
python scripts/replicate_recovery_archive.py verify-clouds --archive /private/pdufa-recovery-20261108.age --date 2026-11-08

# On a signed-in Mac/Windows client, after securely receiving the EXACT same .age file:
python scripts/replicate_recovery_archive.py icloud --archive /private/pdufa-recovery-20261108.age --icloud-dir "/path/to/existing/iCloud Drive/PDUFA Backups"
```

The date used for verification must match upload. Do not mistake files staged in a local iCloud directory for confirmed remotely synced copies.

## Activation and acceptance gates

1. Inventory and export every active database and durable data source, with consistent snapshot boundaries; generate one complete manifest.
2. Create an encrypted `.age` archive and test decryption with a private key available only to the owner/recovery process. Keep source dump copies secure.
3. Provision independent buckets and least-privilege credentials, with tested retention/versioning protections.
4. Run `clouds`, then `verify-clouds`. Retain SHA-256, object IDs, lengths, date and run status in a non-secret backup ledger.
5. Enable the Mac/Windows iCloud relay, stage the exact archive and check remote Apple synchronization from a second device.
6. Restore each PostgreSQL dump into an isolated disposable database; compare schemas, row counts, representative keys and application invariants. Verify source and Google Sheets exports.
7. Only then enable **nightly** orchestration after the existing research jobs complete (with timeout/failure alerts and DST-safe scheduling), plus a weekly download integrity test and monthly isolated recovery rehearsal.
8. Maintain immutable retention and a separate restore credential policy; test a loss-of-one-vendor recovery scenario.
9. Reflect each provider's status independently: **Not Configured / Copy Uploaded / Integrity Verified / Restore Verified / Failed**, with run timestamp and failure reason. Never display 100% or “Protected” from successful scheduling alone.

**Current blockers:** cloud storage accounts/buckets and keys have not been confirmed in connected tooling; no Apple local sync machine is connected; no completed encrypted full-system export has been verified. No backup schedule is enabled by this branch. Cloud storage and requests may incur charges.
