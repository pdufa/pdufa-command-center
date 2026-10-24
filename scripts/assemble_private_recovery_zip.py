"""Assemble private PDUFA recovery ZIP from verified local PostgreSQL dumps.

Never uploads data or includes credentials. Output remains labeled UNTESTED until
isolated restores of both databases and deployment configuration are verified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--partial", required=True, type=Path)
    p.add_argument("--main-dump", required=True, type=Path)
    p.add_argument("--alpaca-dump", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    inputs = [(a.partial, "existing/PDUFA_partial_recovery.zip"), (a.main_dump, "databases/pdufa-main.dump"), (a.alpaca_dump, "databases/pdufa-alpaca.dump")]
    for source, _ in inputs:
        if not source.is_file() or source.stat().st_size == 0:
            p.error(f"Missing or empty input: {source}")
    if len({x.resolve() for x, _ in inputs + [(a.output, "")]}) != 4:
        p.error("Output and inputs must be different files")
    if a.output.exists():
        p.error("Output exists; refusing overwrite")
    with zipfile.ZipFile(a.partial) as z:
        if z.testzip() is not None:
            p.error("Partial archive CRC failure")
    manifest = {"status": "DATABASE_DUMPS_INCLUDED_RESTORE_NOT_YET_TESTED", "contents": [], "secrets_included": False,
                "remaining": ["Isolated restore and record count comparison", "Deployment configuration and secret re-provisioning"]}
    try:
        with zipfile.ZipFile(a.output, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as out:
            for source, name in inputs:
                digest = hashlib.sha256()
                with source.open("rb") as f, out.open(name, "w", force_zip64=True) as dest:
                    while chunk := f.read(1024 * 1024):
                        digest.update(chunk)
                        dest.write(chunk)
                manifest["contents"].append({"path": name, "bytes": source.stat().st_size, "sha256": digest.hexdigest()})
            out.writestr("ASSEMBLY_MANIFEST.json", json.dumps(manifest, indent=2))
        with zipfile.ZipFile(a.output) as z:
            if z.testzip() is not None:
                raise ValueError("Final archive CRC failure")
    except Exception:
        a.output.unlink(missing_ok=True)
        raise
    print(f"Created: {a.output}")
    print("NOT A VERIFIED FULL RESTORE: test both dumps in isolated databases.")
if __name__ == "__main__":
    main()
