"""Rebuild the PRE PHASE 3 research display from saved, dated source evidence.

This refresh is a display materialization, NOT a source collection or
verification of stale SEC, clinical, financing or market inputs.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from step7_cached_snapshot import load_current_snapshot
from step7_live import build_snapshot, write_csv


def main():
    root = Path("data")
    now = datetime.now(timezone.utc)
    trials, financing, status = build_snapshot(root, now)
    if not trials or not isinstance(status.get("source_checks"), list):
        raise SystemExit("BLOCKED: no validated clinical trials or source health; old files retained")
    if len(trials) != status.get("trial_rows") or len(financing) != status.get("financing_events"):
        raise SystemExit("BLOCKED: count mismatch; old files retained")
    with tempfile.TemporaryDirectory(prefix="step7-stage-") as temp_dir:
        staged = Path(temp_dir)
        write_csv(staged / "step7_pre_phase3_feed.csv", trials)
        write_csv(staged / "step7_financing_review.csv", financing)
        (staged / "step7_live_status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8")
        # This uses exactly the reader the dashboard uses, before publishing.
        snapshot = load_current_snapshot(staged, now)
        if snapshot is None or len(snapshot[0]) != len(trials):
            raise SystemExit("BLOCKED: Step 7 reader rejected new snapshot; old files retained")
        for name in ("step7_pre_phase3_feed.csv",
                     "step7_financing_review.csv", "step7_live_status.json"):
            os.replace(staged / name, root / name)
    print(json.dumps({
        "generated_at_utc": status["generated_at_utc"],
        "trial_rows": len(trials),
        "finance_events": len(financing),
        "source_health": [{"source": x.get("Source"), "health": x.get("Health")}
                          for x in status["source_checks"]],
        "claim": "DATED DISPLAY CACHE ONLY; SOURCE HEALTH NOT REVALIDATED",
    }, indent=2))


if __name__ == "__main__":
    main()
