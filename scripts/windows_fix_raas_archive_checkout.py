#!/usr/bin/env python3
"""Restore byte-exact, manifest-pinned archive files after Git CRLF conversion.

For local Windows checkout recovery only. Does not change HEAD, index, or remotes.
Refuses to proceed unless every pinned Git index blob matches the original
manifest hash and every current working file differs only by CRLF conversion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "archives/raas/read-only-record-manifest.json"


def git(*args: str, binary: bool = False):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          **({} if binary else {"text": True})).stdout


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Fix the local working copy after full verification")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("files"), list):
        print("STOP: pinned manifest is invalid.")
        return 2

    paths = []
    crlf_count = 0
    try:
        for entry in manifest["files"]:
            rel = entry["path"]
            expected = entry["sha256"]
            path = (ROOT / rel).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                raise ValueError(f"Missing or unsafe pinned file: {rel}")
            # Index blob is authoritative: never rebaseline altered historical data.
            index_bytes = git("show", f":{rel}", binary=True)
            if digest(index_bytes) != expected:
                raise ValueError(f"Git index differs from pinned archive hash: {rel}")
            working_bytes = path.read_bytes()
            if digest(working_bytes) == expected:
                paths.append((rel, False))
            elif digest(working_bytes.replace(b"\r\n", b"\n")) == expected:
                crlf_count += 1
                paths.append((rel, True))
            else:
                raise ValueError(f"File has content changes beyond CRLF; preserving: {rel}")
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"STOP: {exc}")
        return 2

    print(f"Verified {len(paths)} manifest-pinned records against Git index.")
    print(f"Files needing Windows CRLF restoration: {crlf_count}")
    if not args.apply:
        print("DRY RUN only. No files or settings changed.")
        print("To apply: py -3.13 scripts\\windows_fix_raas_archive_checkout.py --apply")
        return 0

    # Disable conversion in this clone only; never alter the user's global Git settings.
    # Git checkout-index may still apply configured attributes/filters, so restore
    # the *verified index blob bytes* directly, bypassing checkout conversion.
    try:
        git("config", "--local", "core.autocrlf", "false")
        expected_by_path = {entry["path"]: entry["sha256"]
                            for entry in manifest["files"]}
        restored = 0
        for rel, needs_restore in paths:
            if not needs_restore:
                continue
            path = (ROOT / rel).resolve()
            expected = expected_by_path[rel]
            index_bytes = git("show", f":{rel}", binary=True)
            if digest(index_bytes) != expected:
                raise ValueError(f"Index blob changed during repair: {rel}")
            current = path.read_bytes()
            if digest(current) != expected and digest(current.replace(b"\\r\\n", b"\\n")) != expected:
                raise ValueError(f"Working file changed during repair; preserving: {rel}")

            # Atomic file replacement on the same volume; never invoke Git's
            # checkout filters and never rebaseline an archive checksum.
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", prefix=".pdufa-archive-", suffix=".tmp",
                    dir=path.parent, delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(index_bytes)
                if digest(temporary.read_bytes()) != expected:
                    raise ValueError(f"Temporary file failed checksum: {rel}")
                os.replace(temporary, path)
                temporary = None
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            if digest(path.read_bytes()) != expected:
                raise ValueError(f"Restored bytes do not match manifest: {rel}")
            restored += 1
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"STOP: {exc}")
        return 2

    print(f"RESTORED: {restored} pinned records now match stored checksums.")
    print("Git config set locally: core.autocrlf=false")
    print("No remote files, Git commits, or scientific content were changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
