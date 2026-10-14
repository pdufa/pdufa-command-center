#!/usr/bin/env python3
"""Export prior SEC Step 4 cash/operating-flow snapshots as GEM research inputs.

Not a new SEC scan. First refresh issuer snapshots with sec_step4.py using
a valid SEC_USER_AGENT. The GEM scanner independently enforces freshness,
post-financing chronology, >=12 months of cash runway and all other gates.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from sec_step4 import read_history


def export(root):
    root = Path(root)
    db = root / "sec_step4_snapshots.sqlite3"
    if not db.is_file():
        raise FileNotFoundError("SEC Step 4 source database is unavailable; refresh cash/burn facts first")
    latest = {}
    for item in read_history(db_path=db):
        snap = json.loads(item["payload_json"])
        ticker = str(snap.get("ticker") or "").strip().upper()
        if ticker and ticker not in latest:
            latest[ticker] = snap
    payload = {"schema_version": 1, "source": "SEC_STEP4_COMPANYFACTS",
               "snapshots": [latest[t] for t in sorted(latest)]}
    target = root / "gem_runway_evidence.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    return len(latest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(json.dumps({"saved_SEC_cash_snapshots": export(args.data_dir),
                      "entry_authorized": False}))
