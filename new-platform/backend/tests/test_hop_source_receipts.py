"""Synthetic source bytes verify retention safeguards, not real outcome accuracy."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest

from app import hop_source_receipts as receipts

MANIFEST = receipts.MANIFEST_URL
CRL_URL = "https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip"
DRUG_URL = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
START = datetime(2026, 10, 27, 23, 59, 50, tzinfo=timezone.utc)
MANIFEST_DONE = datetime(2026, 10, 27, 23, 59, 59, tzinfo=timezone.utc)
ARCHIVE_DONE = datetime(2026, 10, 28, 0, 0, 3, tzinfo=timezone.utc)


def mock_http(monkeypatch, payloads, *, status=200, redirect_to=None):
    calls = []

    class Response:
        def __init__(self, url):
            self.url = url
            self.status = status
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return redirect_to or self.url
        def read(self, bound):
            calls.append((self.url, bound))
            return payloads[self.url]

    opener = SimpleNamespace(open=lambda req, timeout: Response(req.full_url))
    monkeypatch.setattr(receipts, "build_opener", lambda *handlers: opener)
    return calls


def collect(tmp_path, monkeypatch, *, source="CRL", content=b"PK-synthetic-archive"):
    url = CRL_URL if source == "CRL" else DRUG_URL
    raw_manifest = b'{ "fixture": "preserve whitespace", "not_outcomes": true }\n'
    calls = mock_http(monkeypatch, {MANIFEST: raw_manifest, url: content})
    ticks = iter([START, MANIFEST_DONE, ARCHIVE_DONE])
    batch = receipts.SourceReceipts(tmp_path / "originals", source, clock=lambda: next(ticks))
    assert batch.fetch(MANIFEST, 8000) == raw_manifest
    assert batch.fetch(url, 12000) == content
    return batch, raw_manifest, url, content, calls


@pytest.mark.parametrize("source", ["CRL", "DRUGSFDA"])
def test_retention_is_exact_original_bytes_with_completed_timestamps_and_no_truth_claims(tmp_path, monkeypatch, source):
    batch, raw, url, archive, calls = collect(tmp_path, monkeypatch, source=source)
    assert not batch.destination.exists()
    sha = hashlib.sha256(archive).hexdigest()
    report = batch.retain({url: sha})
    assert (batch.destination / "manifest.original.json").read_bytes() == raw
    assert (batch.destination / f"{sha}.zip").read_bytes() == archive
    assert json.loads((batch.destination / "source-receipt.json").read_text()) == report
    assert report["intake_started_at"] == START.isoformat()
    assert [r["retrieved_at"] for r in report["records"]] == [MANIFEST_DONE.isoformat(), ARCHIVE_DONE.isoformat()]
    assert calls == [(MANIFEST, 8001), (url, 12001)]
    cutoff = datetime(2026, 10, 28, tzinfo=timezone.utc)
    assert [r["role"] for r in report["records"]
            if datetime.fromisoformat(r["retrieved_at"]) < cutoff] == ["DOWNLOAD_MANIFEST"]
    for row in report["records"]:
        assert row["publication_date"] is None and row["document_date"] is None
        assert row["source_content_independently_verified"] is False
        assert row["application_identity_verified"] is False
        assert row["review_cycle_verified"] is False
        assert row["outcome_verified"] is False and row["model_eligible"] is False
    assert report["independently_verified_pass_records"] == 0
    assert report["independently_verified_fail_records"] == 0
    assert report["model_eligible_records"] == 0
    assert report["prediction_probability"] is None
    assert not list(batch.destination.glob("*.json.zip"))  # Content-addressed bytes; never extracted.


def test_completion_clock_is_sampled_after_fetch_and_hash(tmp_path, monkeypatch):
    calls = mock_http(monkeypatch, {MANIFEST: b"{}"})
    real_hash = receipts.hashlib.sha256
    hashed = []

    def digest(content):
        hashed.append(content)
        return real_hash(content)

    def clock():
        if calls:
            assert hashed == [b"{}"]
            return MANIFEST_DONE
        return START

    monkeypatch.setattr(receipts.hashlib, "sha256", digest)
    batch = receipts.SourceReceipts(tmp_path / "new", "CRL", clock=clock)
    batch.fetch(MANIFEST, 100)


@pytest.mark.parametrize("url", [
    "https://download.open.fda.gov.attacker.invalid/transparency/crl/a.json.zip",
    "http://download.open.fda.gov/transparency/crl/a.json.zip",
    "https://u:p@download.open.fda.gov/transparency/crl/a.json.zip",
    "https://download.open.fda.gov:443/transparency/crl/a.json.zip",
    "https://download.open.fda.gov/transparency/crl/a.json.zip?token=x",
    "https://download.open.fda.gov/transparency/crl/a.json.zip#x",
    "https://download.open.fda.gov/drug/drugsfda/a.json.zip",
    "https://api.fda.gov/other.json",
    "https://download.open.fda.gov/transparency/crl/../other.json.zip",
])
def test_invalid_source_url_rejected_before_network(tmp_path, monkeypatch, url):
    monkeypatch.setattr(receipts, "build_opener", lambda *args: pytest.fail("must validate before network"))
    batch = receipts.SourceReceipts(tmp_path / "new", "CRL")
    with pytest.raises(ValueError):
        batch.fetch(url, 100)


@pytest.mark.parametrize("kind", ["existing", "symlink_destination", "symlink_parent", "traversal"])
def test_new_directory_and_real_parent_required_before_network(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(receipts, "build_opener", lambda *args: pytest.fail("must refuse before network"))
    target = tmp_path / "originals"
    if kind == "existing":
        target.mkdir()
        (target / "keep").write_text("unchanged")
    elif kind == "symlink_destination":
        target.symlink_to(tmp_path, target_is_directory=True)
    elif kind == "symlink_parent":
        link = tmp_path / "linked"
        link.symlink_to(tmp_path, target_is_directory=True)
        target = link / "new"
    else:
        target = tmp_path / "child" / ".." / "new"
    with pytest.raises((ValueError, OSError)):
        receipts.SourceReceipts(target, "CRL")
    if kind == "existing":
        assert (target / "keep").read_text() == "unchanged"


def test_wrong_staging_hash_or_modified_capture_never_creates_archive(tmp_path, monkeypatch):
    batch, _, url, archive, _ = collect(tmp_path, monkeypatch)
    sha = hashlib.sha256(archive).hexdigest()
    with pytest.raises(ValueError, match="reconcile"):
        batch.retain({url: "0" * 64})
    assert not batch.destination.exists()
    _, row = batch._captures[url]
    batch._captures[url] = (b"changed", row)
    with pytest.raises(ValueError, match="changed"):
        batch.retain({url: sha})
    assert not batch.destination.exists()


def test_existing_destination_at_commit_is_not_overwritten(tmp_path, monkeypatch):
    batch, _, url, archive, _ = collect(tmp_path, monkeypatch)
    batch.destination.mkdir()
    (batch.destination / "keep").write_bytes(b"prior work")
    with pytest.raises(ValueError, match="already exists"):
        batch.retain({url: hashlib.sha256(archive).hexdigest()})
    assert (batch.destination / "keep").read_bytes() == b"prior work"


@pytest.mark.parametrize("status,redirect_to", [(302, None), (200, "https://www.fda.gov/other")])
def test_http_status_and_redirect_response_refused(tmp_path, monkeypatch, status, redirect_to):
    mock_http(monkeypatch, {MANIFEST: b"{}"}, status=status, redirect_to=redirect_to)
    batch = receipts.SourceReceipts(tmp_path / "new", "CRL")
    with pytest.raises(ValueError, match="exact FDA"):
        batch.fetch(MANIFEST, 100)
    assert not batch.destination.exists()
    assert not batch._captures


def test_redirect_handler_never_follows_even_official_url():
    with pytest.raises(ValueError, match="redirect rejected"):
        receipts._RejectRedirect().redirect_request(None, None, 302, "Found", {}, MANIFEST)


def test_bounds_duplicates_and_backwards_clock_fail_without_receipt(tmp_path, monkeypatch):
    mock_http(monkeypatch, {MANIFEST: b"{}", CRL_URL: b"123456"})
    batch = receipts.SourceReceipts(tmp_path / "new", "CRL")
    with pytest.raises(ValueError, match="capture limit"):
        batch.fetch(MANIFEST, receipts.MAX_CAPTURE_BYTES + 1)
    batch.fetch(MANIFEST, 100)
    with pytest.raises(ValueError, match="duplicate"):
        batch.fetch(MANIFEST, 100)
    with pytest.raises(ValueError, match="byte limit"):
        batch.fetch(CRL_URL, 5)
    monkeypatch.setattr(receipts, "MAX_BATCH_BYTES", 3)
    with pytest.raises(ValueError, match="batch"):
        batch.fetch(CRL_URL, 100)
    times = iter([ARCHIVE_DONE, START])
    backwards = receipts.SourceReceipts(tmp_path / "backwards", "CRL", clock=lambda: next(times))
    with pytest.raises(ValueError, match="predates"):
        backwards.fetch(MANIFEST, 100)
    assert not backwards.destination.exists()


def collector(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payloads(source, *, broken=False):
    if source == "CRL":
        url = CRL_URL
        record = {"application_number": ["NDA123456"], "letter_type": "COMPLETE RESPONSE"}
        section = ("transparency", "crl")
    else:
        url = DRUG_URL
        record = {"application_number": "NDA123456", "submissions": []}
        section = ("drug", "drugsfda")
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as zipped:
        zipped.writestr("source.json", json.dumps({"results": [record]}))
    manifest = {"results": {section[0]: {section[1]: {
        "export_date": "2026-10-23", "total_records": 1,
        "partitions": [{"file": url, "records": 1}],
    }}}}
    # Preserve byte identity independently of parsed/reserialized JSON.
    return {MANIFEST: ("  " + json.dumps(manifest, indent=3) + "\n").encode(),
            url: b"invalid zip" if broken else raw.getvalue()}


@pytest.mark.parametrize("source,name", [("CRL", "collect_hop_openfda_crl.py"),
                                         ("DRUGSFDA", "collect_hop_drugsfda.py")])
@pytest.mark.parametrize("retain", [False, True])
def test_collectors_preserve_defaults_and_opt_in_retains_exact_bytes(tmp_path, monkeypatch, capsys, source, name, retain):
    module = collector(name)
    data = payloads(source)
    output = tmp_path / "derived"
    originals = tmp_path / "originals"
    argv = [name, "--output-dir", str(output)]
    if retain:
        argv += ["--retain-originals-dir", str(originals)]
        mock_http(monkeypatch, data)
        monkeypatch.setattr(module, "download" if source == "CRL" else "fetch",
                            lambda *args: pytest.fail("opt-in must use bounded receipt capture"))
    else:
        monkeypatch.setattr(module, "download" if source == "CRL" else "fetch", lambda url, limit: data[url])
        monkeypatch.setattr(module, "SourceReceipts", lambda *args: pytest.fail("defaults must not activate retention"))
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    assert len(list(output.glob("*.json"))) == 2
    assert json.loads(capsys.readouterr().out)["status"]
    if retain:
        assert (originals / "manifest.original.json").read_bytes() == data[MANIFEST]
        url = CRL_URL if source == "CRL" else DRUG_URL
        sha = hashlib.sha256(data[url]).hexdigest()
        assert (originals / f"{sha}.zip").read_bytes() == data[url]
        report = json.loads((originals / "source-receipt.json").read_text())
        assert report["original_source_archive_sha256"] == {url: sha}
        assert report["model_eligible_records"] == 0
    else:
        assert not originals.exists()


@pytest.mark.parametrize("source,name", [("CRL", "collect_hop_openfda_crl.py"),
                                         ("DRUGSFDA", "collect_hop_drugsfda.py")])
def test_collector_staging_failure_never_claims_original_retention(tmp_path, monkeypatch, source, name):
    module = collector(name)
    mock_http(monkeypatch, payloads(source, broken=True))
    monkeypatch.setattr(sys, "argv", [name, "--output-dir", str(tmp_path / "derived"),
                                      "--retain-originals-dir", str(tmp_path / "originals")])
    with pytest.raises(ValueError, match="invalid"):
        module.main()
    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "derived").exists()
