"""Explicit opt-in CLI for downloading public research documents to a local folder.

Research-only: never backdates retrieval, never marks a download as a
historical snapshot, and never accesses outcome documents implicitly.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .discovery_source_packaging import package_discovery_source_bytes


def download_discovery_source(url: str, destination: Path, *, max_bytes: int = 20_000_000) -> dict:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Only HTTPS source URLs are supported")
    if parts.username or parts.password:
        raise ValueError("Credential-bearing URLs are forbidden")
    request = Request(url, headers={"User-Agent": "PDUFA-Research-Discovery/1.0"})
    with urlopen(request, timeout=30) as response:
        final_url = urlsplit(response.url)
        if final_url.scheme != "https" or not final_url.hostname:
            raise ValueError("Redirect to non-HTTPS URL forbidden")
        if final_url.username or final_url.password:
            raise ValueError("Credential-bearing redirect URL forbidden")
        data = response.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise ValueError("Empty or oversized document")
    retrieved_at = datetime.now(timezone.utc).isoformat()
    record = package_discovery_source_bytes(url, data, retrieved_at)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata = destination.with_suffix(destination.suffix + ".json")
    if destination.exists() or metadata.exists():
        raise FileExistsError("Destination already exists; refusing overwrite")
    # Exclusive creation protects against accidental replacement and concurrent runs.
    # If metadata persistence fails, remove the newly created document to avoid
    # leaving an untracked artifact that could be mistaken for verified evidence.
    with destination.open("xb") as handle:
        handle.write(data)
    try:
        with metadata.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(record, indent=2) + "\n")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Opt-in public source download, discovery-only")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(download_discovery_source(args.url, args.output), indent=2))


if __name__ == "__main__":
    main()
