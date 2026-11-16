"""Offline CLI for a historical FDA evidence collection worklist.

Example:
 python -m assessment_levels_07_20.historical_worklist_cli --manifest cohort.json --sources sources.json

Reads local JSON only; emits a JSON worklist to stdout. No network calls,
FDA outcome lookup, persistent writes, scoring, or production integration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .historical_research_worklist import build_historical_research_worklist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        result = build_historical_research_worklist(manifest, sources)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc),
                          "collection_executed": False}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
