"""Offline safety tests for private recovery ZIP assembly; no live database access."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assemble_private_recovery_zip.py"

def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

def test_assembles_and_hashes(tmp_path):
    partial = tmp_path / "partial.zip"
    with zipfile.ZipFile(partial, "w") as z:
        z.writestr("README.txt", "partial snapshot")
    main = tmp_path / "main.dump"
    alpaca = tmp_path / "alpaca.dump"
    main.write_bytes(b"synthetic main pgdump")
    alpaca.write_bytes(b"synthetic alpaca pgdump")
    output = tmp_path / "complete.zip"
    r = run("--partial", partial, "--main-dump", main, "--alpaca-dump", alpaca, "--output", output)
    assert r.returncode == 0, r.stderr
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        manifest = json.loads(z.read("ASSEMBLY_MANIFEST.json"))
        assert "NOT_YET_TESTED" in manifest["status"]
        assert len(manifest["contents"]) == 3
        for item in manifest["contents"]:
            assert item["bytes"] == len(z.read(item["path"]))
            assert item["sha256"] == hashlib.sha256(z.read(item["path"])).hexdigest()
        assert z.read("databases/pdufa-main.dump") == main.read_bytes()

def test_missing_dump_rejected(tmp_path):
    partial = tmp_path / "partial.zip"
    with zipfile.ZipFile(partial, "w") as z:
        z.writestr("ok", "ok")
    r = run("--partial", partial, "--main-dump", tmp_path / "missing.dump", "--alpaca-dump", tmp_path / "missing2.dump", "--output", tmp_path / "out.zip")
    assert r.returncode != 0
    assert not (tmp_path / "out.zip").exists()

def test_corrupt_partial_rejected(tmp_path):
    partial = tmp_path / "partial.zip"
    partial.write_bytes(b"not a zip")
    dump = tmp_path / "dump"
    dump.write_bytes(b"synthetic")
    r = run("--partial", partial, "--main-dump", dump, "--alpaca-dump", dump, "--output", tmp_path / "out.zip")
    assert r.returncode != 0
    assert not (tmp_path / "out.zip").exists()

def test_existing_output_not_overwritten(tmp_path):
    partial = tmp_path / "partial.zip"
    with zipfile.ZipFile(partial, "w") as z:
        z.writestr("ok", "ok")
    dump = tmp_path / "dump"
    dump.write_bytes(b"synthetic")
    output = tmp_path / "out.zip"
    output.write_bytes(b"keep")
    r = run("--partial", partial, "--main-dump", dump, "--alpaca-dump", dump, "--output", output)
    assert r.returncode != 0
    assert output.read_bytes() == b"keep"
