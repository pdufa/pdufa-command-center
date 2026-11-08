"""Safely replicate a PRE-ENCRYPTED PDUFA recovery archive.

Modes:
  clouds: copy same age-encrypted bytes to Amazon S3 and Backblaze B2
  icloud: atomically stage identical bytes inside an existing local iCloud Drive folder
  verify-clouds: download both objects and compare SHA-256 (restore test still required)

This tool does NOT export databases, encrypt plaintext, enable bucket locks,
schedule jobs, or verify that iCloud has finished synchronizing to Apple servers.
Never log cloud credentials or place them in Git.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import tempfile


@dataclass(frozen=True)
class Target:
    label: str
    bucket: str
    region: str
    key_id: str
    secret: str
    endpoint: str | None = None


def require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        raise RuntimeError(f"Required configuration missing: {key}")
    return value


def targets() -> list[Target]:
    return [
        Target(
            "Amazon S3", require_env("PDUFA_AWS_BACKUP_BUCKET"),
            require_env("PDUFA_AWS_BACKUP_REGION"),
            require_env("PDUFA_AWS_BACKUP_KEY_ID"),
            require_env("PDUFA_AWS_BACKUP_SECRET"),
        ),
        Target(
            "Backblaze B2", require_env("PDUFA_B2_BACKUP_BUCKET"),
            require_env("PDUFA_B2_BACKUP_REGION"),
            require_env("PDUFA_B2_BACKUP_KEY_ID"),
            require_env("PDUFA_B2_BACKUP_SECRET"),
            require_env("PDUFA_B2_BACKUP_ENDPOINT"),
        ),
    ]


def inspect_archive(path: Path) -> tuple[str, int]:
    if not path.is_file() or path.suffix != ".age":
        raise ValueError("Expected an existing .age-encrypted recovery archive")
    size = path.stat().st_size
    if size < 80:
        raise ValueError("Archive is unexpectedly small")
    with path.open("rb") as fp:
        if fp.readline(128) != b"age-encryption.org/v1\n":
            raise ValueError("Not an age v1 encrypted archive")
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest(), size


def remote_key(path: Path, digest: str, date: str) -> str:
    return f"pdufa-recovery/{date}/{digest}-{path.name}"


def client_for(target: Target):
    import boto3  # not needed for local/offline tests
    return boto3.client(
        "s3", region_name=target.region,
        endpoint_url=target.endpoint,
        aws_access_key_id=target.key_id,
        aws_secret_access_key=target.secret,
    )


def verify_head(client, target: Target, key: str, digest: str, size: int) -> None:
    head = client.head_object(Bucket=target.bucket, Key=key)
    if int(head["ContentLength"]) != size or head.get("Metadata", {}).get("sha256") != digest:
        raise RuntimeError(f"{target.label}: remote size/digest metadata mismatch")


def upload_clouds(path: Path, digest: str, size: int, date: str) -> None:
    key = remote_key(path, digest, date)
    for target in targets():
        client = client_for(target)
        # An exact digest-qualified key makes retries idempotent. Bucket-level
        # versioning/retention must still be configured independently.
        client.upload_file(str(path), target.bucket, key,
                           ExtraArgs={"Metadata": {"sha256": digest}})
        verify_head(client, target, key, digest, size)
        print(f"{target.label}: upload recorded and metadata verified")
    print("Cloud object-content verification and isolated restore: NOT YET TESTED")


def verify_clouds(path: Path, digest: str, size: int, date: str) -> None:
    key = remote_key(path, digest, date)
    for target in targets():
        client = client_for(target)
        verify_head(client, target, key, digest, size)
        with tempfile.TemporaryDirectory(prefix="pdufa-restore-check-") as temp:
            out = Path(temp) / path.name
            client.download_file(target.bucket, key, str(out))
            remote_digest, remote_size = inspect_archive(out)
            if (remote_digest, remote_size) != (digest, size):
                raise RuntimeError(f"{target.label}: round-trip SHA-256 mismatch")
        print(f"{target.label}: byte-identical round trip verified")
    print("Database restore verification: STILL REQUIRED")


def stage_icloud(path: Path, destination_dir: Path, digest: str, size: int) -> None:
    if not destination_dir.is_dir():
        raise ValueError("iCloud Drive destination must already exist and be synced by macOS")
    destination = destination_dir / path.name
    if destination.exists():
        existing_digest, existing_size = inspect_archive(destination)
        if (existing_digest, existing_size) != (digest, size):
            raise RuntimeError("Existing iCloud file differs; refusing to overwrite")
        print("iCloud Drive: identical local file already staged")
        return
    temporary = destination_dir / (path.name + ".partial")
    if temporary.exists():
        raise RuntimeError("Previous partial transfer exists; inspect it before retrying")
    try:
        with path.open("rb") as source, temporary.open("xb") as target:
            shutil.copyfileobj(source, target, length=4 * 1024 * 1024)
        staged_digest, staged_size = inspect_archive_with_suffix(temporary)
        if (staged_digest, staged_size) != (digest, size):
            raise RuntimeError("Local iCloud staging SHA-256 mismatch")
        temporary.rename(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print("iCloud Drive: byte-identical LOCAL file staged")
    print("Apple cloud sync and cloud restore: NOT YET VERIFIED")


def inspect_archive_with_suffix(path: Path) -> tuple[str, int]:
    # Temporary files may have a .partial suffix, but the age header is required.
    if not path.is_file():
        raise ValueError("Missing temporary archive")
    with path.open("rb") as fp:
        if fp.readline(128) != b"age-encryption.org/v1\n":
            raise ValueError("Invalid age header in temporary file")
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest(), size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("clouds", "icloud", "verify-clouds"))
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--icloud-dir", type=Path)
    args = parser.parse_args()
    archive = args.archive.expanduser().resolve()
    digest, size = inspect_archive(archive)
    if args.mode == "clouds":
        upload_clouds(archive, digest, size, args.date)
    elif args.mode == "verify-clouds":
        verify_clouds(archive, digest, size, args.date)
    else:
        if args.icloud_dir is None:
            parser.error("--icloud-dir is required for icloud mode")
        stage_icloud(archive, args.icloud_dir.expanduser().resolve(), digest, size)


if __name__ == "__main__":
    main()
