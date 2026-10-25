"""Offline scientific source integrity and no-fabricated-score regressions."""
from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from app.scientific_assessment import assess, DOMAINS
from app.scientific_stored_record import MAX_ARCHIVED_JSON_BYTES, evidence_from_archive

NCT = "NCT04280705"


def archive(record):
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return gzip.compress(canonical), hashlib.sha256(canonical).hexdigest()


def test_source_metadata_and_results_never_invent_six_domain_scores():
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT},
            "designModule": {"designInfo": {"allocation": "RANDOMIZED"},
                             "enrollmentInfo": {"count": 1062}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
            "statusModule": {"overallStatus": "COMPLETED"},
        },
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [{"title": "Overall survival", "analysisGroups": []}]
            }
        },
    }
    payload, checksum = archive(record)
    extracted = evidence_from_archive(NCT, payload, checksum)
    assert extracted["nctId"] == NCT
    assert extracted["verificationStatus"] == "source_record_only"
    assert extracted["metadata"]["enrollment"] == 1062
    assert extracted["sourceUrl"] == "https://clinicaltrials.gov/study/" + NCT
    assert extracted["scoringEvidence"] == {}
    score = assess(extracted["scoringEvidence"])
    assert score["overall_score"] is None
    assert score["status"] == "insufficient_evidence"
    assert len(score["domains"]) == len(DOMAINS) == 6
    assert all(v["score"] is None and not v["verified"] for v in score["domains"].values())


@pytest.mark.parametrize("digest", ["invalid", "X" * 64, "f" * 63, None])
def test_malformed_hash_rejected_without_parsing_source(digest):
    payload, _ = archive({"protocolSection": {"identificationModule": {"nctId": NCT}}})
    with pytest.raises(ValueError, match="SHA-256"):
        evidence_from_archive(NCT, payload, digest)


def test_checksum_mismatch_fails_closed():
    payload, _ = archive({"protocolSection": {"identificationModule": {"nctId": NCT}}})
    with pytest.raises(ValueError, match="checksum mismatch"):
        evidence_from_archive(NCT, payload, "0" * 64)


def test_expanded_gzip_payload_beyond_limit_is_rejected():
    oversize = gzip.compress(b" " * (MAX_ARCHIVED_JSON_BYTES + 1), compresslevel=1)
    with pytest.raises(ValueError, match="expanded size limit"):
        evidence_from_archive(NCT, oversize, "0" * 64)


def test_mismatched_trial_identity_never_accepted():
    payload, checksum = archive({
        "protocolSection": {"identificationModule": {"nctId": "NCT02142738"}}
    })
    with pytest.raises(ValueError, match="identity mismatch"):
        evidence_from_archive(NCT, payload, checksum)


@pytest.mark.parametrize("bad_record", [[], None, "not-an-object", 42])
def test_non_object_archived_data_is_rejected(bad_record):
    payload, checksum = archive(bad_record)
    with pytest.raises(ValueError, match="must be an object"):
        evidence_from_archive(NCT, payload, checksum)
