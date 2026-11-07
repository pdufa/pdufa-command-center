"""Create bounded, paired FDA reviewer source batches off the public artifact tree.

Actual input: two private *blank* identity-gap role files produced earlier in the
same isolated FDA research workflow. No reviewer claims/identities or outcomes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.hop_fda_private_review_batches import prepare_private_review_batches

REPOSITORY = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split 124 UNADJUDICATED FDA letter references into private paired batches"
    )
    parser.add_argument("--private-first-review-json", type=Path, required=True)
    parser.add_argument("--private-second-review-json", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-aggregate-json", type=Path, required=True)
    args = parser.parse_args()

    first_file = args.private_first_review_json.resolve()
    second_file = args.private_second_review_json.resolve()
    destination = args.private_output_dir.resolve()
    public_file = args.public_aggregate_json.resolve()
    source_paths = (first_file, second_file)
    if (first_file == second_file
            or destination == public_file.parent
            or destination.is_relative_to(public_file.parent)
            or public_file.parent.is_relative_to(destination)
            or destination.is_relative_to(REPOSITORY)
            or destination in source_paths
            or any(p.is_relative_to(destination) for p in source_paths)
            or public_file in source_paths
            or "public_aggregate_only" in destination.parts
            or public_file.exists() or public_file.is_symlink()):
        raise ValueError("FDA source batches require separate private and public output paths")

    first = json.loads(first_file.read_text(encoding="utf-8"))
    second = json.loads(second_file.read_text(encoding="utf-8"))
    batches, audit = prepare_private_review_batches(
        first, second, max_references=20,
        expected_references=124, expected_groups=101,
    )
    outputs = []
    for b in batches:
        ident = b["batch_id"]
        outputs.extend([
            (destination / (ident + "_FIRST_unreviewed.json"),
             b["first_blank_reviewer_sources"]),
            (destination / (ident + "_SECOND_unreviewed.json"),
             b["second_blank_reviewer_sources"]),
        ])
    if any(p.exists() or p.is_symlink() for p, _ in outputs):
        raise FileExistsError("Cannot overwrite an existing private FDA reviewer batch")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    for target, payload in outputs:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(payload, output, indent=2, sort_keys=True)
            output.write("\n")
    public_file.parent.mkdir(parents=True, exist_ok=True)
    with public_file.open("x", encoding="utf-8") as out:
        json.dump(audit, out, indent=2, sort_keys=True)
        out.write("\n")
    print(json.dumps(audit, sort_keys=True))
    return 0  # Preparation only, not original FDA action verification.


if __name__ == "__main__":
    raise SystemExit(main())
