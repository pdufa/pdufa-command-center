#!/usr/bin/env python3
"""Generate Step 7 display snapshots from saved upstream scanner outputs."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from step7_live import build_snapshot, write_csv


def main():
    data = ROOT / "data"
    trials, financing, state = build_snapshot(data, datetime.now(timezone.utc))
    write_csv(data / "step7_pre_phase3_feed.csv", trials)
    write_csv(data / "step7_financing_review.csv", financing)
    (data / "step7_live_status.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "trials": len(trials), "financing_events": len(financing),
        "health": {r["Source"]: r["Health"] for r in state["source_checks"]},
        "entry_ready_count": 0,
    }, indent=2))
    if not trials:
        print("No clinical trial records to display: check upstream intake.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
