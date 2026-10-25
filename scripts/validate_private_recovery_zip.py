"""Offline validation of recovery ZIP structure and recorded SHA-256 hashes.

Does not connect to production databases or claim successful database restoration.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

EXPECTED = {
    "existing/PDUFA_partial_recovery.zip",
    "databases/pdufa-main.dump",
    "databases/pdufa-alpaca.dump",
}

def validate(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entry names")
        if archive.testzip() is not None:
            raise ValueError("Archive CRC validation failed")
        manifest = json.loads(archive.read("ASSEMBLY_MANIFEST.json"))
        entries = manifest["contents"]
        paths = [entry["path"] for entry in entries]
        if len(paths) != len(set(paths)) or set(paths) != EXPECTED:
            raise ValueError("Missing, duplicate or unexpected manifest entries")
        if manifest.get("secrets_included") is not False:
            raise ValueError("Secrets inclusion status is not safe")
        for entry in entries:
            name = entry["path"]
            info = archive.getinfo(name)
            if info.file_size != entry["bytes"] or info.file_size == 0:
                raise ValueError(f"Size mismatch or empty entry: {name}")
            digest = hashlib.sha256()
            with archive.open(name) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA-256 mismatch: {name}")
    return {"archive_integrity": "PASS", "database_restore": "NOT_TESTED",
            "deployment_restore": "NOT_TESTED"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.archive), indent=2))

if __name__ == "__main__":
    main()
