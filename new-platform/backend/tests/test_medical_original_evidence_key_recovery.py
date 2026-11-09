"""Synthetic recovery drills; no real keys, files, artifacts or backend secrets."""
from __future__ import annotations
import copy
import json
import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app import medical_original_evidence_key_recovery as recovery


def keys():
    return os.urandom(32),os.urandom(32)


def test_distinct_keys_wrap_and_restore_with_no_plaintext_in_envelope():
    original,offline=keys()
    envelope=recovery.wrap_key_for_offline_backup(
        original,offline,key_label="ACACIA_PUBLIC_EVIDENCE_KEY_V1")
    assert envelope["schema"]==recovery.SCHEMA
    assert envelope["scope"]==recovery.SCOPE
    assert envelope["keyLabel"]=="ACACIA_PUBLIC_EVIDENCE_KEY_V1"
    assert len(envelope["wrappedKeyB64"])>48
    exported=json.dumps(envelope,sort_keys=True)
    assert original.hex() not in exported
    assert offline.hex() not in exported
    assert len(recovery.envelope_integrity_digest(envelope))==64
    restored=recovery.restore_key_from_offline_backup(
        envelope,offline,expected_label="ACACIA_PUBLIC_EVIDENCE_KEY_V1")
    assert restored==original
    # Real AES-GCM ciphertext is decryptable with recovered key; metadata only
    # is included in the backup and no source or plaintext document is stored.
    nonce=os.urandom(12)
    aad=b"source receipt identity in nonproduction drill"
    ciphertext=AESGCM(original).encrypt(nonce,b"synthetic source evidence",aad)
    assert AESGCM(restored).decrypt(nonce,ciphertext,aad)==b"synthetic source evidence"


def test_backup_encryption_is_nondeterministic_and_namespaces_are_authenticated():
    original,offline=keys()
    a=recovery.wrap_key_for_offline_backup(original,offline,key_label="ACACIA_V1")
    b=recovery.wrap_key_for_offline_backup(original,offline,key_label="ACACIA_V1")
    assert a["nonceB64"]!=b["nonceB64"]
    assert a["wrappedKeyB64"]!=b["wrappedKeyB64"]
    assert recovery.envelope_integrity_digest(a)!=recovery.envelope_integrity_digest(b)
    for field,replacement in (
        ("keyLabel","OTHER_VAULT"),
        ("scope","OTHER_PROJECT"),
        ("schema","FAKE_ENVELOPE"),
        ("wrappedKeyB64",b["wrappedKeyB64"]),
        ("nonceB64",b["nonceB64"]),
        ("publicKeyFingerprintSha256","0"*64),
    ):
        corrupted=copy.deepcopy(a)
        corrupted[field]=replacement
        with pytest.raises(recovery.KeyRecoveryError):
            recovery.restore_key_from_offline_backup(
                corrupted,offline,expected_label="ACACIA_V1")


def test_wrong_recovery_key_never_restores_and_does_not_reveal_original():
    original,offline=keys()
    envelope=recovery.wrap_key_for_offline_backup(original,offline,key_label="ACACIA_V1")
    with pytest.raises(recovery.KeyRecoveryError,match="authentication failed") as e:
        recovery.restore_key_from_offline_backup(envelope,os.urandom(32),
                                                  expected_label="ACACIA_V1")
    assert original.hex() not in str(e.value)
    assert offline.hex() not in str(e.value)


def test_same_key_and_non_256bit_material_are_rejected():
    original,offline=keys()
    with pytest.raises(recovery.KeyRecoveryError,match="independent"):
        recovery.wrap_key_for_offline_backup(original,original,key_label="ACACIA_V1")
    for bad in (b"",b"1234",b"x"*31,b"x"*33):
        with pytest.raises(recovery.KeyRecoveryError):
            recovery.wrap_key_for_offline_backup(bad,offline,key_label="ACACIA_V1")
        with pytest.raises(recovery.KeyRecoveryError):
            recovery.wrap_key_for_offline_backup(original,bad,key_label="ACACIA_V1")
        with pytest.raises(recovery.KeyRecoveryError):
            recovery.restore_key_from_offline_backup({},bad,expected_label="ACACIA_V1")


def test_malformed_envelope_never_skips_integrity_check():
    original,offline=keys()
    envelope=recovery.wrap_key_for_offline_backup(original,offline,key_label="ACACIA_V1")
    variants=[
        None,{},{"untrusted":"value"},
        {**envelope,"encryptionKey":original.hex()},
        {**envelope,"nonceB64":"not base64!"},
        {**envelope,"nonceB64":"eA=="},
        {**envelope,"wrappedKeyB64":"eA=="},
        {**envelope,"keyLabel":"../../ACACIA_V1"},
        {**envelope,"publicKeyFingerprintSha256":"INVALID"},
    ]
    for altered in variants:
        with pytest.raises(recovery.KeyRecoveryError):
            recovery.restore_key_from_offline_backup(altered,offline,expected_label="ACACIA_V1")
