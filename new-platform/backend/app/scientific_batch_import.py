"""Explicit, bounded scientific trial batch importer for isolated review.

Usage (backend working directory):
    python -m app.scientific_batch_import --batch-file trial_ids.txt

One exact NCT identifier per line; blank lines and # comments are allowed.
Emits one structured JSON progress record per trial, followed by a summary.
Never schedules itself, enables trading, or writes to production.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError

from . import scientific_import

MAX_TRIALS = 25
MAX_INPUT_BYTES = 4096
NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")


def parse_batch_file(path: Path) -> list[str]:
    """Validate the entire input before importing a single record."""
    with path.open("rb") as handle:
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Batch file exceeds size limit")
    lines = raw.decode("utf-8").splitlines()
    ids = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not ids:
        raise ValueError("Batch file contains no NCT identifiers")
    if len(ids) > MAX_TRIALS:
        raise ValueError(f"Batch exceeds {MAX_TRIALS} trials")
    if any(not NCT_PATTERN.fullmatch(nct_id) for nct_id in ids):
        raise ValueError("Batch requires one exact NCT identifier per line")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NCT identifier in batch")
    return ids


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_batch(
    ids: list[str],
    *,
    import_trial: Callable[[str], str] | None = None,
    emit: Callable[[dict], None] | None = None,
    delay_seconds: float = 0.0,
) -> dict:
    """Run sequentially; isolate per-trial failures and emit bounded progress."""
    if not ids or len(ids) > MAX_TRIALS or any(not NCT_PATTERN.fullmatch(x) for x in ids):
        raise ValueError("Invalid bounded batch")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NCT identifier in batch")
    if not scientific_import.DATABASE_URL.startswith("postgresql+psycopg://"):
        raise RuntimeError("Persistent PostgreSQL required; refusing SQLite import")
    if delay_seconds < 0:
        raise ValueError("Delay must be nonnegative")

    importer = import_trial or scientific_import.import_one
    reporter = emit or (lambda event: print(json.dumps(event, sort_keys=True), flush=True))
    counts = {"imported": 0, "already_exists": 0, "failed": 0}
    total = len(ids)
    reporter({"event": "batch_started", "total": total, "timestamp": _utc_now()})
    for index, nct_id in enumerate(ids, 1):
        if index > 1 and delay_seconds:
            time.sleep(delay_seconds)
        event = {"event": "trial_finished", "index": index, "total": total,
                 "nct_id": nct_id, "timestamp": _utc_now()}
        try:
            status = importer(nct_id)
            if status not in ("imported", "already_exists"):
                raise ValueError("Unexpected importer status")
            counts[status] += 1
            event["status"] = status
        except Exception as exc:
            counts["failed"] += 1
            event["status"] = "failed"
            event["error_type"] = type(exc).__name__
            if isinstance(exc, HTTPError):
                event["http_status"] = exc.code
        event["processed"] = index
        event.update(counts)
        reporter(event)
    summary = {"event": "batch_finished", "total": total, "processed": total,
               **counts, "timestamp": _utc_now()}
    reporter(summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ids = parse_batch_file(args.batch_file)
        summary = run_batch(ids, delay_seconds=1.0)
    except (ValueError, RuntimeError, OSError, UnicodeError) as exc:
        # Do not echo file paths, connection settings, URLs, or registry responses.
        print(json.dumps({"event": "batch_rejected", "error_type": type(exc).__name__}), flush=True)
        return 1
    return 0 if summary["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
