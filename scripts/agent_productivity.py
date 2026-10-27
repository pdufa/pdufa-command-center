"""Agent productivity metrics from structured JSONL execution records.

Run: python scripts/agent_productivity.py logs/agent_runs.jsonl
Each line: {"run_id":"...", "started_at":"ISO8601", "ended_at":"ISO8601",
"status":"success|failed|partial", "tasks_attempted":2, "tasks_completed":1,
"tasks_verified":1, "rework_tasks":0, "quality_passed":true}
Missing fields are excluded from their metric; never assume success.
"""
import json, sys
from datetime import datetime
from collections import defaultdict

def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def measure(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[timestamp(row["started_at"]).date().isoformat()].append(row)
    result = []
    for day, runs in sorted(groups.items()):
        durations = []
        for r in runs:
            if r.get("ended_at"):
                try:
                    seconds = (timestamp(r["ended_at"]) - timestamp(r["started_at"])).total_seconds()
                    if seconds >= 0: durations.append(seconds / 3600)
                except (ValueError, TypeError): pass
        attempted = sum(max(0, int(r.get("tasks_attempted", 0))) for r in runs)
        completed = sum(max(0, int(r.get("tasks_completed", 0))) for r in runs)
        verified = sum(max(0, int(r.get("tasks_verified", 0))) for r in runs)
        rework = sum(max(0, int(r.get("rework_tasks", 0))) for r in runs)
        statuses = [r.get("status") for r in runs]
        known = [s for s in statuses if s in ("success", "failed", "partial")]
        hours = sum(durations)
        completion = completed / attempted if attempted else None
        accuracy = verified / completed if completed else None
        reliability = known.count("success") / len(known) if known else None
        minimal_rework = max(0, 1 - rework / completed) if completed else None
        # Efficiency baseline: 1 verified task/hour = 100%; adjustable after calibration.
        efficiency = min(1, verified / hours) if hours else None
        factors = [(completion, .35), (accuracy, .30), (efficiency, .15),
                   (reliability, .10), (minimal_rework, .10)]
        score = round(100 * sum(v*w for v,w in factors), 1) if all(v is not None for v,w in factors) else None
        result.append({"date":day,"runs":len(runs),"hours_logged":round(hours,2),
          "tasks_attempted":attempted,"tasks_completed":completed,"tasks_verified":verified,
          "failed_runs":known.count("failed"),"rework_tasks":rework,
          "completion_pct":round(100*completion,1) if completion is not None else None,
          "verified_tasks_per_hour":round(verified/hours,2) if hours else None,
          "productivity_score_pct":score,
          "note":"Unscored until all required inputs are available" if score is None else "Provisional calibrated score"})
    return result

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as file:
        rows = [json.loads(line) for line in file if line.strip()]
    print(json.dumps(measure(rows), indent=2))
