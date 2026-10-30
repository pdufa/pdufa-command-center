"""Authenticated, read-only staging SSE smoke test. Requires env key; prints no secrets."""
import json
import os
import re
import sys
import urllib.error
import urllib.request

def main():
    base = os.environ.get("PDUFA_API_BASE_URL", "").rstrip("/")
    key = os.environ.get("PDUFA_INTERNAL_API_KEY", "")
    nct = os.environ.get("PDUFA_TEST_NCT", "")
    if not base.startswith("https://") or not key or not re.fullmatch(r"NCT[0-9]{8}", nct):
        print("Set PDUFA_API_BASE_URL (https), PDUFA_INTERNAL_API_KEY, PDUFA_TEST_NCT (saved NCT)", file=sys.stderr)
        return 2
    request = urllib.request.Request(
        f"{base}/api/prediction-events/{nct}",
        headers={"X-Pdufa-Internal-Key": key, "Accept": "text/event-stream"},
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            if response.status != 200 or "text/event-stream" not in response.headers.get("Content-Type", ""):
                raise RuntimeError("Unexpected HTTP response or content type")
            body = response.read(1_000_000).decode("utf-8")
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"Smoke test failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    frames = [part for part in body.split("\n\n") if part.strip()]
    events = []
    for frame in frames:
        lines = frame.splitlines()
        if len(lines) != 2 or not lines[0].startswith("event: ") or not lines[1].startswith("data: "):
            print("Malformed SSE frame", file=sys.stderr)
            return 1
        payload = json.loads(lines[1][6:])
        if payload.get("type") != lines[0][7:] or payload.get("nct_id") != nct:
            print("Event type or NCT identity mismatch", file=sys.stderr)
            return 1
        events.append(payload)
    checks = [
        len(events) == 63,
        events[0].get("type") == "started",
        events[0].get("mode") == "SAVED_EVIDENCE_REPLAY",
        events[0].get("research_running") is False,
        len([e for e in events if e["type"] == "assessment"]) == 40,
        all(e.get("status") == "NOT_ASSESSED" for e in events if e["type"] == "assessment"),
        events[-1].get("type") == "complete",
        events[-1].get("decision") == "ABSTAIN",
    ]
    if not all(checks):
        print("SSE invariant failure", file=sys.stderr)
        return 1
    print(f"PASS: {nct}, {len(events)} SSE events, 40 unassessed, ABSTAIN")
    return 0

if __name__ == "__main__":
    sys.exit(main())
