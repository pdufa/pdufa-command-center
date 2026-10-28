"""Opt-in exact-byte retention for FDA bulk sources, without outcome clearance.

The collectors still perform their existing staging validation. This helper never
extracts an archive and writes nothing until explicitly committed by the collector.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Callable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MANIFEST_URL = "https://api.fda.gov/download.json"
SOURCE_PREFIXES = {"CRL": "/transparency/crl/", "DRUGSFDA": "/drug/drugsfda/"}
MAX_CAPTURE_BYTES = 24_000_000
MAX_BATCH_BYTES = 256_000_000
MAX_CAPTURES = 64


def _directory(path: Path) -> int:
    absolute = path.absolute()
    if ".." in absolute.parts:
        raise ValueError("source receipt directory must not traverse parents")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _new_destination(path: Path) -> None:
    if not path.name:
        raise ValueError("source receipt destination must be a new directory")
    fd = _directory(path.parent)
    try:
        try:
            os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise ValueError("source receipt destination already exists; no overwrite allowed")
    finally:
        os.close(fd)


def _utc(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware source receipt clock required")
    return value.astimezone(timezone.utc)


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("FDA bulk source redirect rejected")


def _write(fd: int, name: str, content: bytes) -> None:
    file_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                      0o600, dir_fd=fd)
    try:
        with os.fdopen(file_fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(file_fd)


class SourceReceipts:
    """Stage bounded captures in memory; retain after collector validation succeeds."""

    def __init__(self, destination: str | Path, source: str, *,
                 clock: Callable[[], datetime] | None = None):
        if source not in SOURCE_PREFIXES:
            raise ValueError("unsupported FDA bulk source")
        self.destination = Path(destination).absolute()
        _new_destination(self.destination)
        self.source = source
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.started_at = _utc(self.clock)
        self.last_completed_at = self.started_at
        self._captures: dict[str, tuple[bytes, dict]] = {}
        self._total_bytes = 0

    def _role(self, url: str) -> str:
        if (not isinstance(url, str) or len(url) > 2048 or "\\" in url
                or any(c.isspace() or ord(c) < 32 for c in url)):
            raise ValueError("invalid official FDA bulk source URL")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username is not None
                or parsed.password is not None or parsed.port is not None
                or parsed.query or parsed.fragment):
            raise ValueError("invalid official FDA bulk source URL")
        if url == MANIFEST_URL:
            return "DOWNLOAD_MANIFEST"
        if (parsed.hostname != "download.open.fda.gov"
                or not parsed.path.startswith(SOURCE_PREFIXES[self.source])
                or not parsed.path.endswith(".json.zip")
                or "/../" in parsed.path or "/./" in parsed.path):
            raise ValueError("unapproved official FDA source archive URL")
        return "SOURCE_ARCHIVE"

    def fetch(self, url: str, limit: int) -> bytes:
        """Use inherited proxy/default verified TLS, never follow a redirect."""
        role = self._role(url)  # Validate before any network activity.
        if type(limit) is not int or not 1 <= limit <= MAX_CAPTURE_BYTES:
            raise ValueError("invalid bounded source capture limit")
        if url in self._captures or len(self._captures) >= MAX_CAPTURES:
            raise ValueError("duplicate source URL or source capture count exceeded")
        request = Request(url, headers={"User-Agent": "PDUFA-source-original-retention/1.0"})
        with build_opener(_RejectRedirect()).open(request, timeout=60) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("exact FDA bulk URL did not return HTTP 200")
            content = response.read(limit + 1)
        if not isinstance(content, bytes) or not 0 < len(content) <= limit:
            raise ValueError("FDA bulk source exceeds byte limit or is empty")
        if self._total_bytes + len(content) > MAX_BATCH_BYTES:
            raise ValueError("FDA bulk source batch exceeds byte limit")
        digest = hashlib.sha256(content).hexdigest()
        completed_at = _utc(self.clock)
        if completed_at < self.last_completed_at:
            raise ValueError("source receipt clock predates start or earlier completion")
        self.last_completed_at = completed_at
        self._captures[url] = (content, {
            "source_url": url, "role": role, "sha256": digest, "bytes": len(content),
            "retrieved_at": completed_at.isoformat(),
            "document_date": None, "publication_date": None,
            "retained_path": "manifest.original.json" if role == "DOWNLOAD_MANIFEST" else f"{digest}.zip",
            "source_content_independently_verified": False,
            "application_identity_verified": False, "review_cycle_verified": False,
            "outcome_verified": False, "model_eligible": False,
        })
        self._total_bytes += len(content)
        return content

    def retain(self, expected_archive_sha256: dict[str, str]) -> dict:
        """Retain exact captures only if existing staging hashes reconcile."""
        if MANIFEST_URL not in self._captures:
            raise ValueError("original FDA download manifest is missing")
        actual = {url: row["sha256"] for url, (_, row) in self._captures.items()
                  if row["role"] == "SOURCE_ARCHIVE"}
        if (not actual or not isinstance(expected_archive_sha256, dict)
                or actual != expected_archive_sha256
                or any(not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in actual.values())):
            raise ValueError("retained originals do not reconcile with staged archive hashes")
        for content, row in self._captures.values():
            if hashlib.sha256(content).hexdigest() != row["sha256"] or len(content) != row["bytes"]:
                raise ValueError("captured original bytes changed before retention")
        _new_destination(self.destination)
        report = {
            "schema_version": 1, "status": "ORIGINAL_SOURCE_BYTES_RETAINED_NOT_OUTCOME_VERIFICATION",
            "source": self.source, "intake_started_at": self.started_at.isoformat(),
            "records": [row.copy() for _, row in self._captures.values()],
            "original_source_archive_sha256": actual,
            "source_content_independently_verified": False,
            "independently_verified_pass_records": 0, "independently_verified_fail_records": 0,
            "complete_application_denominator_verified": False, "model_eligible_records": 0,
            "prediction_probability": None, "trade_authorized": False,
            "limitations": [
                "An exact HTTP capture and digest establish acquisition provenance, not outcome truth.",
                "Retrieval timestamps do not establish original document publication dates.",
                "Source export metadata and published letter dates are not adjudicated action dates.",
                "Application/cycle identity, scientific features and denominator require independent review.",
            ],
        }
        parent_fd = _directory(self.destination.parent)
        try:
            os.mkdir(self.destination.name, 0o700, dir_fd=parent_fd)
            directory_fd = os.open(self.destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                   dir_fd=parent_fd)
            try:
                retained_names = set()
                for content, row in self._captures.values():
                    if row["retained_path"] not in retained_names:
                        _write(directory_fd, row["retained_path"], content)
                        retained_names.add(row["retained_path"])
                _write(directory_fd, "source-receipt.json",
                       (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
            finally:
                os.close(directory_fd)
        finally:
            os.close(parent_fd)
        return report
