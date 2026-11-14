# FDA visual-review intake: independent recipient public key and owner-only storage

**Status: draft research, not a completed reviewer transfer.**
**Repository visibility: PUBLIC.** No original FDA image bytes, page-to-application
maps, decryption private keys, reviewer notes or recipient identities belong in
this repository, public GitHub Actions logs or public artifacts.

## Verified storage staging

The user's connected Google Drive includes an existing FDA independent-review
workspace and distinct unassigned Reviewer A, Reviewer B and custody
folders. The new encrypted visual intake subfolder is placed under that
workspace. Its Google Drive permission metadata was read back as
**not shared**, with only the owner permission, and its contents were
verified **empty**. The Drive folder identifier and owner email are
intentionally **not present in this public research repository**.
Google Drive owner-only permissions provide a private destination, not
automatic delivery or reviewer authentication.

## New recipient-held X25519 encryption protocol

`app/hop_fda_visual_recipient_envelope.py` supports sealing the actual
19-source-image archive using **only a recipient's verified X25519 public
key**. The encrypting runner derives a fresh AES-256 key using ephemeral
X25519 ECDH, HKDF-SHA256 and a 16-byte random salt, and then uses the
existing source-locked AES-256-GCM archive encoder. The outer envelope
records only a public-key fingerprint, ephemeral public key, derivation
salt and authenticated ciphertext. A distinct receiver with the matching
private key can decrypt and recheck the **19 image hashes** and the two
private source manifests. Wrong recipients, tampering, conflicting
source PNG digests and false model-clearance flags are rejected.

This protocol avoids placing a shared, reusable AES secret into GitHub
Actions, CI variables or Google Drive. The actual recipient private key
is **not generated in GitHub Actions** and must remain outside GitHub
and the shared Drive workspace. The source filenames and page mappings
are encrypted inside the envelope, not written in the audit metadata.

An offline script `scripts/manage_hop_fda_visual_recipient_keys.py`
provides separate explicit operations to:
- Generate a new local recipient keypair in an owner-only
  restricted **POSIX/WSL directory outside the repository**.
- Encrypt an existing private 19-image source worklist using **only**
  that recipient's public-key file.
- Decrypt an encrypted envelope into a NEW restricted private local
  directory with the separately held private key.

On native Windows, POSIX owner-only permission checks are not sufficient
to verify NTFS ACLs. The local key-generation/decryption helper fails
closed; the owner must use a restricted WSL/Linux environment or another
approved operating-system credential store. **Do not create keys in a
Google Drive-synced folder, browser download folder shared with others,
repository, GitHub action log or this chat.**

Example **on a private owner-controlled WSL/Linux machine**:

```bash
# This creates a NEW local directory and does not print the secret key.
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/manage_hop_fda_visual_recipient_keys.py \
  --create-local-recipient-keys \
  --new-private-key-folder /home/USER/.private-pdufa-fda-review-keys
```

Store the `fda_visual_review_recipient_private.hex` file only in
secure offline storage or a controlled secrets manager. The separate
`fda_visual_review_recipient_public.hex` is safe to submit to the
review-preparation workflow **after independent key-fingerprint
confirmation**.

A trusted operator with the newly regenerated private FDA images can
then run:

```bash
PYTHONPATH=new-platform/backend python \
  new-platform/backend/scripts/manage_hop_fda_visual_recipient_keys.py \
  --encrypt-with-public-key \
  --recipient-public-key-file /secure/public/fda_visual_review_recipient_public.hex \
  --private-image-dir /secure/source/no_text_visual_images \
  --private-batch1-manifest /secure/source/no_text_visual_manifest_batch1.json \
  --private-batch2-manifest /secure/source/no_text_visual_manifest_batch2.json \
  --encrypted-output /secure/transfer/fda_visual_pages_19.recipient-encrypted
```

Only **the recipient-encrypted file** should be uploaded to the verified
owner-only Google Drive intake. No Drive upload or role-sharing automation
is activated in the research draft, and no remote file exists yet. The
recipient can later decrypt **locally**, supplying the same separately
held private key file, and must still independently inspect the source
pages before any regulatory decision is adjudicated.

## Completion gates

| Requirement | Current state |
|---|---|
| Actual original FDA page-PNG source set reproduced | 19 PNGs, transient CI only |
| Real-source ephemeral symmetric AES-GCM roundtrip | Verified |
| Recipient-public-key X25519 envelope implementation | Added; tests required |
| Google Drive private destination and ACL | Verified owner-only and empty |
| Reviewer-controlled **permanent** recipient private key | **Not configured** |
| Independently confirmed matching recipient public key | **Not supplied** |
| Durable recipient-encrypted archive in Drive | **Not uploaded** |
| Independent reviewer assignments and human page inspections | **Zero** |
| Original NDA/BLA decision-cycle adjudications | **Zero** |
| Model-eligible original FDA outcomes / approval probability | **Zero / unavailable** |

Even when a recipient-encrypted bundle is placed in private Drive, the
complete historical original NDA/BLA approved/nonapproved decision population
and independent FDA action-cycle evidence are still needed before scientific
prediction calibration. The PR remains unmerged and does not change
GEM JR/GEM FS/FA presets, live scanning, trading, or production deployment.
