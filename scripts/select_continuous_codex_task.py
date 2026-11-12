#!/usr/bin/env python3
"""Select one explicitly source-controlled Codex task, never invent work."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".github/codex/continuous-development-queue.json"
SLUG = re.compile(r"[a-z][a-z0-9-]{4,45}")
REPO = "pdufa/pdufa-command-center"
API = "https://api.github.com/repos/" + REPO


def eligible(task):
    if not isinstance(task, dict) or task.get("status") != "approved_for_draft_pr":
        return False
    slug = task.get("id")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        return False
    if task.get("branch") != "autodev/" + slug:
        return False
    if task.get("promptFile") != ".github/codex/tasks/" + slug + ".md":
        return False
    path = ROOT / task["promptFile"]
    return path.is_file() and not path.is_symlink()


def existing_pr(token, branch):
    params = urllib.parse.urlencode({"head": "pdufa:" + branch, "state": "all", "per_page": 100})
    req = urllib.request.Request(API + "/pulls?" + params, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PDUFA-Codex-Queue",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise ValueError("GitHub pull list shape unavailable")
    return len(rows) > 0


def branch_reserved(token, branch):
    url = API + "/git/ref/heads/" + urllib.parse.quote(branch, safe="/")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def reserve_once(token, branch):
    """Reserving an approved branch prevents repeated billed attempts on failure."""
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Trusted GitHub source SHA missing")
    body = json.dumps({"ref": "refs/heads/" + branch, "sha": sha}).encode()
    req = urllib.request.Request(API + "/git/refs", data=body, method="POST", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 201:
            raise RuntimeError("GitHub branch reservation not confirmed")


def main():
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or not isinstance(data.get("tasks"), list):
        raise SystemExit("Invalid approved Codex queue")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GitHub read token missing")
    output = {"task_id": "", "prompt_file": "", "branch": ""}
    for task in data["tasks"]:
        if not eligible(task):
            continue
        if existing_pr(token, task["branch"]) or branch_reserved(token, task["branch"]):
            continue
        # Reserve before invoking the paid agent. A failed/no-patch attempt is
        # never automatically retried on the next scheduled tick.
        reserve_once(token, task["branch"])
        output = {"task_id": task["id"], "prompt_file": task["promptFile"], "branch": task["branch"]}
        break
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        raise SystemExit("GitHub output file missing")
    with open(output_file, "a", encoding="utf-8") as f:
        for key, value in output.items():
            f.write(key + "=" + value + "\n")
    print("Approved task selected: " + (output["task_id"] or "none / all already attempted"))


if __name__ == "__main__":
    main()
