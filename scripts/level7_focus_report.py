"""Read-only Level 7 report over the packaged FOCUS roster.

Usage:
  python scripts/level7_focus_report.py --db path/to/evidence.sqlite3
  python scripts/level7_focus_report.py --db path/to/evidence.sqlite3 --output report.json
This does not fetch evidence, alter roster membership, or generate predictions.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from level7_focus_coverage import focus_level7_coverage
from level7_store import EvidenceStore

SNAPSHOT = ROOT / "new-platform/frontend/data/p3PostDataActive.json"

def run(db_path: Path, snapshot_path: Path = SNAPSHOT) -> dict:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    members = snapshot.get("records")
    if not isinstance(members, list) or len(members) != 32:
        raise ValueError("FOCUS report requires exactly 32 roster records")
    ncts = [member.get("nct") if isinstance(member, dict) else None for member in members]
    if len(set(ncts)) != 32 or any(not isinstance(nct, str) for nct in ncts):
        raise ValueError("FOCUS roster has missing or duplicate NCT identities")
    if not db_path.is_file():
        raise FileNotFoundError("Level 7 evidence database does not exist")
    with sqlite3.connect(db_path) as connection:
        present = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='level7_evidence'"
        ).fetchone()
    if not present:
        raise ValueError("Level 7 evidence table not initialized")
    result = focus_level7_coverage(EvidenceStore(db_path), members)
    result["rosterAsOf"] = snapshot.get("asOf")
    result["source"] = snapshot.get("source")
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.db)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
