# FDA OUTCOME — one-primary-reviewer encrypted handoff (research only)

**Scope:** Optional single qualified PRIMARY reviewer, plus an independent
CUSTODY keyholder. A routine second reviewer and second-reviewer encryption
key are **not required**. Separate legacy FIRST/SECOND/CUSTODY tools remain
unchanged and available for disputed or higher-risk records.

## What is installed

The offline archive tool accepts exactly the seven **blank**
`*_PRIMARY_unreviewed.json` work batches prepared under the isolated FDA
research branch, covering **124** source references in **101** preliminary
groups. It verifies source locks, all unchanged evidence and model flags,
contiguous source membership and deterministic grouping. It encrypts each
batch to the independently authenticated primary reviewer's X25519 public key.
An eighth encrypted file contains a checksum baseline, encrypted to the
independent custodian's **different** X25519 public key.

Encryption uses an ephemeral X25519 exchange, HKDF-SHA256 and AES-256-GCM,
with fresh salts and nonces and authenticated role/filename/key-fingerprint
metadata. Ciphertext contains no plaintext FDA source records.

The tool does not create public or private encryption keys, authenticate
people, upload files, send messages or validate FDA outcomes. It requires two
separately verified externally managed public keys (PRIMARY and CUSTODY).
Verify recipient identity and public-key SHA-256 fingerprints out of band.
**Do not put private keys in chat, GitHub, Google Drive or CI logs.**

## Offline sealing

The original research workflow prepares seven private primary-only source
worksheets in runner-temp private storage. This tooling does not preserve or
transfer those ephemeral files automatically. On an access-controlled
workstation where those files have been securely delivered and verified:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/transfer_hop_fda_single_primary_encrypted_archive.py \
  --encrypt-offline \
  --source-folder /private/primary_fda_blank_batches \
  --new-output-folder /private/primary_fda_encrypted_archive \
  --primary-role-key-file /keys/verified_primary.pub \
  --custody-role-key-file /keys/verified_custody.pub
```

The two `.pub` files must contain **base64-encoded raw 32-byte X25519
public keys**. The tool expects a *new*, non-repository output folder and
refuses overwriting. It writes **seven PRIMARY encrypted files and one
CUSTODY encrypted baseline** with restricted local permissions, and prints
counts only. No cloud upload is performed.

Only after explicit approval of the recipient, key handling and access
controls should encrypted PRIMARY envelopes be placed into the owner-only
primary-reviewer Google Drive staging folder, and the separate encrypted
CUSTODY envelope into its distinct owner-only custody staging folder. The
optional second-review folder should remain empty unless a case is escalated.

## Controlled offline recovery

On a restricted, locally managed workstation where the authorized keyholders
can make both private keys available under an approved recovery procedure,
verify a *downloaded copy* of all eight encrypted packages:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/transfer_hop_fda_single_primary_encrypted_archive.py \
  --recover-offline \
  --source-folder /private/downloaded_primary_encrypted_archive \
  --new-output-folder /private/controlled_primary_restore \
  --primary-role-key-file /keys/primary_private.key \
  --custody-role-key-file /keys/custody_private.key
```

Private key files must contain base64-encoded raw 32-byte X25519 private keys
and use owner-only filesystem permissions. Recovery decrypts into a **new
restricted local destination**, recomputes all FDA source hash locks, source
groups, seven batch memberships and archived SHA checksums, and refuses
incorrect keys, modified ciphertext, missing/extra packages, duplicate
references and model eligibility claims. The plaintext recovery copy must
remain protected. A purely local round-trip test is **not** proof of durable
storage or verified recipient access.

## Explicit remaining gates

- [ ] Identify and independently authenticate **one** qualified primary
      reviewer and a different authorized custody keyholder.
- [ ] Obtain and authenticate the PRIMARY and CUSTODY encryption public keys
      using a trusted channel, and agree on safe private-key recovery.
- [ ] Demonstrate an encrypted-only transfer to the owner's existing Drive
      staging folders, with least-privilege file access and no plaintext in
      Drive, repository or public CI artifacts.
- [ ] Perform an off-runner download-and-restore integrity exercise.
- [ ] Conduct actual original FDA source review, escalating missing original
      PDFs, ambiguous identities, inconclusive dates/cycles or conflicts to an
      independently qualified additional source check.
- [ ] Separately construct the full NDA/BLA original-decision sampling frame,
      verify publication-time cutoffs and calibrate and evaluate historical
      models before any FDA outcome probability or approval grade is available.

**No actual FDA reviewer has submitted authenticated evidence yet.**
Independently adjudicated original FDA review-cycle outcomes: **0**;
model-eligible records: **0**; complete historical denominator: **false**;
prediction probability: **null**. No production/nightly scan, GEM JR/GEM
FS/FA, WT, model, trading or credentials are changed.
