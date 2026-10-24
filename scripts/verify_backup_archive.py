"""Offline, read-only integrity checks for PDUFA ZIP backups.

This does not claim Google Drive delivery, restore success, or source freshness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile


def verify_zip(path: Path) -> dict:
    result = {"archive": str(path), "valid": False, "files": 0, "bytes": 0, "error": None}
    try:
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if not members:
                raise ValueError("archive has no files")
            if len({m.filename for m in members}) != len(members):
                raise ValueError("archive contains duplicate paths")
            for member in members:
                normalized = member.filename.replace("\\", "/")
                parts = normalized.split("/")
                if normalized.startswith("/") or ".." in parts or "\x00" in normalized:
                    raise ValueError("unsafe archive member path")
                if member.flag_bits & 0x1:
                    raise ValueError("encrypted member cannot be verified")
            bad = archive.testzip()
            if bad:
                raise ValueError(f"CRC verification failed: {bad}")
            result.update(valid=True, files=len(members), bytes=sum(m.file_size for m in members))
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only PDUFA ZIP integrity verifier")
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    results = [verify_zip(path) for path in args.archives]
    print(json.dumps({"results": results, "all_valid": all(r["valid"] for r in results)}, indent=2))
    return 0 if all(r["valid"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
