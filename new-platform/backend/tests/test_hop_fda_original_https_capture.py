"""Controlled FDA original-URL capture: offline transport and rollback tests.

Synthetic bytes prove the *mechanics* only; they are not genuine FDA evidence
and do not certify any application, FDA action or first publication date.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture_hop_fda_original_https.py"
spec = spec_from_file_location("fda_original_capture_test", SCRIPT)
mod = module_from_spec(spec)
spec.loader.exec_module(mod)

APPROVED = "NDA213973_ORIGINAL_1_20200515_APPROVED"
CRL = "BLA761303_ORIGINAL_1_20240322_CRL"
STAMP = datetime(2026, 10, 28, 15, 25, tzinfo=timezone.utc)


def pdf_bytes():
    # Header, a plausible-size inert byte body and a terminal PDF marker.
    return b"%PDF-1.7\n" + b"Test-only synthetic PDF bytes" * 100 + b"\n%%EOF\n"


def manifest():
    return json.loads(mod._SAMPLE_FILE.read_text(encoding="utf-8"))


class FakeResponse:
    status = 200
    def __init__(self, content, url, *, status=200, mime="application/pdf"):
        self.status = status
        self.data = content
        self.url = url
        self.pos = 0
        self.closed = False
        self.headers = {
            "Content-Type": mime,
            "Last-Modified": "Wed, 28 Oct 2026 00:00:00 GMT",
            "Date": "Wed, 28 Oct 2026 15:25:00 GMT",
            "ETag": '"synthetic-test-etag"',
        }

    def read(self, size=-1):
        if size < 0:
            raise AssertionError("Unbounded reads prohibited")
        result = self.data[self.pos:self.pos + size]
        self.pos += len(result)
        return result

    def geturl(self):
        return self.url

    def close(self):
        self.closed = True


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return self.response


def make_opener(key=APPROVED, content=None, **kwargs):
    response = FakeResponse(
        pdf_bytes() if content is None else content,
        mod.EXACT_FDA_DOCUMENT_URLS[key],
        **kwargs,
    )
    return FakeOpener(response)


@pytest.mark.parametrize("key", [APPROVED, CRL])
def test_exact_fda_https_source_bytes_hash_and_provenance_are_local_only(tmp_path, key):
    opener = make_opener(key)
    result = mod.capture_fda_pdf_bytes(
        manifest(), key, tmp_path, opener=opener, observed_at=STAMP,
    )
    captured = tmp_path / f"{key}.pdf"
    provenance = tmp_path / f"{key}.provenance.json"
    assert captured.read_bytes() == pdf_bytes()
    assert json.loads(provenance.read_text()) == result
    assert result["sha256OfCapturedBytes"] == hashlib.sha256(pdf_bytes()).hexdigest()
    assert result["byteLength"] == len(pdf_bytes())
    assert result["httpStatus"] == 200
    assert result["httpDateHeader"] == "Wed, 28 Oct 2026 15:25:00 GMT"
    assert result["observedAtUtc"] == "2026-10-28T15:25:00+00:00"
    assert result["FDAletterFirstPublishedAt"] is None
    assert result["sourceDocumentIndependentlyReviewed"] is False
    assert result["documentReferenceAndActionIndependentlyAdjudicated"] is False
    assert result["historicalReviewCycleVerified"] is False
    assert result["frozenPredecisionFeaturesVerified"] is False
    assert result["modelEligible"] is False
    assert result["approvalProbability"] is None
    assert result["archiveRetention"] == "SHORT_LIVED_RESTRICTED_CI_ARTIFACT"
    assert not list(tmp_path.glob(".fda-pdf-*.tmp"))
    assert opener.response.closed
    request, timeout = opener.requests[0]
    assert request.full_url == mod.EXACT_FDA_DOCUMENT_URLS[key]
    assert request.get_method() == "GET"
    assert timeout == 30
    assert "Authorization" not in request.headers
    assert "Cookie" not in request.headers


@pytest.mark.parametrize("mutate", [
    lambda m: m["letters"][0].update(original_document_url="https://www.accessdata.fda.gov/other.pdf"),
    lambda m: m["letters"][0].update(original_document_url="https://malicious.invalid/other.pdf"),
    lambda m: m["letters"][0].update(original_document_url="http://www.accessdata.fda.gov/other.pdf"),
    lambda m: m["letters"][0].update(eligible_for_training=True),
    lambda m: m["letters"][0].update(source_document_bytes_sha256="0" * 64),
])
def test_curated_source_cannot_be_substituted_or_promoted(tmp_path, mutate):
    source = manifest()
    mutate(source)
    opener = make_opener()
    with pytest.raises(ValueError):
        mod.capture_fda_pdf_bytes(source, APPROVED, tmp_path, opener=opener)
    assert not opener.requests
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("identity", [
    "", "NDA999999_ORIGINAL_1_20200515_APPROVED",
    "../NDA213973_ORIGINAL_1_20200515_APPROVED",
    "BLA761303_ORIGINAL_2_20240322_CRL",
])
def test_unknown_or_malformed_exact_identity_rejected_before_network(tmp_path, identity):
    opener = make_opener()
    with pytest.raises(ValueError):
        mod.capture_fda_pdf_bytes(manifest(), identity, tmp_path, opener=opener)
    assert not opener.requests


@pytest.mark.parametrize("kwargs", [
    {"status": 403},
    {"status": 404},
    {"mime": "text/html"},
    {"mime": "text/plain"},
])
def test_http_failure_or_html_response_not_stored(tmp_path, kwargs):
    opener = make_opener(**kwargs)
    with pytest.raises(ValueError):
        mod.capture_fda_pdf_bytes(manifest(), APPROVED, tmp_path, opener=opener)
    assert opener.response.closed
    assert list(tmp_path.iterdir()) == []


def test_redirect_to_other_fda_url_blocked_even_with_http_200(tmp_path):
    opener = make_opener()
    opener.response.url = "https://www.accessdata.fda.gov/unreviewed.pdf"
    with pytest.raises(ValueError, match="exact-url"):
        mod.capture_fda_pdf_bytes(manifest(), APPROVED, tmp_path, opener=opener)
    assert not list(tmp_path.iterdir())


def test_urllib_redirect_handler_refuses_all_redirects():
    with pytest.raises(ValueError, match="redirect"):
        mod.NoRedirects().redirect_request(
            None, None, 302, "Moved", {}, "https://www.accessdata.fda.gov/new.pdf"
        )


@pytest.mark.parametrize("bad_pdf", [
    b"really an html response" * 150,
    b"%PDF-1.7\n" + b"no trailer" * 250,
    b"%PDF-1.7\n" + b"content" * 6 + b"\n%%EOF\n",
])
def test_fake_or_truncated_pdf_cleans_all_temporary_files(tmp_path, bad_pdf):
    opener = make_opener(content=bad_pdf)
    with pytest.raises(ValueError, match="PDF"):
        mod.capture_fda_pdf_bytes(manifest(), APPROVED, tmp_path, opener=opener)
    assert not list(tmp_path.iterdir())


def test_response_over_bounded_size_cleans_partial_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "MAX_BYTES", 1500)
    opener = make_opener()
    with pytest.raises(ValueError, match="maximum"):
        mod.capture_fda_pdf_bytes(manifest(), APPROVED, tmp_path, opener=opener)
    assert not list(tmp_path.iterdir())


def test_existing_pdf_or_provenance_is_never_overwritten(tmp_path):
    for ext in (".pdf", ".provenance.json"):
        path = tmp_path / f"{APPROVED}{ext}"
        path.write_text("Do not change this")
        opener = make_opener()
        with pytest.raises(ValueError, match="overwrite"):
            mod.capture_fda_pdf_bytes(manifest(), APPROVED, tmp_path, opener=opener)
        assert path.read_text() == "Do not change this"
        assert not opener.requests
        path.unlink()


def test_symlink_folder_and_naive_timestamps_blocked(tmp_path):
    linked = tmp_path / "symlink"
    linked.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        mod.capture_fda_pdf_bytes(manifest(), APPROVED, linked, opener=make_opener())
    with pytest.raises(ValueError, match="timezone-aware"):
        mod.capture_fda_pdf_bytes(
            manifest(), APPROVED, tmp_path, opener=make_opener(),
            observed_at=datetime(2026, 10, 28, 15, 25),
        )
    assert not [x for x in tmp_path.iterdir() if x.name != "symlink"]


def test_failure_writing_provenance_rolls_back_pdf_and_json(tmp_path, monkeypatch):
    opener = make_opener()

    def fail_write(*args, **kwargs):
        raise OSError("simulated provenance disk failure")

    monkeypatch.setattr(mod.json, "dump", fail_write)
    with pytest.raises(OSError, match="provenance disk failure"):
        mod.capture_fda_pdf_bytes(
            manifest(), APPROVED, tmp_path, opener=opener, observed_at=STAMP,
        )
    assert not list(tmp_path.iterdir())
    assert opener.response.closed


def test_original_fda_url_host_allowlist_contains_only_two_exact_documents():
    assert mod.EXACT_FDA_DOCUMENT_URLS == {
        APPROVED: "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2020/213973Orig1s000ltr.pdf",
        CRL: "https://download.open.fda.gov/crl/CRL_BLA761303Original1_20240322.pdf",
    }
    assert len(mod.EXACT_FDA_DOCUMENT_URLS) == 2
