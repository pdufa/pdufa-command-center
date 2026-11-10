#!/usr/bin/env python3
"""Fail-closed preflight for a future authorized coding executor.

This script does NOT call a model, modify code, or authorize spending.
"""
import json
import os
from pathlib import Path

def main():
    budget = float(os.getenv("AI_MONTHLY_BUDGET_USD", "0"))
    queue = Path("research/focus/approved-development-tasks.json")
    if not queue.exists():
        print(json.dumps({"status":"idle","reason":"no_approved_task_queue","budget_usd":budget,"ai_calls":0}))
        return
    tasks = json.loads(queue.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("Task queue must be a list")
    approved = [t for t in tasks if isinstance(t, dict) and t.get("approved") is True]
    print(json.dumps({"status":"awaiting_executor_and_billing_guard","approved_tasks":len(approved),"budget_usd":budget,"ai_calls":0}))

if __name__ == "__main__":
    main()
