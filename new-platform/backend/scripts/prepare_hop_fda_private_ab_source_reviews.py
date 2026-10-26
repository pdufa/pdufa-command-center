"""Prepare private A/B FDA source inspections from a quarantined 101-packet list.

NEVER upload either reviewer's packet JSON to GitHub artifacts or public URLs.
The saved aggregate contains counts only and no application IDs or PDF hashes.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_fda_gap_dual_handoff import prepare_gap_source_review_handoffs

REPO = Path(__file__).resolve().parents[3]
PINNED = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
          / "hop_fda_grouped_evidence_search_packets_20261025.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create separate UNREVIEWED FDA original-source A/B packets locally"
    )
    parser.add_argument("--private-enriched-packets", type=Path, required=True)
    parser.add_argument("--private-original-grouped-packets", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()

    # Prevent inadvertent version-control or CI aggregate export of private
    # per-letter source identifiers and source URLs.
    dest = args.private_output_dir.resolve()
    source = args.private_enriched_packets.resolve()
    baseline_source = args.private_original_grouped_packets.resolve()
    if dest == REPO or dest.is_relative_to(REPO):
        raise ValueError("FDA reviewer files must remain outside the repository")
    if dest == source or dest in source.parents or dest == baseline_source or dest in baseline_source.parents:
        raise ValueError("FDA private source file must not be overwritten")
    pinned = json.loads(PINNED.read_text(encoding="utf-8"))
    enriched = json.loads(source.read_text(encoding="utf-8"))
    original_grouped = json.loads(baseline_source.read_text(encoding="utf-8"))
    first, second, aggregate = prepare_gap_source_review_handoffs(
        enriched, original_grouped, pinned_audit=pinned, as_of=args.as_of,
    )
    paths = [
        dest / "first_blank_original_fda_source_review.json",
        dest / "second_blank_original_fda_source_review.json",
        dest / "local_reviewer_handoff_counts_only.json",
    ]
    if any(path.exists() for path in paths):
        raise FileExistsError("Existing FDA reviewer packet output must not be overwritten")
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path, body in zip(paths, (first, second, aggregate)):
        with path.open("x", encoding="utf-8") as stream:
            json.dump(body, stream, indent=2, sort_keys=True)
            stream.write("\n")
        path.chmod(0o600)
    print(json.dumps(aggregate, sort_keys=True))
    # Exit success certifies only safe preparation, never FDA approval labels.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
