"""Verify PDUFA portable recovery bundles without modifying production data."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

FORMAT = "pdufa-portable-recovery-bundle-v1"

def verify_bundle(path: Path) -> dict:
    result = {"archive": str(path), "valid": False, "verified_files": 0, "errors": []}
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [m.filename for m in members if not m.is_dir()]
            if len(names) != len(set(names)):
                raise ValueError("duplicate ZIP entries")
            for member in members:
                name = member.filename.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/") or "\x00" in name or member.flag_bits & 1:
                    raise ValueError("unsafe or encrypted ZIP member")
            if archive.testzip() is not None:
                raise ValueError("ZIP CRC failure")
            manifest = json.loads(archive.read("RECOVERY_MANIFEST.json"))
            if manifest.get("format") != FORMAT:
                raise ValueError("unsupported recovery manifest format")
            entries = manifest.get("contents")
            if not isinstance(entries, list) or not entries:
                raise ValueError("missing manifest file list")
            listed = []
            for entry in entries:
                if not isinstance(entry, dict) or not all(k in entry for k in ("path", "bytes", "sha256")):
                    raise ValueError("malformed manifest file entry")
                name = entry["path"]
                listed.append(name)
                if name not in names:
                    result["errors"].append(f"missing file: {name}")
                    continue
                payload = archive.read(name)
                if len(payload) != entry["bytes"]:
                    result["errors"].append(f"byte length mismatch: {name}")
                if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                    result["errors"].append(f"SHA256 mismatch: {name}")
                if name.endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(payload)) as nested:
                        if nested.testzip() is not None:
                            result["errors"].append(f"nested ZIP CRC failure: {name}")
                result["verified_files"] += 1
            if len(listed) != len(set(listed)):
                raise ValueError("duplicate manifest entries")
            unexpected = set(names) - set(listed) - {"RECOVERY_MANIFEST.json", "README_RESTORE.txt"}
            if unexpected:
                result["errors"].append("unlisted ZIP entries: " + ", ".join(sorted(unexpected)))
            result["valid"] = not result["errors"]
            result["status"] = manifest.get("status", "UNKNOWN")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile, RuntimeError) as exc:
        result["errors"].append(str(exc))
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PDUFA portable recovery ZIP")
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = verify_bundle(args.archive)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
