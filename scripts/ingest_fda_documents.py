"""Retain bounded FDA PDF bytes for quarantined source review, never model clearance.

Offline mode checks explicitly supplied originals against their declared hashes.
Download mode uses the inherited proxy/TLS policy and rejects redirects. No output
directory means dry run: offline bytes are inspected; downloads are not requested.
An explicit output directory must be new. Existing archives are never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_MANIFEST_BYTES = 1_000_000
MAX_PDF_BYTES = 20_000_000
MAX_TOTAL_BYTES = 100_000_000
MAX_DOCUMENTS = 20
FDA_HOSTS = frozenset({"www.fda.gov", "accessdata.fda.gov", "www.accessdata.fda.gov",
                       "download.open.fda.gov"})
COMMON_FIELDS = {"id", "url", "document_date", "publication_date"}


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _directory(path: Path) -> int:
    """Open every absolute directory component without following symlinks."""
    absolute = path.absolute()
    if ".." in absolute.parts:
        raise ValueError("directory traversal is not allowed")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _relative(value: object) -> tuple[str, ...]:
    if (not isinstance(value, str) or not value or len(value) > 500
            or "\\" in value or any(ord(c) < 32 for c in value)):
        raise ValueError("invalid relative PDF path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("relative PDF path must not traverse directories")
    return path.parts


def _read_file(root: Path, relative: str, limit: int) -> bytes:
    parts = _relative(relative)
    fd = _directory(root)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=fd)
            os.close(fd)
            fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=fd)
        try:
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
                raise ValueError("input must be a bounded nonempty regular file")
            chunks, length = [], 0
            while True:
                chunk = os.read(file_fd, min(65536, limit + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                if length > limit:
                    raise ValueError("input exceeds byte limit")
            after = os.fstat(file_fd)
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    or length != before.st_size):
                raise ValueError("input changed while being read")
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def _official_url(value: object) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 2048
            or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value):
        raise ValueError("official FDA HTTPS URL required")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in FDA_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port is not None or parsed.query or parsed.fragment
            or parsed.path in ("", "/")):
        raise ValueError("official FDA HTTPS URL required without credentials or redirects")
    return value


def _declared_date(value: object, *, as_of: date) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("declared document/publication dates must be ISO dates or null")
    if date.fromisoformat(value) > as_of:
        raise ValueError("declared document/publication date is in the future")


def parse_manifest(raw: bytes, *, mode: str, as_of: date) -> list[dict]:
    if mode not in {"offline", "download"}:
        raise ValueError("mode must be offline or download")
    if not 0 < len(raw) <= MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds byte limit or is empty")
    manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_no_duplicate_keys)
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "documents"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1):
        raise ValueError("manifest requires exact schema_version 1 envelope")
    documents = manifest["documents"]
    if not isinstance(documents, list) or not 1 <= len(documents) <= MAX_DOCUMENTS:
        raise ValueError("manifest requires 1..20 documents")
    identifiers, paths = set(), set()
    for item in documents:
        required = COMMON_FIELDS | ({"relative_path", "expected_sha256"} if mode == "offline" else set())
        allowed = required | ({"expected_sha256"} if mode == "download" else set())
        if not isinstance(item, dict) or not required <= set(item) <= allowed:
            raise ValueError("missing or unexpected document fields; verification flags are forbidden")
        identifier = item["id"]
        if (not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", identifier)
                or identifier in identifiers):
            raise ValueError("invalid or duplicate document id")
        identifiers.add(identifier)
        _official_url(item["url"])
        for field in ("document_date", "publication_date"):
            _declared_date(item[field], as_of=as_of)
        if "expected_sha256" in item and (not isinstance(item["expected_sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["expected_sha256"])):
            raise ValueError("expected_sha256 must be a lowercase SHA-256 digest")
        if mode == "offline":
            _relative(item["relative_path"])
            if item["relative_path"] in paths:
                raise ValueError("duplicate offline PDF path")
            paths.add(item["relative_path"])
    return documents


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("FDA redirect rejected; review the original URL separately")


def fetch_pdf(url: str) -> bytes:
    """Acquire only through normal inherited proxy and default verified TLS."""
    _official_url(url)
    request = Request(url, headers={"User-Agent": "PDUFA-quarantined-document-intake/1.0",
                                    "Accept": "application/pdf"})
    with build_opener(_RejectRedirect()).open(request, timeout=20) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("exact FDA URL did not return HTTP 200")
        if response.headers.get_content_type() not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("FDA response is not a PDF media type")
        content = response.read(MAX_PDF_BYTES + 1)
    _pdf(content)
    return content


def _pdf(content: bytes) -> None:
    if not isinstance(content, bytes) or not 5 <= len(content) <= MAX_PDF_BYTES:
        raise ValueError("PDF exceeds byte limit or is empty")
    if not content.startswith(b"%PDF-"):
        raise ValueError("PDF header missing; content requires review")


def _write_exclusive(directory_fd: int, name: str, content: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def ingest(manifest_path: Path, *, mode: str = "offline", source_dir: Path | None = None,
           output_dir: Path | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware receipt time required")
    timestamp = now.astimezone(timezone.utc).isoformat()
    manifest_path = Path(manifest_path)
    raw = _read_file(manifest_path.parent, manifest_path.name, MAX_MANIFEST_BYTES)
    documents = parse_manifest(raw, mode=mode, as_of=now.date())
    if mode == "offline" and source_dir is None:
        raise ValueError("offline mode requires an explicit source directory")
    output = Path(output_dir).absolute() if output_dir is not None else None
    if output is not None:
        parent_fd = _directory(output.parent)
        try:
            try:
                os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError("output directory must be new; existing data is never overwritten")
        finally:
            os.close(parent_fd)
    blobs, records, total = {}, [], 0
    for item in documents:
        content = None
        if mode == "offline":
            content = _read_file(Path(source_dir), item["relative_path"], MAX_PDF_BYTES)
        elif output is not None:
            content = fetch_pdf(item["url"])
        digest = None
        if content is not None:
            _pdf(content)
            total += len(content)
            if total > MAX_TOTAL_BYTES:
                raise ValueError("batch exceeds total byte limit")
            digest = hashlib.sha256(content).hexdigest()
            if item.get("expected_sha256", digest) != digest:
                raise ValueError("original document SHA-256 mismatch")
            blobs[digest] = content
        records.append({
            "id": item["id"], "source_url_as_declared": item["url"],
            "document_date_as_declared": item["document_date"],
            "publication_date_as_declared": item["publication_date"],
            "received_at": timestamp if content is not None else None,
            "retrieved_at": timestamp if content is not None and mode == "download" else None,
            "capture_status": ("MANIFEST_VALIDATED_NOT_FETCHED" if content is None else
                               "OFFLINE_BYTES_INTEGRITY_CONFIRMED" if mode == "offline" else
                               "HTTP_PDF_BYTES_RECEIVED"),
            "sha256": digest, "bytes": len(content) if content is not None else None,
            "retained_path": f"{digest}.pdf" if output is not None else None,
            "original_source_authenticity_verified": False,
            "independently_verified": False, "review_cycle_verified": False,
            "outcome": None, "model_eligible": False,
        })
    report = {
        "schema_version": 1, "status": "QUARANTINED_DOCUMENT_RECEIPT_ONLY",
        "mode": mode, "dry_run": output is None, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "document_count": len(records), "bytes_inspected": total, "records": records,
        "independently_verified_pass_records": 0, "independently_verified_fail_records": 0,
        "complete_application_denominator_verified": False, "model_eligible_records": 0,
        "prediction_probability": None, "trade_authorized": False,
        "limitations": [
            "A hash or PDF header checks byte integrity, not source truth or valid PDF semantics.",
            "Offline source URLs and dates are declarations, not authenticated retrieval evidence.",
            "Document dates are not publication dates or effective FDA action dates.",
            "Independent application/cycle/outcome review and predecision evidence remain required.",
        ],
    }
    if output is not None:
        parent_fd = _directory(output.parent)
        try:
            os.mkdir(output.name, mode=0o700, dir_fd=parent_fd)
            archive_fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=parent_fd)
            try:
                _write_exclusive(archive_fd, "manifest.original.json", raw)
                for digest, content in blobs.items():
                    _write_exclusive(archive_fd, f"{digest}.pdf", content)
                _write_exclusive(archive_fd, "receipt.json",
                                 (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
            finally:
                os.close(archive_fd)
        finally:
            os.close(parent_fd)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--mode", choices=("offline", "download"), default="offline")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        report = ingest(args.manifest, mode=args.mode, source_dir=args.source_dir,
                        output_dir=args.output_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        print(f"DOCUMENT_INTAKE_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
