"""Real FDA-hosted PDF bytes: matching historical source hashes, not model labels."""
from copy import deepcopy
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from app.hop_fda_original_capture_receipts import (
    audit_real_fda_capture_receipts, load_real_fda_capture_receipts,
    verify_source_artifact_zip,
)

BASE = Path(__file__).resolve().parents[1] / "app" / "research_sources"
CUTOFF = date(2026, 10, 28)
NDA_ID = "NDA213973_ORIGINAL_1_20200515_APPROVED"
BLA_ID = "BLA761303_ORIGINAL_1_20240322_CRL"


def manifests():
    return (
        json.loads((BASE / "hop_fda_original_byte_capture_receipts.json").read_text()),
        json.loads((BASE / "hop_fda_primary_action_letter_samples.json").read_text()),
    )


def audit(register=None, letters=None, as_of=CUTOFF):
    source, letter_data = manifests()
    return audit_real_fda_capture_receipts(
        register if register is not None else source,
        letters if letters is not None else letter_data, as_of=as_of,
    )


def test_two_real_fda_pdf_hashes_recomputed_from_original_bytes_are_now_versioned():
    r = load_real_fda_capture_receipts(as_of=CUTOFF)
    assert r["status"] == "FDA_ORIGINAL_PDF_BYTES_FINGERPRINTED_RESEARCH_ONLY"
    assert r["capturedPdfRecords"] == 2
    assert r["captureWorkflowRunId"] == 40716416188
    assert r["captureArtifactId"] == 12828286739
    assert r["artifactRetentionDays"] == 14
    assert r["artifactAvailabilityNow"] == "NOT_CHECKED"
    assert r["artifactZipSha256"] == "765dc93ca2fafa048dceb2d48221d00b74eaa909cbc24b3c570a33d6ca7060eb"
    assert r["sourceBytesCommittedToRepository"] is False
    observed = {item["recordId"]: item for item in r["records"]}
    assert set(observed) == {NDA_ID, BLA_ID}
    nda, bla = observed[NDA_ID], observed[BLA_ID]
    assert nda["pdfSha256"] == "5c559425eddb609ab8c2c2545413860947ca0f30e9a937fd81eca502dba4626e"
    assert bla["pdfSha256"] == "394bc0667eb2704b34fbb40046e068b0c087e07865dd89658ef4f2f858c8f880"
    assert nda["capturedBytes"] == 768468 and nda["capturedPageCount"] == 8
    assert bla["capturedBytes"] == 168170 and bla["capturedPageCount"] == 7
    assert nda["sourceDocumentReference"] == "4609421"
    assert bla["sourceDocumentReference"] == "5352252"
    assert nda["signedFdaActionDate"] == "2020-05-15"
    assert bla["signedFdaActionDate"] == "2024-03-22"
    for row in observed.values():
        assert row["pdfFirstPublicDate"] is None
        assert row["htmlLastModifiedIsFirstPublication"] is False
        assert row["exactCycleIndependentReviewerCertified"] is False
        assert row["modelEligible"] is False
    assert r["trainingAuthorized"] is False
    assert r["approvalProbability"] is None
    assert r["independentlyVerifiedModelCycles"] == 0
    assert r["historicalRealBacktests"] == 0


@pytest.mark.parametrize("changed", [
    lambda data: data["receipts"][0].update(pdf_sha256="a"*64),
    lambda data: data["receipts"][0].update(pdf_sha256="bad"),
    lambda data: data["receipts"][0].update(response_byte_length=0),
    lambda data: data["receipts"][0].update(response_byte_length=True),
    lambda data: data["receipts"][0].update(http_status=302),
    lambda data: data["receipts"][0].update(redirected=True),
    lambda data: data["receipts"][0].update(content_type="text/html"),
    lambda data: data["receipts"][0].update(original_fda_pdf_first_publication_date_verified="2020-05-15"),
    lambda data: data["receipts"][0].update(eligible_for_model_training=True),
    lambda data: data["receipts"][0].update(independently_adjudicated_fda_review_cycle=True),
    lambda data: data["receipts"][0].update(pdf_pages=0),
    lambda data: data["receipts"][0].update(document_reference_id="0000000"),
    lambda data: data["receipts"][0].update(first_page_action_observed="COMPLETE RESPONSE"),
    lambda data: data["receipts"][0].update(first_page_application_observed="BLA 761303"),
    lambda data: data["receipts"][0].update(original_url="https://fake.fda.gov/test.pdf"),
    lambda data: data["receipts"][0].update(retrieval_observed_at_utc="2026-10-29T15:29:20+00:00"),
    lambda data: data["receipts"][0].update(retrieval_observed_at_utc="2026-10-28T15:29:20"),
    lambda data: data["receipts"][0].update(http_last_modified_header=""),
    lambda data: data["receipts"][1].update(pdf_sha256=data["receipts"][0]["pdf_sha256"]),
    lambda data: data["receipts"][1].update(record_id=data["receipts"][0]["record_id"]),
    lambda data: data["source_capture"].update(original_fda_pdf_files_persisted_in_git=True),
    lambda data: data["source_capture"].update(github_artifact_url="https://other.com/false-artifact"),
    lambda data: data["source_capture"].update(artifact_sha256="fake"),
    lambda data: data["source_capture"].update(artifact_retention_days=10000),
    lambda data: data.update(model_eligible_records=2),
])
def test_receipt_tampering_or_unearned_regulatory_certification_rejected(changed):
    sources, letters = manifests()
    changed(sources)
    with pytest.raises(ValueError):
        audit(register=sources, letters=letters)


def test_retrospective_date_before_oct_28_cannot_observe_later_pdf_capture():
    for cutoff in [date(2020, 5, 15), date(2024, 3, 25),
                   date(2025, 12, 31), date(2026, 10, 27)]:
        result = audit(as_of=cutoff)
        assert result["status"] == "CAPTURE_RECEIPTS_NOT_AVAILABLE_AT_AS_OF"
        assert result["capturedPdfRecords"] == 0
        assert result["approvalProbability"] is None
        assert result["trainingAuthorized"] is False


def test_not_a_canonical_review_cycle_or_probabilistic_training_label():
    from app.hop_fda_public_disclosure_clock import load_historical_fda_public_outcome_packet
    packet = load_historical_fda_public_outcome_packet(as_of=CUTOFF)
    assert packet["originalPdfCaptureResearch"]["capturedPdfRecords"] == 2
    assert packet["originalPdfCaptureResearch"]["independentlyVerifiedModelCycles"] == 0
    assert packet["publicDisclosureResearch"]["totalPublicReleaseLeads"] == 3
    assert packet["actionLetterResearch"]["sourceLettersInspected"] == 2
    assert packet["independentModelEligibleCycles"] == 0
    assert packet["independentHistoricalBacktests"] == 0
    assert packet["approvalProbability"] is None
    assert packet["tradeAuthorized"] is False


def _synthetic_artifact():
    register, _ = manifests()
    files = {}
    for row in register["receipts"]:
        case = row["record_id"]
        pdf = b"%PDF-1.7\n" + (case.encode() + b"\n") * 45 + b"%%EOF\n"
        row["pdf_sha256"] = hashlib.sha256(pdf).hexdigest()
        row["response_byte_length"] = len(pdf)
        files[f"{case}.pdf"] = pdf
        files[f"{case}.provenance.json"] = json.dumps({
            "sha256OfCapturedBytes": row["pdf_sha256"],
            "byteLength": len(pdf),
            "exactRequestedFdaUrl": row["original_url"],
            "modelEligible": False,
        }).encode()
    files["source-capture-summary.json"] = b'{"trainingAuthorized": false}\n'
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zip_:
        for key, value in files.items():
            zip_.writestr(key, value)
    blob = bio.getvalue()
    register["source_capture"]["artifact_sha256"] = hashlib.sha256(blob).hexdigest()
    return register, blob


def test_standalone_artifact_rehash_proves_bytes_not_fda_prediction():
    register, blob = _synthetic_artifact()
    out = verify_source_artifact_zip(blob, register)
    assert out["status"] == "SOURCE_BYTES_AND_CAPTURE_METADATA_HASHES_RECOMPUTED"
    assert out["matchedPdfDocuments"] == 2
    assert out["firstPublicLetterDateVerified"] is False
    assert out["independentReviewCycleAdjudication"] is False
    assert out["modelEligibleRecords"] == 0
    assert out["approvalProbability"] is None
    with pytest.raises(ValueError, match="SHA"):
        verify_source_artifact_zip(blob + b"tamper", register)


def test_unexpected_zip_member_or_corrupt_pdf_is_blocked():
    register, blob = _synthetic_artifact()
    a = io.BytesIO()
    with zipfile.ZipFile(a, "w") as out, zipfile.ZipFile(io.BytesIO(blob)) as prior:
        for name in prior.namelist():
            out.writestr(name, prior.read(name))
        out.writestr("../unexpected.txt", b"not allowed")
    register["source_capture"]["artifact_sha256"] = hashlib.sha256(a.getvalue()).hexdigest()
    with pytest.raises(ValueError, match="Unexpected"):
        verify_source_artifact_zip(a.getvalue(), register)
