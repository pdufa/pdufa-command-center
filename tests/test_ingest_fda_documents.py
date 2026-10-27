"""Synthetic bytes test intake integrity only, never FDA prediction accuracy."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


SPEC = importlib.util.spec_from_file_location(
    "ingest_fda_documents", Path(__file__).resolve().parents[1] / "scripts/ingest_fda_documents.py")
intake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(intake)
NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)
PDF = b"%PDF-1.7\nsynthetic test-only content\n%%EOF\n"
SHA = hashlib.sha256(PDF).hexdigest()
URL = "https://www.fda.gov/media/123456/download"


def document(**updates):
    return {"id": "source-one", "url": URL, "document_date": "2020-01-01",
            "publication_date": None, "relative_path": "original.pdf",
            "expected_sha256": SHA, **updates}


def manifest(tmp_path, *documents):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema_version": 1, "documents": documents or [document()]}))
    return path


def original(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "original.pdf").write_bytes(PDF)
    return root


def test_default_dry_run_checks_bytes_without_writes_or_false_verification(tmp_path):
    source = original(tmp_path)
    path = manifest(tmp_path)
    before = set(tmp_path.rglob("*"))
    report = intake.ingest(path, source_dir=source, now=NOW)
    assert set(tmp_path.rglob("*")) == before
    row = report["records"][0]
    assert row["sha256"] == SHA
    assert row["capture_status"] == "OFFLINE_BYTES_INTEGRITY_CONFIRMED"
    assert row["publication_date_as_declared"] is None
    assert row["retrieved_at"] is None  # Receipt now is not an invented original retrieval.
    assert row["received_at"] == NOW.isoformat()
    assert row["retained_path"] is None
    assert row["original_source_authenticity_verified"] is False
    assert row["independently_verified"] is False
    assert row["review_cycle_verified"] is False
    assert row["outcome"] is None
    assert report["model_eligible_records"] == 0
    assert report["independently_verified_pass_records"] == 0
    assert report["independently_verified_fail_records"] == 0
    assert report["prediction_probability"] is None


def test_explicit_new_destination_retains_exact_original_manifest_and_bytes(tmp_path):
    source = original(tmp_path)
    path = manifest(tmp_path)
    archive = tmp_path / "archive"
    report = intake.ingest(path, source_dir=source, output_dir=archive, now=NOW)
    assert (archive / "manifest.original.json").read_bytes() == path.read_bytes()
    assert (archive / f"{SHA}.pdf").read_bytes() == PDF
    assert json.loads((archive / "receipt.json").read_text()) == report
    assert (source / "original.pdf").read_bytes() == PDF
    assert report["dry_run"] is False
    with pytest.raises(ValueError, match="must be new"):
        intake.ingest(path, source_dir=source, output_dir=archive, now=NOW)


def test_corruption_rejects_entire_batch_before_creating_archive(tmp_path):
    source = original(tmp_path)
    path = manifest(tmp_path, document(expected_sha256="0" * 64))
    archive = tmp_path / "archive"
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        intake.ingest(path, source_dir=source, output_dir=archive, now=NOW)
    assert not archive.exists()


@pytest.mark.parametrize("relative", ["../original.pdf", "/etc/passwd", "a/../../original.pdf",
    "./original.pdf", "a//original.pdf", "a/./original.pdf", "a\\original.pdf", "bad\x00.pdf"])
def test_traversal_never_reads_outside_source(tmp_path, relative):
    path = manifest(tmp_path, document(relative_path=relative))
    with pytest.raises(ValueError, match="path"):
        intake.ingest(path, source_dir=tmp_path, now=NOW)


@pytest.mark.parametrize("location", ["file", "directory", "source_root", "manifest", "output_parent"])
def test_symlink_inputs_and_output_ancestors_rejected(tmp_path, location):
    source = original(tmp_path)
    path = manifest(tmp_path)
    output = None
    if location == "file":
        (source / "link.pdf").symlink_to(source / "original.pdf")
        path = manifest(tmp_path, document(relative_path="link.pdf"))
    elif location == "directory":
        (source / "linked").symlink_to(source, target_is_directory=True)
        path = manifest(tmp_path, document(relative_path="linked/original.pdf"))
    elif location == "source_root":
        (tmp_path / "linked").symlink_to(source, target_is_directory=True)
        source = tmp_path / "linked"
    elif location == "manifest":
        (tmp_path / "linked.json").symlink_to(path)
        path = tmp_path / "linked.json"
    else:
        (tmp_path / "linked").symlink_to(tmp_path, target_is_directory=True)
        output = tmp_path / "linked" / "new-archive"
    with pytest.raises(OSError):
        intake.ingest(path, source_dir=source, output_dir=output, now=NOW)


def test_fifo_does_not_block_or_become_document(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    os.mkfifo(source / "original.pdf")
    with pytest.raises(ValueError, match="regular file"):
        intake.ingest(manifest(tmp_path), source_dir=source, now=NOW)


@pytest.mark.parametrize("updates", [
    {"model_eligible": True}, {"independently_verified": True}, {"outcome": "APPROVED"},
    {"publication_date": "2099-01-01"}, {"document_date": "2020-02-30"},
    {"document_date": "20200101"}, {"document_date": True},
    {"expected_sha256": "a" * 63}, {"expected_sha256": "A" * 64},
    {"url": "https://www.fda.gov.attacker.invalid/letter.pdf"},
    {"url": "http://www.fda.gov/letter.pdf"},
    {"url": "https://user:password@www.fda.gov/letter.pdf"},
    {"url": "https://www.fda.gov:443/letter.pdf"},
    {"url": "https://www.fda.gov/letter.pdf#page=1"},
    {"url": "https://www.fda.gov/letter.pdf?redirect=other"},
    {"url": "https://www.fda.gov/letter\n.pdf"},
])
def test_invalid_manifest_or_caller_promotion_rejected(tmp_path, updates):
    with pytest.raises(ValueError):
        intake.ingest(manifest(tmp_path, document(**updates)), source_dir=tmp_path, now=NOW)


def test_duplicate_identity_or_path_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate document id"):
        intake.ingest(manifest(tmp_path, document(), document()), source_dir=tmp_path, now=NOW)
    with pytest.raises(ValueError, match="duplicate offline PDF path"):
        intake.ingest(manifest(tmp_path, document(), document(id="two")), source_dir=tmp_path, now=NOW)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version":1,"schema_version":1,"documents":[]}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        intake.ingest(path, source_dir=tmp_path, now=NOW)


def test_size_limits_and_nonpdf_fail_before_write(tmp_path, monkeypatch):
    source = original(tmp_path)
    path = manifest(tmp_path)
    monkeypatch.setattr(intake, "MAX_PDF_BYTES", 8)
    with pytest.raises(ValueError, match="bounded"):
        intake.ingest(path, source_dir=source, now=NOW)
    monkeypatch.setattr(intake, "MAX_PDF_BYTES", 200)
    monkeypatch.setattr(intake, "MAX_TOTAL_BYTES", 8)
    with pytest.raises(ValueError, match="batch exceeds"):
        intake.ingest(path, source_dir=source, now=NOW)
    monkeypatch.setattr(intake, "MAX_TOTAL_BYTES", 200)
    (source / "original.pdf").write_bytes(b"<html>not a PDF</html>")
    with pytest.raises(ValueError, match="header"):
        intake.ingest(path, source_dir=source, now=NOW)


def download_document(**updates):
    return {key: value for key, value in document(**updates).items() if key != "relative_path"}


def test_download_dry_run_never_fetches(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "fetch_pdf", lambda _: pytest.fail("dry run must not fetch"))
    report = intake.ingest(manifest(tmp_path, download_document()), mode="download", now=NOW)
    assert report["bytes_inspected"] == 0
    assert report["records"][0]["capture_status"] == "MANIFEST_VALIDATED_NOT_FETCHED"
    assert report["records"][0]["sha256"] is None


def test_explicit_download_keeps_bytes_without_source_truth_promotion(tmp_path, monkeypatch):
    calls = []
    def fetch(url):
        calls.append(url)
        return PDF
    monkeypatch.setattr(intake, "fetch_pdf", fetch)
    report = intake.ingest(manifest(tmp_path, download_document()), mode="download",
                           output_dir=tmp_path / "archive", now=NOW)
    assert calls == [URL]
    row = report["records"][0]
    assert row["retrieved_at"] == NOW.isoformat()
    assert row["capture_status"] == "HTTP_PDF_BYTES_RECEIVED"
    assert row["independently_verified"] is False
    assert (tmp_path / "archive" / f"{SHA}.pdf").read_bytes() == PDF


@pytest.mark.parametrize("status,url,mime,content", [
    (302, URL, "application/pdf", PDF),
    (200, "https://www.fda.gov/media/other/download", "application/pdf", PDF),
    (200, URL, "text/html", PDF),
    (200, URL, "application/pdf", b"not a PDF"),
])
def test_http_response_restrictions(monkeypatch, status, url, mime, content):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return url
        def read(self, bound):
            assert bound == intake.MAX_PDF_BYTES + 1
            return content
    response = Response()
    response.status = status
    response.headers = SimpleNamespace(get_content_type=lambda: mime)
    monkeypatch.setattr(intake, "build_opener", lambda *args: SimpleNamespace(open=lambda *a, **kw: response))
    with pytest.raises(ValueError):
        intake.fetch_pdf(URL)


def test_redirect_handler_never_follows_even_official_redirect():
    with pytest.raises(ValueError, match="redirect rejected"):
        intake._RejectRedirect().redirect_request(None, None, 302, "Found", {}, URL)


def test_existing_output_refused_before_network(tmp_path, monkeypatch):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "keep.txt").write_text("unchanged")
    monkeypatch.setattr(intake, "fetch_pdf", lambda _: pytest.fail("must fail before fetching"))
    with pytest.raises(ValueError, match="must be new"):
        intake.ingest(manifest(tmp_path, download_document()), mode="download", output_dir=archive, now=NOW)
    assert (archive / "keep.txt").read_text() == "unchanged"
