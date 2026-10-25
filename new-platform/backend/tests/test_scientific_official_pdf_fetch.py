"""Pinned-only original PDF acquisition: no outbound calls or clinical status changes in tests."""
from __future__ import annotations

import base64
import hashlib

import pytest
import requests

from app import scientific_official_pdf_fetch as sources


GOOD_PDF = b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\nOfficial-source-test-bytes\n%%EOF\n"


class Response:
    def __init__(self, body=GOOD_PDF, *, status=200, kind="application/pdf",
                 length=None, streamed=None):
        self.status_code = status
        self.headers = {"Content-Type": kind}
        if length is not None:
            self.headers["Content-Length"] = str(length)
        self.body = body
        self.streamed = streamed
        self.closed = False

    def iter_content(self, chunk_size):
        assert chunk_size <= 65536
        for piece in (self.streamed if self.streamed is not None else [self.body]):
            yield piece

    def close(self):
        self.closed = True


def test_fetch_uses_only_exact_pinned_urls_with_tls_no_redirects(monkeypatch):
    calls = []
    response = Response(length=len(GOOD_PDF))
    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response
    monkeypatch.setattr(sources.requests, "get", fake_get)
    assert sources.fetch_official_pdf("protocol") == GOOD_PDF
    assert len(calls) == 1
    assert calls[0][0] == sources.PROTOCOL_SAP
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["stream"] is True
    assert calls[0][1]["timeout"] == (5, 15)
    assert calls[0][0].startswith("https://cdn.clinicaltrials.gov/")
    assert response.closed is True
    response2 = Response(length=len(GOOD_PDF))
    monkeypatch.setattr(sources.requests, "get", lambda url, **kwargs: (
        calls.append((url, kwargs)) or response2))
    assert sources.fetch_official_pdf("fda") == GOOD_PDF
    assert calls[-1][0] == sources.FDA_2016_APPROVAL
    assert calls[-1][0].startswith("https://www.accessdata.fda.gov/")
    response3 = Response(length=len(GOOD_PDF))
    monkeypatch.setattr(sources.requests, "get", lambda url, **kwargs: (
        calls.append((url, kwargs)) or response3))
    assert sources.fetch_official_pdf("csr") == GOOD_PDF
    assert calls[-1][0] == sources.GERMAN_REGULATOR_CSR
    assert calls[-1][0].startswith("https://portal.dimdi.de/data/ctr/")
    assert calls[-1][1]["allow_redirects"] is False
    assert response3.closed is True
    response4 = Response(length=len(GOOD_PDF))
    monkeypatch.setattr(sources.requests, "get", lambda url, **kwargs: (
        calls.append((url, kwargs)) or response4))
    assert sources.fetch_official_pdf("ema") == GOOD_PDF
    assert calls[-1][0] == sources.EMA_2016_ASSESSMENT
    assert calls[-1][0].startswith("https://www.ema.europa.eu/en/documents/variation-report/")
    assert calls[-1][1]["allow_redirects"] is False
    assert response4.closed is True


@pytest.mark.parametrize("invalid", ["https://evil.example/payload", "other", "", None])
def test_unknown_source_never_makes_network_call(monkeypatch, invalid):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("Unapproved URL must never be fetched")
    monkeypatch.setattr(sources.requests, "get", unexpected)
    with pytest.raises(ValueError, match="Unknown official source"):
        sources.fetch_official_pdf(invalid)


@pytest.mark.parametrize("response", [
    Response(status=301),
    Response(status=302),
    Response(status=403),
    Response(status=500),
    Response(kind="text/html"),
    Response(body=b"<html>Unrelated content and large enough to parse</html>"),
    Response(body=GOOD_PDF[:-6]),
    Response(body=GOOD_PDF, length=len(GOOD_PDF)-1),
    Response(body=GOOD_PDF, length=sources.MAX_PDF_BYTES+1),
    Response(body=GOOD_PDF, length="not-a-number"),
    Response(streamed=[b"%PDF-1.7\n", b"x"*(sources.MAX_PDF_BYTES+1)]),
])
def test_fail_closed_on_unavailable_or_wrong_pdf(monkeypatch, response):
    monkeypatch.setattr(sources.requests, "get", lambda *_args, **_kw: response)
    with pytest.raises(sources.OfficialSourceUnavailable):
        sources.fetch_official_pdf("protocol")
    assert response.closed is True


def test_network_errors_are_non_secret_and_do_not_write(monkeypatch):
    monkeypatch.setattr(sources.requests, "get",
                        lambda *_args, **_kw: (_ for _ in ()).throw(
                            requests.exceptions.Timeout("private upstream request")))
    with pytest.raises(sources.OfficialSourceUnavailable) as error:
        sources.fetch_official_pdf("fda")
    assert "private upstream" not in str(error.value)


def test_archive_fetch_produces_unchanged_unverified_source_receipt(monkeypatch):
    captured = []
    monkeypatch.setattr(sources, "read_document_manifest",
                        lambda _: {"documents": [], "sourceDocumentCount": 0})
    monkeypatch.setattr(sources, "fetch_official_pdf",
                        lambda source: GOOD_PDF)
    def saved(nct_id, payload):
        captured.append((nct_id, payload))
        return {
            "documentId": "a"*32,
            "nctId": nct_id,
            "sha256": payload["sha256"],
            "documentContentScientificallyVerified": False,
            "byteIntegrityChecked": True,
            "canCountTowardReadiness": False,
        }
    monkeypatch.setattr(sources, "capture_document", saved)
    record = sources.archive_official_pdf("NCT02142738", "protocol")
    assert record["alreadyArchived"] is False
    assert record["scientificallyVerified"] is False
    assert record["independentReviewRequired"] is True
    assert "2017" in record["documentDateNote"]
    assert len(captured) == 1
    nct, payload = captured[0]
    assert nct == "NCT02142738"
    assert payload["gateId"] == "protocol_sap"
    assert payload["sourceType"] == "protocol_sap"
    assert payload["sourceUrl"] == sources.PROTOCOL_SAP
    assert payload["sha256"] == hashlib.sha256(GOOD_PDF).hexdigest()
    assert base64.b64decode(payload["contentBase64"]) == GOOD_PDF
    assert "scientificallyVerified" not in payload


def test_idempotent_exact_source_archive_skips_network(monkeypatch):
    existing = {
        "documentId": "a"*32,
        "gateId": "official_regulatory",
        "sourceUrl": sources.FDA_2016_APPROVAL,
        "sha256": "b"*64,
        "documentContentScientificallyVerified": False,
    }
    monkeypatch.setattr(sources, "read_document_manifest",
                        lambda _: {"documents": [existing], "sourceDocumentCount": 1})
    monkeypatch.setattr(sources, "fetch_official_pdf",
                        lambda _: (_ for _ in ()).throw(AssertionError("Should not redownload")))
    record = sources.archive_official_pdf("NCT02142738", "fda")
    assert record["alreadyArchived"] is True
    assert record["scientificallyVerified"] is False
    assert record["independentReviewRequired"] is True
    assert record["documentId"] == existing["documentId"]


def test_other_trial_cannot_trigger_source_request(monkeypatch):
    monkeypatch.setattr(sources, "fetch_official_pdf",
                        lambda _: (_ for _ in ()).throw(AssertionError("Must not fetch")))
    with pytest.raises(ValueError):
        sources.archive_official_pdf("NCT99999999", "fda")



def test_bootstrap_pinned_sources_runs_all_four_once_and_keeps_science_unverified(monkeypatch, caplog):
    called=[]
    def capture(nct, source):
        called.append((nct,source))
        return {
            "alreadyArchived": source=="fda", "byteLength": 1536,
            "scientificallyVerified": False, "independentReviewRequired": True,
        }
    monkeypatch.setattr(sources, "archive_official_pdf", capture)
    sources.bootstrap_pinned_pilot_sources()
    assert called == [(sources.PILOT_NCT, "protocol"), (sources.PILOT_NCT, "fda"),
                      (sources.PILOT_NCT, "csr"), (sources.PILOT_NCT, "ema")]
    assert caplog.text.count("scientific_verification=False") == 4
    assert "status=CAPTURED" in caplog.text
    assert "status=ALREADY_ARCHIVED" in caplog.text


def test_bootstrap_fails_open_for_health_but_closed_for_science(monkeypatch, caplog):
    called=[]
    def capture(nct, source):
        called.append(source)
        if source=="protocol":
            raise sources.OfficialSourceUnavailable("Private server error")
        return {
            "alreadyArchived": False, "byteLength": 2048,
            "scientificallyVerified": False, "independentReviewRequired": True,
        }
    monkeypatch.setattr(sources, "archive_official_pdf", capture)
    sources.bootstrap_pinned_pilot_sources()
    assert called == ["protocol", "fda", "csr", "ema"]
    assert "source=protocol status=UNAVAILABLE" in caplog.text
    assert "source=fda status=CAPTURED" in caplog.text
    assert "Private server error" not in caplog.text



def test_german_csr_read_only_archive_metadata_never_confers_preunblinding_signoff(monkeypatch):
    captured=[]
    monkeypatch.setattr(sources, "read_document_manifest",
                        lambda _: {"documents": [], "sourceDocumentCount": 0})
    monkeypatch.setattr(sources, "fetch_official_pdf", lambda name: GOOD_PDF)
    def saved(nct_id,payload):
        captured.append(payload)
        return {"documentId":"a"*32,"byteLength":len(GOOD_PDF),
                "sha256":payload["sha256"],
                "documentContentScientificallyVerified":False,
                "canCountTowardReadiness":False}
    monkeypatch.setattr(sources, "capture_document", saved)
    receipt=sources.archive_official_pdf("NCT02142738","csr")
    assert receipt["alreadyArchived"] is False
    assert receipt["scientificallyVerified"] is False
    assert receipt["independentReviewRequired"] is True
    assert "not a signed contemporaneous 2016 SAP" in receipt["documentDateNote"]
    assert captured[0]["sourceUrl"] == sources.GERMAN_REGULATOR_CSR
    assert captured[0]["gateId"] == "protocol_sap"
    assert captured[0]["sourceType"] == "clinical_study_report"
    assert captured[0]["capturedBy"] == "Verified Google operator: pinned source"
    assert "independentlyVerified" not in captured[0]
    assert "scientificallyVerified" not in captured[0]



def test_ema_fourth_source_is_pdf_bytes_only_not_signed_prelock_sap(monkeypatch):
    captured=[]
    monkeypatch.setattr(sources,"read_document_manifest",
                        lambda _: {"documents":[],"sourceDocumentCount":0})
    monkeypatch.setattr(sources,"fetch_official_pdf",lambda source: GOOD_PDF)
    def save(nct,body):
        captured.append(body)
        return {"documentId":"e"*32,"byteLength":len(GOOD_PDF),
                "sha256":body["sha256"],"byteIntegrityChecked":True,
                "documentContentScientificallyVerified":False,
                "sourceAuthorshipVerified":False,"canCountTowardReadiness":False}
    monkeypatch.setattr(sources,"capture_document",save)
    result=sources.archive_official_pdf("NCT02142738","ema")
    assert result["scientificallyVerified"] is False
    assert result["independentReviewRequired"] is True
    assert "not a complete signed" in result["documentDateNote"]
    assert len(captured)==1
    assert captured[0]["sourceUrl"]==sources.EMA_2016_ASSESSMENT
    assert captured[0]["sourceType"]=="official_agency_document"
    assert captured[0]["gateId"]=="protocol_sap"
    assert "independentlyVerified" not in captured[0]



def test_ema_exact_url_enforces_separate_5_mib_ceiling(monkeypatch):
    calls=[]
    # A response just above 4 MiB is allowed only for the pinned EMA PDF.
    raw=b"%PDF-1.7\n" + b"0"*(sources.MAX_PDF_BYTES+1) + b"\n%%EOF\n"
    def mocked(url,**kwargs):
        calls.append(url)
        return Response(body=raw,length=len(raw))
    monkeypatch.setattr(sources.requests,"get",mocked)
    assert sources.fetch_official_pdf("ema") == raw
    assert calls == [sources.EMA_2016_ASSESSMENT]
    with pytest.raises(sources.OfficialSourceUnavailable,
                       match="exceeds archival limit"):
        sources.fetch_official_pdf("protocol")
    too_big=Response(length=sources.MAX_EMA_PDF_BYTES+1)
    monkeypatch.setattr(sources.requests,"get",
                        lambda url,**kwargs: too_big)
    with pytest.raises(sources.OfficialSourceUnavailable,
                       match="exceeds archival limit"):
        sources.fetch_official_pdf("ema")
    assert too_big.closed is True


def test_bootstrap_only_prints_allowlisted_fetch_error_reasons(monkeypatch,caplog):
    def rejects(_,source):
        raise sources.OfficialSourceUnavailable("Private upstream auth token 123")
    monkeypatch.setattr(sources,"archive_official_pdf",rejects)
    sources.bootstrap_pinned_pilot_sources()
    assert "Private upstream auth token" not in caplog.text
    assert "reason=Local archive validation, conflict, or source unavailable" in caplog.text
