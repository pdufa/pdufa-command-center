#!/usr/bin/env python3
"""Fail-closed preflight for a future authorized coding executor.

No model calls, code writes, or billing authorization occur here.
"""
import json
import math
import os
from pathlib import Path


def validate_budget(raw):
    try:
        value = float(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid AI budget") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("AI budget must be finite and nonnegative")
    return value


def inspect_queue(path):
    if not path.exists():
        return {"status": "idle", "reason": "no_approved_task_queue", "approved_tasks": 0}
    tasks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("Task queue must be a list")
    approved = [t for t in tasks if isinstance(t, dict) and t.get("approved") is True]
    return {"status": "awaiting_executor_and_billing_guard", "approved_tasks": len(approved)}


def main():
    budget = validate_budget(os.getenv("AI_MONTHLY_BUDGET_USD", "0"))
    result = inspect_queue(Path("research/focus/approved-development-tasks.json"))
    print(json.dumps({**result, "budget_usd": budget, "ai_calls": 0}))


if __name__ == "__main__":
    main()
