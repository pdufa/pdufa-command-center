#!/usr/bin/env python3
"""Read-only heartbeat loop; no GitHub writes or scientific adjudication."""
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
running = True

def stop(*_):
    global running
    running = False

def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    interval = max(1.0, float(os.environ.get("PDUFA_POLL_SECONDS", "1")))
    while running:
        started = time.monotonic()
        if not ROSTER.is_file():
            print(json.dumps({"status": "blocked", "reason": "missing_roster"}), flush=True)
        else:
            try:
                roster = json.loads(ROSTER.read_text(encoding="utf-8"))
                if not isinstance(roster, (list, dict)):
                    raise ValueError("invalid roster type")
                print(json.dumps({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                  "worker": "stage4-second-heartbeat",
                                  "status": "healthy", "mode": "read_only",
                                  "roster_present": True}), flush=True)
            except (ValueError, OSError) as exc:
                print(json.dumps({"status": "blocked", "reason": type(exc).__name__}), flush=True)
        remaining = interval - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

if __name__ == "__main__":
    main()
