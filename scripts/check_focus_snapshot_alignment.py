"""Read-only reconciliation of packaged and frontend FOCUS roster snapshots.

Never rewrites either snapshot, membership, or historical assessment exports.
Usage: python scripts/check_focus_snapshot_alignment.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
BACKEND = ROOT / "new-platform/backend/app/data/focus_snapshot.json"

def compare(frontend: dict, backend: dict) -> dict:
    def index(data):
        rows = data.get("records")
        if not isinstance(rows, list):
            raise ValueError("FOCUS records must be a list")
        result = {}
        for row in rows:
            nct = row.get("nct")
            if not isinstance(nct, str) or not nct or nct in result:
                raise ValueError("Missing or duplicate exact NCT")
            result[nct] = row
        return result
    f, b = index(frontend), index(backend)
    field_differences = {}
    for nct in sorted(f.keys() & b.keys()):
        differing = sorted(
            key for key in f[nct].keys() | b[nct].keys()
            if f[nct].get(key) != b[nct].get(key)
        )
        if differing:
            field_differences[nct] = {
                "ticker": f[nct].get("ticker"),
                "fields": differing,
                "frontendMarketCap": f[nct].get("marketCap") if "marketCap" in differing else None,
                "backendMarketCap": b[nct].get("marketCap") if "marketCap" in differing else None,
            }
    return {
        "fieldDifferences": field_differences,
        "marketCapOnlyDrift": bool(field_differences) and all(
            row["fields"] == ["marketCap"] for row in field_differences.values()
        ) and f.keys() == b.keys(),
        "frontendAsOf": frontend.get("asOf"),
        "backendAsOf": backend.get("asOf"),
        "frontendCount": len(f),
        "backendCount": len(b),
        "frontendOnlyNcts": sorted(f.keys() - b.keys()),
        "backendOnlyNcts": sorted(b.keys() - f.keys()),
        "changedNcts": sorted(nct for nct in f.keys() & b.keys() if f[nct] != b[nct]),
        "aligned": frontend.get("asOf") == backend.get("asOf") and f == b,
        "action": "REVIEW_CANONICAL_SOURCE_BEFORE_REPACKAGING",
    }

def main() -> int:
    result = compare(json.loads(FRONTEND.read_text(encoding="utf-8")),
                     json.loads(BACKEND.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["aligned"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
