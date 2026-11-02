# FDA OUTCOME — offline encrypted reviewer handoff (research only)

**Code ready for testing, NOT an activated export, completed durable upload or
FDA decision adjudication.** The PDUFA Research & Learning Google Drive holds
owner-only blank staging folders for Reviewer A, Reviewer B and Custody Baseline.
No private FDA source file was uploaded by this installation.

## Threat boundary and keys

The original 7 FDA source-review batches contain 14 blank role JSON files and
one SHA-256 custody baseline JSON. These are produced in restricted ephemeral
GitHub runner storage; don't upload them as plaintext or publish artifact URLs
that expose original application identity or PDF mapping.

This tool seals **15 separate encrypted envelopes**, using vetted
`cryptography` APIs: ephemeral X25519 ECDH, HKDF-SHA256 with a random
per-envelope salt and authenticated metadata, and AES-256-GCM with a random
96-bit nonce. Reviewer FIRST, reviewer SECOND and custody manifest must have
**three distinct independently trusted recipient public keys**. Role and
filename are authenticated; swapping envelopes or changing their bytes
breaks verification.

A recipient key is NOT verified merely by its name: authenticate the
recipient separately and verify its public-key SHA-256 fingerprint by a
trusted second channel before encrypting. The original reviewer credentials,
recipient private keys and any secrets must stay outside GitHub, CI secrets,
the public dashboard and Google Drive. Do not paste private keys into chat.

You can generate X25519 recipient key pairs on each recipient's own trusted
offline workstation using an approved key-management process, with secure
backup and private-key recovery instructions. The transfer CLI accepts
**base64-encoded raw 32-byte X25519 public keys** from three external
`.pub` files; it does not generate or persist user credentials. A
role-specific private key (`0600` owner-only on POSIX) is needed only for
a controlled offline restore. Keep the custody private key separate from
both reviewers' keys. This is **not** reviewer login/authentication.

## Offline sealing — outside repository

Install `cryptography` in the trusted local Python environment. The
example paths are placeholders and are NOT known working locations.

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/transfer_hop_fda_private_encrypted_archive.py \
  --encrypt-offline \
  --source-folder /private/validated-fda-review-batches \
  --new-output-folder /private/encrypted-fda-archive \
  --first-role-key-file /secure-keys/reviewer-a-x25519.pub \
  --second-role-key-file /secure-keys/reviewer-b-x25519.pub \
  --custody-role-key-file /secure-keys/custodian-x25519.pub
```

The source folder must contain the saved *original, frozen* 14 blank role
files and custody baseline, with intact role/source locks and restricted
permissions. The destination must be new, private and **not** inside the
repository or public artifact folders. After successful sealing, the
destination has seven FIRST encrypted files, seven SECOND encrypted files
and one CUSTODY encrypted baseline (`.fdaenc`). Only counts are printed.

**No cloud upload is performed by the command.** Before any external
transfer, explicitly confirm folder sharing and reviewer isolation,
which provider controls apply, archive retention and deletion policy,
key custody, audit-log availability, and the rights and identities of
the two qualified reviewers. Transfer **only the encrypted envelopes**,
partitioned by role, not the plaintext or the local baseline.

## Recovery test before declaring archival success

On a secured custodian workstation holding all three independent role
private keys:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/transfer_hop_fda_private_encrypted_archive.py \
  --recover-offline \
  --source-folder /private/downloaded-15-encrypted-envelope-files \
  --new-output-folder /private/controlled-recovery-check \
  --first-role-key-file /secure-keys/reviewer-a-x25519.key \
  --second-role-key-file /secure-keys/reviewer-b-x25519.key \
  --custody-role-key-file /secure-keys/custodian-x25519.key
```

This requires all **15** authentic encrypted envelopes, rejects wrong keys,
role swaps and modified ciphertext, recreates plaintext in a **new restricted
local** folder, and reruns the original FDA blank-source checksum and grouping
verification (7 groups of batches, 124 source references, 101 research
groupings). The restored plaintext must never be uploaded as the backup
artifact; keep it controlled and remove it only under an approved evidence
retention procedure.

The exercise is valid as *cryptographic recovery of blank research packets*
only when independently run from a **downloaded, durable stored copy**.
A roundtrip wholly inside a CI runner is a software test, **not** proof
of persistent Drive backup, independent reviewer access, regulatory
adjudication, model training eligibility or scientific calibration.

## Installation gates remaining

- [ ] Obtain three independently verified public keys from authorized
  reviewer A, reviewer B, and an independent custody officer.
- [ ] Explicitly authorize a narrowly scoped, encrypted-only storage transfer
  and configure a secure exchange without leaking private runner inputs.
- [ ] Check Google Drive sharing and segregate permissions for each role,
  including review of inherited access; the blank folders are currently
  owner-only and no reviewer has been assigned.
- [ ] Demonstrate an off-runner, download-and-restore test using the intended
  permanent storage provider and independently secured keys.
- [ ] Obtain and authenticate two qualified original FDA source reviewers
  and a separate adjudicator; verify individual original NDA/BLA cycles
  against FDA action documents including a complete nonapproval population.
- [ ] Validate no leakage, historical cohort completeness, chronological
  holdouts and calibrated FDA approval probabilities before enabling scores.

**Currently:** 0 adjudicated FDA review-cycle outcomes, 0 model-eligible
historical decisions, incomplete FDA decision denominator, FDA probability
null. Nightly scans, GEM JR/GEM FS/FA, WT, and production trading remain
untouched.
