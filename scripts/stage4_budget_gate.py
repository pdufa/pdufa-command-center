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
    if len(tasks) > 100:
        raise ValueError("Development queue exceeds 100 tasks")
    seen_ids = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"Task {index} must be an object")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError(f"Task {index} must have a nonempty string id")
        if len(task_id) > 128 or not all(c.isascii() and (c.isalnum() or c in "-_") for c in task_id):
            raise ValueError(f"Task {index} id must use ASCII letters, digits, dash or underscore")
        if task_id in seen_ids:
            raise ValueError(f"Duplicate task id: {task_id}")
        seen_ids.add(task_id)
        if "approved" in task and not isinstance(task["approved"], bool):
            raise ValueError(f"Task {index} approval must be a boolean")
    approved = [t for t in tasks if t.get("approved") is True]
    return {"status": "awaiting_executor_and_billing_guard", "approved_tasks": len(approved)}


def main():
    budget = validate_budget(os.getenv("AI_MONTHLY_BUDGET_USD", "0"))
    result = inspect_queue(Path("research/focus/approved-development-tasks.json"))
    print(json.dumps({**result, "budget_usd": budget, "ai_calls": 0}))


if __name__ == "__main__":
    main()
