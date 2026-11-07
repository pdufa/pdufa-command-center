"""Internal-only, opt-in PostgreSQL logical backup for authorized Render shell use.

Run inside the service environment with DATABASE_URL set. Writes only a local
backup file. Does not expose HTTP routes, change the database, upload secrets,
or trigger automatically.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an offline PostgreSQL custom-format dump")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        parser.error("DATABASE_URL is not configured")
    parsed = urlsplit(raw.replace("postgresql+psycopg://", "postgresql://", 1))
    if parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname or not parsed.path.strip("/"):
        parser.error("DATABASE_URL must identify a PostgreSQL database")
    if not shutil.which("pg_dump"):
        parser.error("pg_dump is not installed in this runtime")
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error("output already exists; refusing to overwrite")
    if not output.parent.is_dir():
        parser.error("output directory does not exist")
    # Keep connection credentials in environment, never command-line arguments or logs.
    env = os.environ.copy()
    env["PGHOST"] = parsed.hostname
    env["PGPORT"] = str(parsed.port or 5432)
    env["PGUSER"] = unquote(parsed.username or "")
    env["PGPASSWORD"] = unquote(parsed.password or "")
    env["PGDATABASE"] = unquote(parsed.path.lstrip("/"))
    env["PGSSLMODE"] = "require"
    created = False
    try:
        # Exclusive creation protects an existing backup even if it appears
        # after the preflight check. Dumps contain private application data.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(fd, "wb") as target:
            result = subprocess.run(
                ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file=-"],
                stdout=target, stderr=subprocess.PIPE, env=env, timeout=900, check=False
            )
        if result.returncode != 0 or output.stat().st_size == 0:
            output.unlink(missing_ok=True)
            print("Backup failed; no valid archive created. Check pg_dump availability and database permissions.", file=sys.stderr)
            return 1
    except (OSError, subprocess.TimeoutExpired) as exc:
        if created:
            output.unlink(missing_ok=True)
        print(f"Backup failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"Created local PostgreSQL dump: {output.name} ({output.stat().st_size} bytes)")
    print("NOT a verified full restore. Securely transfer and test restore into an isolated database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
