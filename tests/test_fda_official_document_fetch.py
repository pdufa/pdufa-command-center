from io import BytesIO
from unittest.mock import patch

from research.fda_official_document_fetch import fetch_public_fda_document


def test_spoofed_and_insecure_hosts_rejected_without_network():
    for url in (
        "http://www.fda.gov/document.pdf",
        "https://www.fda.gov.evil.example/document.pdf",
        "https://fda.gov@evil.example/document.pdf",
        "https://evil.example/document.pdf",
        "https://fda.gov:8443/document.pdf",
    ):
        assert fetch_public_fda_document(url).status == "NON_OFFICIAL_OR_UNSAFE_URL"


def test_bytes_captured_but_decision_not_authenticated():
    class FakeResponse:
        headers = {"Content-Type": "application/pdf"}
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, count): return b"%PDF-fixture"

    class FakeOpener:
        def open(self, request, timeout): return FakeResponse()

    with patch("research.fda_official_document_fetch.build_opener", return_value=FakeOpener()):
        result = fetch_public_fda_document("https://www.fda.gov/example.pdf")
    assert result.status == "HTTPS_BYTES_CAPTURED_DECISION_UNVERIFIED"
    assert result.document_bytes == b"%PDF-fixture"
    assert not result.independently_authenticated_decision


def test_oversized_response_rejected():
    class FakeResponse:
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, count): return b"x" * count

    class FakeOpener:
        def open(self, request, timeout): return FakeResponse()

    with patch("research.fda_official_document_fetch.build_opener", return_value=FakeOpener()):
        result = fetch_public_fda_document("https://www.fda.gov/large.pdf", max_bytes=4)
    assert result.status == "DOCUMENT_TOO_LARGE"
