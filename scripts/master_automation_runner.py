#!/usr/bin/env python3
"""Opt-in GitHub/Neon controller executor. NEVER trades, merges or deploys.

Runs the two source-verified lanes first; unavailable clinical prediction and
news integrations are left explicitly NOT_WIRED instead of silently succeeding.
A failed step is checkpointed; resume only changes the failed stage and its
managed descendants. Workflow correlation is exact, never "last run won".
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "new-platform/backend"))
from app.master_automation import MANAGED, STAGES

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "pdufa/pdufa-command-center")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
BACKEND_URL = os.environ.get("PDUFA_MASTER_API_BASE_URL", "").rstrip("/")
BACKEND_KEY = os.environ.get("PDUFA_MASTER_INTERNAL_API_KEY", "")
ALLOWED_DATA = ("data/", "reports/", "new-platform/frontend/data/", "research/")


class ControllerError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def validate_repo():
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", REPO):
        raise ControllerError("INVALID_REPO")
    if not TOKEN:
        raise ControllerError("GITHUB_TOKEN_NOT_CONFIGURED")


def gh(method, path, **kwargs):
    validate_repo()
    r = requests.request(method, API + path,
                         headers={"Authorization": "Bearer " + TOKEN,
                                  "Accept": "application/vnd.github+json",
                                  "X-GitHub-Api-Version": "2022-11-28"},
                         timeout=45, **kwargs)
    if r.status_code >= 400:
        raise ControllerError("GITHUB_HTTP_" + str(r.status_code))
    if r.status_code == 204 or not r.content:
        return {}
    return r.json()


def backend(method, path, payload=None):
    if (not BACKEND_URL.startswith("https://") or not BACKEND_KEY
            or "@" in BACKEND_URL):
        raise ControllerError("BACKEND_AUTH_OR_HTTPS_NOT_CONFIGURED")
    r = requests.request(method, BACKEND_URL + "/api/master-automation" + path,
                         headers={"x-pdufa-internal-key": BACKEND_KEY,
                                  "Content-Type": "application/json"},
                         json=payload, timeout=35)
    if r.status_code >= 400:
        raise ControllerError("CONTROLLER_API_HTTP_" + str(r.status_code))
    return r.json()


def default_sha():
    data = gh("GET", f"/repos/{REPO}/git/ref/heads/main")
    sha = (data.get("object") or {}).get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ControllerError("HEAD_SHA_NOT_VERIFIED")
    return sha


def source_lineage_ok(original):
    """Allow documented generated outputs but never quietly swap executable code."""
    current = default_sha()
    if original == current:
        return
    j = gh("GET", f"/repos/{REPO}/compare/{original}...{current}")
    if j.get("status") != "ahead" or j.get("total_commits", 999) > 200:
        raise ControllerError("SOURCE_SHA_DIVERGED")
    changed = j.get("files") or []
    if not changed or len(changed) >= 300:
        raise ControllerError("SOURCE_DIFF_INCOMPLETE")
    if any(not str(x.get("filename", "")).startswith(ALLOWED_DATA) for x in changed):
        raise ControllerError("SOURCE_CODE_CHANGED_MID_RUN")


def workflow_for(stage):
    return next(x["workflow"] for x in STAGES if x["id"] == stage)


def workflow_runs(stage):
    workflow = workflow_for(stage)
    return gh("GET", f"/repos/{REPO}/actions/workflows/{workflow}/runs?per_page=100")["workflow_runs"]


def assert_not_running(stage):
    recent = workflow_runs(stage)
    if any(x.get("status") in {"queued", "in_progress", "pending", "waiting", "requested"}
           and x.get("head_branch") == "main" for x in recent):
        raise ControllerError("WORKFLOW_ALREADY_RUNNING")


def correlated_run(stage, controller_id, dispatched_after):
    expected = f"MASTER:{controller_id}:{stage}"
    for run in workflow_runs(stage):
        if (run.get("event") == "workflow_dispatch" and
                run.get("display_title") == expected and
                run.get("head_branch") == "main"):
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created >= dispatched_after - timedelta(seconds=30):
                return run
    return None


def dispatch_and_wait(stage, controller_id, timeout_seconds=10800):
    before = datetime.now(timezone.utc)
    workflow = workflow_for(stage)
    body = {"ref": "main", "inputs": {"master_run_id": controller_id}}
    if stage == "POOL":
        body["inputs"]["scan_mode"] = "DELTA"
        body["inputs"]["validate_only"] = "false"
    # A POST timeout is ambiguous: do not repeat it. First try to correlate.
    try:
        gh("POST", f"/repos/{REPO}/actions/workflows/{workflow}/dispatches", json=body)
    except Exception:
        if not correlated_run(stage, controller_id, before):
            raise ControllerError("DISPATCH_NOT_CONFIRMED") from None
    run_id = None
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        run = correlated_run(stage, controller_id, before)
        if run:
            run_id = int(run["id"])
            if run.get("status") == "completed":
                if run.get("conclusion") != "success":
                    raise ControllerError("WORKFLOW_CONCLUSION_FAILED:" + str(run_id))
                return run_id, before
        time.sleep(20)
    raise ControllerError("WORKFLOW_TIMEOUT:" + str(run_id or 0))


def _artifact_json(run_id, prefix, since):
    result = gh("GET", f"/repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")
    matches = [a for a in result.get("artifacts", []) if
               str(a.get("name", "")).startswith(prefix + str(run_id)) and
               not a.get("expired") and
               datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")) >=
               since - timedelta(seconds=30)]
    if not matches:
        raise ControllerError("MISSING_EVIDENCE_ARTIFACT")
    latest = max(matches, key=lambda a: a["created_at"])
    r = requests.get(f"{API}/repos/{REPO}/actions/artifacts/{latest['id']}/zip",
                     headers={"Authorization": "Bearer " + TOKEN,
                              "Accept": "application/vnd.github+json"},
                     timeout=60)
    if r.status_code != 200 or len(r.content) > 10_000_000:
        raise ControllerError("ARTIFACT_DOWNLOAD_FAILED")
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            names = [x for x in z.namelist() if x.endswith(".json") and not x.startswith("__MACOSX")]
            if len(names) != 1:
                raise ValueError("Artifact expected exactly one JSON report")
            return json.loads(z.read(names[0]))
    except (zipfile.BadZipFile, ValueError, KeyError, UnicodeError):
        raise ControllerError("MALFORMED_EVIDENCE_ARTIFACT") from None


def evidence(stage, run_id, dispatch_at):
    result = gh("GET", f"/repos/{REPO}/actions/runs/{run_id}")
    if result.get("conclusion") != "success" or result.get("status") != "completed":
        raise ControllerError("GITHUB_RUN_NOT_SUCCESSFUL")
    if stage == "POOL":
        # Existing overnight workflow's own 'result' job fails if any
        # required clinical/source/scoring step fails or is skipped.
        jobs = gh("GET", f"/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100")
        items = jobs.get("jobs", [])
        if not items or jobs.get("total_count", 0) > len(items):
            raise ControllerError("INCOMPLETE_JOB_EVIDENCE")
        if any(x.get("conclusion") not in {"success", "skipped"} for x in items):
            raise ControllerError("NIGHTLY_JOB_NOT_COMPLETE")
        if not any(str(x.get("name", "")).lower().endswith("result") and
                   x.get("conclusion") == "success" for x in items):
            raise ControllerError("NIGHTLY_RESULT_GATE_MISSING")
        verified = {"runId": run_id, "workflow": "POOL",
                    "jobEvidence": sorted((x["name"], x["conclusion"]) for x in items)}
    elif stage == "FOCUS":
        pool = _artifact_json(run_id, "focus-full-pool-reconciliation-", dispatch_at)
        promoted = _artifact_json(run_id, "p3-post-data-auto-promotion-", dispatch_at)
        counts = pool.get("counts") or {}
        if (pool.get("status") != "COMPLETE" or
                counts.get("POOL_RECORDS", 0) < 1 or
                counts.get("REGISTRY_QUERIED") != counts.get("CAP_ELIGIBLE") or
                counts.get("REGISTRY_RECORDS_RETURNED") != counts.get("REGISTRY_QUERIED")):
            raise ControllerError("FOCUS_POOL_COVERAGE_INCOMPLETE")
        additions = promoted.get("added")
        if (not isinstance(additions, list) or
                promoted.get("total") != promoted.get("existing", -1) + len(additions) or
                promoted.get("poolModified") is not False or
                promoted.get("historicalScoresModified") is not False):
            raise ControllerError("FOCUS_PROMOTION_NOT_VERIFIED")
        verified = {"runId": run_id, "workflow": "FOCUS",
                    "poolAsOf": pool.get("asOf"),
                    "reviewQueue": counts.get("REVIEW_QUEUE"),
                    "total": promoted["total"], "added": additions}
    else:
        raise ControllerError("STAGE_NOT_IMPLEMENTED")
    return hashlib.sha256(
        json.dumps(verified, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest(), verified


def execute(run):
    for stage in MANAGED:
        entry = next(s for s in run["stages"] if s["id"] == stage)
        if entry["status"] == "SUCCEEDED":
            print("REUSE_VERIFIED_CHECKPOINT", stage, entry["workflowRunId"], flush=True)
            continue
        if entry["status"] != "PENDING":
            raise ControllerError("STAGE_NOT_READY_" + stage)
        source_lineage_ok(run["sourceSha"])
        # Preflight before claim; an existing nightly job must never be doubled.
        assert_not_running(stage)
        worker = "github-master-" + (os.environ.get("GITHUB_RUN_ID") or "manual") + "-" + stage.lower()
        run = backend("POST", f"/runs/{run['id']}/claim",
                      {"stage": stage, "worker": worker, "version": run["version"]})
        workflow_run_id = 0
        try:
            workflow_run_id, dispatched = dispatch_and_wait(stage, run["id"])
            digest, facts = evidence(stage, workflow_run_id, dispatched)
        except ControllerError as exc:
            # Preserve an actual correlated run number when available.
            if ":" in exc.code:
                try:
                    workflow_run_id = int(exc.code.rsplit(":", 1)[1])
                except ValueError:
                    pass
            reason = exc.code.split(":", 1)[0]
            run = backend("POST", f"/runs/{run['id']}/complete",
                          {"stage": stage, "worker": worker, "version": run["version"],
                           "conclusion": "FAILED", "workflowRunId": workflow_run_id,
                           "errorCode": reason})
            print("CHECKPOINT_FAILED", stage, reason, flush=True)
            raise
        run = backend("POST", f"/runs/{run['id']}/complete",
                      {"stage": stage, "worker": worker, "version": run["version"],
                       "conclusion": "SUCCEEDED", "workflowRunId": workflow_run_id,
                       "evidenceDigest": digest})
        print("CHECKPOINT_SUCCEEDED", stage, json.dumps(facts, sort_keys=True), flush=True)
    print("MANAGED_STAGES_COMPLETE; scientific predictions/news and trading remain NOT_WIRED", flush=True)
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("plan", "run", "resume"), default="plan")
    parser.add_argument("--run-key", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--from-stage", default="")
    args = parser.parse_args()
    if args.mode == "plan":
        for s in STAGES:
            print(s["id"], s["kind"], "depends_on=" + ",".join(s["needs"]),
                  "workflow=" + str(s["workflow"]))
        print("PLAN_ONLY; no workflow dispatch, database mutation, orders, or deployment")
        return 0
    if os.getenv("PDUFA_MASTER_ALLOW_EXECUTION") != "1":
        raise ControllerError("EXECUTION_OPT_IN_DISABLED")
    if args.mode == "run":
        if not args.run_key:
            raise ControllerError("RUN_KEY_REQUIRED")
        run = backend("POST", "/runs", {"runKey": args.run_key, "sourceSha": default_sha()})
    else:
        if not args.run_id or args.from_stage not in MANAGED:
            raise ControllerError("EXPLICIT_FAILED_STAGE_AND_RUN_ID_REQUIRED")
        previous = backend("GET", "/runs/" + args.run_id)
        run = backend("POST", f"/runs/{args.run_id}/resume",
                      {"version": previous["version"], "stage": args.from_stage})
    print("CONTROLLER_RUN", run["id"], "generation", run["generation"], flush=True)
    execute(run)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ControllerError as exc:
        print("MASTER_CONTROLLER_BLOCKED", exc.code, flush=True)
        sys.exit(1)
    except requests.RequestException:
        print("MASTER_CONTROLLER_BLOCKED", "NETWORK_FAILURE", flush=True)
        sys.exit(1)
