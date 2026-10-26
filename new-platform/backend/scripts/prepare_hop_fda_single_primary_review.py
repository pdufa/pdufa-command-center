"""One-primary-reviewer private FDA source worksheet and aggregate-only triage.

The existing dual-review and SHA custody paths remain unchanged. This CLI
creates seven FIRST-role-only blank batches OR checks privately supplied
primary claims; it does not make FDA action labels or upload private data.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from app.hop_fda_single_primary_review import (
    prepare_single_primary_batches, reconcile_single_primary_claims,
)

REPOSITORY = Path(__file__).resolve().parents[3]


def main() -> int:
    p = argparse.ArgumentParser(description="One primary FDA source reviewer; escalation optional")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-primary-batches", action="store_true")
    mode.add_argument("--triage-primary-claims", action="store_true")
    p.add_argument("--private-blank-first-json", type=Path, required=True)
    p.add_argument("--private-claims-json", type=Path)
    p.add_argument("--private-output-dir", type=Path)
    p.add_argument("--public-aggregate-json", type=Path, required=True)
    p.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 10, 25))
    args = p.parse_args()
    source = args.private_blank_first_json.resolve()
    public = args.public_aggregate_json.resolve()
    if (not source.is_file() or source == public
            or public.exists() or public.is_symlink()
            or source == REPOSITORY or "public_aggregate_only" in source.parts):
        raise ValueError("Private FDA reviewer source/public audit paths unsafe")
    if args.as_of != date(2026, 10, 25):
        raise ValueError("Historical FDA source research must use pinned cutoff")

    blank = json.loads(source.read_text(encoding="utf-8"))
    if args.prepare_primary_batches:
        if args.private_claims_json is not None or args.private_output_dir is None:
            raise ValueError("One-primary handoff needs only a private output directory")
        destination = args.private_output_dir.resolve()
        if (destination.exists() or destination.is_symlink()
                or destination == source.parent or source.is_relative_to(destination)
                or destination == public.parent
                or destination.is_relative_to(public.parent)
                or public.parent.is_relative_to(destination)
                or destination.is_relative_to(REPOSITORY)
                or "public_aggregate_only" in destination.parts):
            raise ValueError("FDA primary review must use a new separate private output folder")
        batches, audit = prepare_single_primary_batches(blank)
        destination.mkdir(parents=True, mode=0o700)
        destination.chmod(0o700)
        for batch in batches:
            path = destination / (batch["batch_id"] + "_PRIMARY_unreviewed.json")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(batch["primary_blank_source_rows"], out, indent=2, sort_keys=True)
                out.write("\n")
    else:
        if args.private_claims_json is None or args.private_output_dir is not None:
            raise ValueError("Triage requires private completed primary claims only")
        claims_file = args.private_claims_json.resolve()
        if (claims_file == source or claims_file == public
                or not claims_file.is_file()
                or "public_aggregate_only" in claims_file.parts):
            raise ValueError("FDA primary claims must be private and separate")
        claims = json.loads(claims_file.read_text(encoding="utf-8"))
        audit = reconcile_single_primary_claims(blank, claims, as_of=args.as_of)
    public.parent.mkdir(parents=True, exist_ok=True)
    with public.open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
