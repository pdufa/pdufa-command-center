"""Prepare two BLANK private FDA identity-gap source reviewer packet sets.

Neither a generated packet nor a future matching reviewer claim constitutes
independent adjudication of FDA outcome labels. Never upload private reviewer
data to a public GitHub Actions artifact or live database.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.hop_fda_identity_gap_dual_review import blank_identity_gap_dual_reviews


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare two independent empty FDA source reviewer handoff packets"
    )
    parser.add_argument("--private-enriched-packets", type=Path, required=True)
    parser.add_argument("--private-first-review-json", type=Path, required=True)
    parser.add_argument("--private-second-review-json", type=Path, required=True)
    parser.add_argument("--public-audit-json", type=Path, required=True)
    args = parser.parse_args()
    source = args.private_enriched_packets.resolve()
    first_path = args.private_first_review_json.resolve()
    second_path = args.private_second_review_json.resolve()
    audit_path = args.public_audit_json.resolve()
    paths = (source, first_path, second_path, audit_path)
    if len(set(paths)) != len(paths):
        raise ValueError("FDA source reviewers and public audit must use distinct files")
    # The private reviewer packets must not end up in the repository, in the
    # public aggregate artifact directory, or in a public audit's ancestry.
    private_dir = first_path.parent
    public_dir = audit_path.parent
    repository = Path(__file__).resolve().parents[3]
    if (second_path.parent != private_dir
            or private_dir == public_dir
            or private_dir.is_relative_to(public_dir)
            or public_dir.is_relative_to(private_dir)
            or private_dir.is_relative_to(repository)
            or "public_aggregate_only" in private_dir.parts
            or any(path.exists() or path.is_symlink()
                   for path in (first_path, second_path, audit_path))):
        raise ValueError("FDA private reviewer files require a separate safe directory and new output names")
    enriched = json.loads(source.read_text(encoding="utf-8"))
    first, second, audit = blank_identity_gap_dual_reviews(enriched)
    if (audit["model_eligible_records"] != 0
            or audit["independent_reviews_completed"] != 0
            or audit["review_cycle_outcomes_verified"] != 0):
        raise ValueError("FDA source packets may never self-authorize model review")
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Files already generated elsewhere in this directory remain private.
    private_dir.chmod(0o700)
    for path, obj in ((first_path, first), (second_path, second)):
        # O_EXCL prevents overwriting a previous independent review;
        # O_NOFOLLOW rejects a last-moment symlink replacement on POSIX.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(obj, stream, indent=2, sort_keys=True)
            stream.write("\n")
    public_dir.mkdir(parents=True, exist_ok=True)
    with audit_path.open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write("\n")
    # Only aggregate counts reach this stream, never reviewer identities.
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0  # Source-blank packet generation only; NEVER outcome adjudication.


if __name__ == "__main__":
    raise SystemExit(main())
