"""End-to-end RFC3161 cryptography test with a locally generated TEST authority.

A local CA is NOT an independently trusted timestamp authority. This test
proves parser/verification interoperability only.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess

import pytest

from research.fda_rfc3161_token_time import verify_token_time_before_cutoff


def _run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=20)


def test_locally_issued_rfc3161_token_round_trip(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("OpenSSL unavailable")
    key = tmp_path / "tsa.key"
    cert = tmp_path / "tsa.pem"
    serial = tmp_path / "tsa.srl"
    query = tmp_path / "request.tsq"
    response = tmp_path / "response.tsr"
    config = tmp_path / "tsa.cnf"
    payload = b"research-only prospective freeze fixture"
    digest = sha256(payload).hexdigest()
    try:
        _run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", str(key), "-out", str(cert), "-days", "2",
             "-subj", "/CN=UNTRUSTED LOCAL TEST TSA",
             "-addext", "extendedKeyUsage=critical,timeStamping")
        serial.write_text("01\n")
        config.write_text(
            "[tsa]\ndefault_tsa = local\n[local]\n"
            f"serial = {serial}\n"
            f"signer_cert = {cert}\n"
            f"signer_key = {key}\n"
            f"certs = {cert}\n"
            "signer_digest = sha256\ndefault_policy = 1.2.3.4\n"
            "digests = sha256\naccuracy = secs:1\n"
            "ordering = yes\ntsa_name = yes\ness_cert_id_chain = no\n"
        )
        _run("openssl", "ts", "-query", "-digest", digest, "-sha256",
             "-cert", "-out", str(query))
        _run("openssl", "ts", "-reply", "-config", str(config),
             "-queryfile", str(query), "-out", str(response))
        token = tmp_path / "token.der"
        _run("openssl", "ts", "-reply", "-in", str(response),
             "-token_out", "-out", str(token))
        ca = cert.read_bytes()
        status = verify_token_time_before_cutoff(
            token.read_bytes(), "2099-01-01T00:00:00Z",
            expected_imprint_sha256=digest,
            trusted_ca_pem=ca,
            pinned_ca_bundle_sha256=sha256(ca).hexdigest(),
        )
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"Local RFC3161 fixture could not be constructed: {exc.stderr}")
    assert status == "TOKEN_TIME_BEFORE_CUTOFF_CA_POLICY_NOT_INDEPENDENTLY_ATTESTED"
