"""Read-only verification of archived ClinicalTrials.gov records."""
import gzip
import hashlib
import json

from .scientific_registry_evidence import extract_trial_evidence


def verified_record_from_archive(nct_id: str, payload_gzip: bytes,
                                 expected_sha256: str) -> dict:
    """Check compression, byte integrity and trial identity before analysis."""
    if not isinstance(payload_gzip, bytes):
        raise ValueError("Archived payload must be bytes")
    raw = gzip.decompress(payload_gzip)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Archived record checksum mismatch")
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("Archived trial record must be an object")
    extract_trial_evidence(nct_id, record)  # Strict exact NCT identity check.
    return record


def evidence_from_archive(nct_id: str, payload_gzip: bytes, expected_sha256: str) -> dict:
    record = verified_record_from_archive(nct_id, payload_gzip, expected_sha256)
    return extract_trial_evidence(nct_id, record)
