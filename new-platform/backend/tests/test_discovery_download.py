import json
from io import BytesIO

import pytest

from assessment_levels_07_20 import discovery_download


class Response(BytesIO):
    url = "https://example.org/paper.pdf"


def test_download_writes_real_bytes_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(discovery_download, "urlopen", lambda request, timeout: Response(b"%PDF-1.7 sample"))
    destination = tmp_path / "paper.pdf"
    record = discovery_download.download_discovery_source("https://example.org/paper.pdf", destination)
    assert destination.read_bytes() == b"%PDF-1.7 sample"
    assert json.loads((tmp_path / "paper.pdf.json").read_text())["sha256"] == record["sha256"]
    assert record["blind_eligible"] is False


def test_refuses_overwrite(monkeypatch, tmp_path):
    monkeypatch.setattr(discovery_download, "urlopen", lambda request, timeout: Response(b"data"))
    destination = tmp_path / "paper.pdf"
    destination.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        discovery_download.download_discovery_source("https://example.org/paper.pdf", destination)
    assert destination.read_bytes() == b"existing"


def test_rejects_non_https(tmp_path):
    with pytest.raises(ValueError):
        discovery_download.download_discovery_source("http://example.org/paper.pdf", tmp_path / "paper.pdf")


def test_rejects_oversized(monkeypatch, tmp_path):
    monkeypatch.setattr(discovery_download, "urlopen", lambda request, timeout: Response(b"abcde"))
    with pytest.raises(ValueError):
        discovery_download.download_discovery_source("https://example.org/paper.pdf", tmp_path / "paper.pdf", max_bytes=4)
