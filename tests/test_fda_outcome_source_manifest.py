from dataclasses import replace
from hashlib import sha256

from research.fda_outcome_source_manifest import OutcomeSourceManifest, inspect_outcome_source


def test_fda_looking_source_does_not_prove_authenticity(tmp_path):
    path = tmp_path / "decision.pdf"
    path.write_bytes(b"research fixture")
    manifest = OutcomeSourceManifest(
        "TRIAL-1", "NDA-123456", "PASS",
        "https://www.fda.gov/drugs/example",
        sha256(path.read_bytes()).hexdigest(),
    )
    result = inspect_outcome_source(manifest, path, expected_trial_id="TRIAL-1")
    assert result.status == "LOCAL_BYTES_MATCH_FDA_ORIGIN_UNVERIFIED"
    assert not result.independently_authenticated


def test_domain_spoof_and_wrong_trial_rejected(tmp_path):
    path = tmp_path / "decision.pdf"
    path.write_bytes(b"fixture")
    manifest = OutcomeSourceManifest(
        "TRIAL-1", "NDA-123456", "CRL",
        "https://www.fda.gov.evil.example/letter",
        sha256(path.read_bytes()).hexdigest(),
    )
    assert inspect_outcome_source(
        manifest, path, expected_trial_id="TRIAL-1"
    ).status == "NON_FDA_SOURCE"
    assert inspect_outcome_source(
        manifest, path, expected_trial_id="TRIAL-2"
    ).status == "TRIAL_ID_MISMATCH"


def test_document_tampering_rejected(tmp_path):
    path = tmp_path / "decision.pdf"
    path.write_bytes(b"modified")
    manifest = OutcomeSourceManifest(
        "TRIAL-1", "NDA-123456", "EXTENSION",
        "https://fda.gov/example", "0" * 64,
    )
    assert inspect_outcome_source(
        manifest, path, expected_trial_id="TRIAL-1"
    ).status == "DOCUMENT_DIGEST_MISMATCH"
