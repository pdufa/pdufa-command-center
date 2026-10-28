"""Source-bound FDA HTTPS capture: actual bytes != independent review."""
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from pathlib import Path
import hashlib
import json

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("fda_original_capture", ROOT / "scripts" / "capture_hop_fda_original_https.py")
capture = module_from_spec(spec)
spec.loader.exec_module(capture)
MANIFEST = json.loads((
    ROOT / "app" / "research_sources" / "hop_fda_primary_action_letter_samples.json"
).read_text(encoding="utf-8"))
GOOD_ID = "NDA213973_ORIGINAL_1_20200515_APPROVED"
CRL_ID = "BLA761303_ORIGINAL_1_20240322_CRL"


def test_pdf():
    # Deliberate synthetic bytes: header/EOF only, not an actual FDA document.
    return b"%PDF-1.6\n" + (b"research-only synthetic input\n" * 70) + b"\n%%EOF\n"


class Response(BytesIO):
    def __init__(self, content, *, url, status=200, content_type="application/pdf"):
        super().__init__(content)
        self.url = url
        self.status = status
        self.headers = {
            "Content-Type": content_type,
            "Last-Modified": "Wed, 28 Oct 2026 14:00:00 GMT",
            "Date": "Wed, 28 Oct 2026 15:00:00 GMT",
            "ETag": "research-test-only",
        }

    def geturl(self):
        return self.url


class Opener:
    def __init__(self, payload=None, *, modified_url=None, status=200, content_type="application/pdf"):
        self.payload = test_pdf() if payload is None else payload
        self.modified_url = modified_url
        self.status = status
        self.content_type = content_type
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request.full_url, request.get_method(), timeout))
        return Response(
            self.payload, url=self.modified_url or request.full_url,
            status=self.status, content_type=self.content_type,
        )


def test_exact_fda_pdf_capture_is_hashable_but_not_certified(tmp_path):
    opener = Opener()
    at = datetime(2026, 10, 28, 15, 0, tzinfo=timezone.utc)
    captured = capture.capture_fda_pdf_bytes(
        MANIFEST, GOOD_ID, tmp_path, opener=opener, observed_at=at,
    )
    source = MANIFEST["letters"][0]["original_document_url"]
    assert opener.calls == [(source, "GET", 30)]
    assert (tmp_path / f"{GOOD_ID}.pdf").read_bytes() == test_pdf()
    assert captured["sha256OfCapturedBytes"] == hashlib.sha256(test_pdf()).hexdigest()
    assert captured["byteLength"] == len(test_pdf())
    assert captured["httpStatus"] == 200
    assert captured["redirected"] is False
    assert captured["observedAtUtc"] == "2026-10-28T15:00:00+00:00"
    assert captured["httpLastModifiedHeader"].startswith("Wed")
    # Response metadata is not first-publication chronology.
    assert captured["FDAletterFirstPublishedAt"] is None
    assert captured["sourceDocumentIndependentlyReviewed"] is False
    assert captured["documentReferenceAndActionIndependentlyAdjudicated"] is False
    assert captured["historicalReviewCycleVerified"] is False
    assert captured["frozenPredecisionFeaturesVerified"] is False
    assert captured["modelEligible"] is False
    assert captured["approvalProbability"] is None
    recorded = json.loads((tmp_path / f"{GOOD_ID}.provenance.json").read_text())
    assert recorded == captured


def test_never_rewrites_a_saved_original_source_capture(tmp_path):
    capture.capture_fda_pdf_bytes(MANIFEST, GOOD_ID, tmp_path, opener=Opener())
    with pytest.raises(ValueError, match="overwrite"):
        capture.capture_fda_pdf_bytes(MANIFEST, GOOD_ID, tmp_path, opener=Opener())
    assert (tmp_path / f"{GOOD_ID}.pdf").read_bytes() == test_pdf()


@pytest.mark.parametrize("overrides", [
    {"modified_url": "https://evil.test/fda.pdf"},
    {"status": 302},
    {"status": 404},
    {"content_type": "text/html"},
    {"payload": b"<html>login</html>" * 200},
    {"payload": b"%PDF-1.7" + b"a" * 2000},
    {"payload": b"nothing" * 2000 + b"%%EOF"},
    {"payload": b"%PDF-1.7" + b"a" * (capture.MAX_BYTES + 5) + b"%%EOF"},
])
def test_external_capture_errors_fail_closed_without_persisting_bytes(tmp_path, overrides):
    with pytest.raises(ValueError):
        capture.capture_fda_pdf_bytes(
            MANIFEST, GOOD_ID, tmp_path, opener=Opener(**overrides),
        )
    assert list(tmp_path.iterdir()) == []


def test_unrecognized_or_spoofed_fda_source_rejected(tmp_path):
    with pytest.raises(ValueError):
        capture.capture_fda_pdf_bytes(MANIFEST, "NDA000000_ORIGINAL_1_20200515_APPROVED", tmp_path, opener=Opener())
    fake = json.loads(json.dumps(MANIFEST))
    fake["letters"][1]["original_document_url"] = "https://www.fda.gov@evil.com/a.pdf"
    with pytest.raises(ValueError):
        capture.capture_fda_pdf_bytes(fake, CRL_ID, tmp_path, opener=Opener())
    fake = json.loads(json.dumps(MANIFEST))
    fake["letters"][0]["source_document_bytes_sha256"] = "a" * 64
    with pytest.raises(ValueError):
        capture.capture_fda_pdf_bytes(fake, GOOD_ID, tmp_path, opener=Opener())
    fake = json.loads(json.dumps(MANIFEST))
    fake["letters"][0]["eligible_for_training"] = True
    with pytest.raises(ValueError):
        capture.capture_fda_pdf_bytes(fake, GOOD_ID, tmp_path, opener=Opener())


def test_symlinked_output_directory_rejected(tmp_path):
    real = tmp_path / "evidence"
    real.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        capture.capture_fda_pdf_bytes(MANIFEST, GOOD_ID, link, opener=Opener())


def test_naive_timestamp_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        capture.capture_fda_pdf_bytes(
            MANIFEST, GOOD_ID, tmp_path, opener=Opener(),
            observed_at=datetime(2026, 10, 28, 15, 0),
        )


def test_pdf_redirects_unconditionally_rejected():
    handler = capture.NoRedirects()
    with pytest.raises(ValueError, match="redirect"):
        handler.redirect_request(None, None, 302, "found", {}, "https://other.example/file.pdf")


@pytest.mark.parametrize("case_id,new_url", [
    (GOOD_ID, "https://www.accessdata.fda.gov/unrelated-but-fda-hosted.pdf"),
    (CRL_ID, "https://download.open.fda.gov/crl/different-bla.pdf"),
    (GOOD_ID, "https://download.open.fda.gov/crl/CRL_BLA761303Original1_20240322.pdf"),
])
def test_same_fda_host_or_swapped_letter_cannot_replace_curated_exact_url(
    tmp_path, case_id, new_url,
):
    # A domain allowlist alone does not bind the *specific* reviewed letter.
    # Altering a versioned manifest must not silently change this source.
    fake = json.loads(json.dumps(MANIFEST))
    target = next(r for r in fake["letters"] if r["record_id"] == case_id)
    target["original_document_url"] = new_url
    transport = Opener()
    with pytest.raises(ValueError, match="immutable official FDA URL"):
        capture.capture_fda_pdf_bytes(fake, case_id, tmp_path, opener=transport)
    assert transport.calls == []
    assert list(tmp_path.iterdir()) == []


def test_failed_json_receipt_write_rolls_back_newly_captured_pdf(tmp_path, monkeypatch):
    # Simulate a sudden disk error after a *valid* PDF has already been
    # hard-linked into its final path but while its receipt is being written.
    # Nothing should be published without the matching receipt.
    def fail_json_write(*args, **kwargs):
        raise OSError("simulated receipt-write failure")

    monkeypatch.setattr(capture.json, "dump", fail_json_write)
    with pytest.raises(OSError, match="receipt-write failure"):
        capture.capture_fda_pdf_bytes(
            MANIFEST, GOOD_ID, tmp_path,
            opener=Opener(), observed_at=datetime(2026, 10, 28, 15, 0,
                                                   tzinfo=timezone.utc),
        )
    assert list(tmp_path.iterdir()) == []


def test_exact_curated_url_pins_match_original_fda_letter_manifest():
    assert set(capture.EXACT_FDA_DOCUMENT_URLS) == {GOOD_ID, CRL_ID}
    assert {
        item["record_id"]: item["original_document_url"]
        for item in MANIFEST["letters"]
    } == capture.EXACT_FDA_DOCUMENT_URLS
