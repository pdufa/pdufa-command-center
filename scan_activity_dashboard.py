"""Top-level read-only 24-hour GitHub scan activity viewer.

GitHub Actions run status is execution status, NOT trade/evidence readiness.
The PDUFA SCANS subtab remains the published audit and scan-control surface.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

REPO = "pdufa/pdufa-command-center"
ACTIONS_URL = "https://github.com/" + REPO + "/actions"
API = "https://api.github.com/repos/" + REPO
PACIFIC = ZoneInfo("America/Los_Angeles")
SOURCE_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/pdufa_source_report.json"
GEM_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/gem_scan_block_report.json"

# Explicit, bounded list avoids auto-repair/CI spam obscuring actual scans.
# GitHub API returns up to 50 recent runs PER workflow, not all repository runs.
WORKFLOWS = (
    ("Clinical scans", "pdufa-nightly-clinical.yml"),
    ("GEMS quality snapshot", "gem-research-quality.yml"),
    ("GEMS financing research", "gem-financing-full-coverage.yml"),
    ("GEMS potential audit", "gem-potential-live-audit.yml"),
    ("FDA / SEC / financial / market / issuer", "pdufa-nightly-missing-sources.yml"),
    ("Source evidence recheck", "pdufa-reverify-45-primary-20261014.yml"),
    ("FDA primary proof", "pdufa-run-four-primary-fda-20261014.yml"),
    ("Clinical report publisher", "pdufa-nightly-report.yml"),
    ("Scoring / error / repair", "pdufa-nightly-scoring-then-repair.yml"),
    ("Nightly report checks", "pdufa-nightly-report-checks.yml"),
    ("Morning 6 AM results", "pdufa-morning-6am-results.yml"),
    ("Scan control", "pdufa-scan-control.yml"),
    ("Overnight scan start", "pdufa-nightly-pacific-start.yml"),
    ("Manual clinical scan", "pdufa-one-time-clinical-scan.yml"),
)

def _github_token():
    # Never put a credential in client-side links, tables or error messages.
    try:
        return str(st.secrets.get("PDUFA_GITHUB_TOKEN", "") or
                   st.secrets.get("GITHUB_TOKEN", "") or "").strip()
    except (OSError, KeyError, TypeError):
        return ""


def _get_json(url: str, token: str = "", timeout: int = 5) -> dict:
    headers = {
        "User-Agent": "pdufa-command-center-scans",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("GitHub returned a non-object response")
    return result


def _timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.astimezone(timezone.utc) if date.tzinfo else None
    except ValueError:
        return None


def _run_url(run_id):
    if type(run_id) is not int or run_id <= 0:
        return ""
    return ACTIONS_URL + "/runs/" + str(run_id)


def _job_url(run_id, job_id):
    if not _run_url(run_id) or type(job_id) is not int or job_id <= 0:
        return ""
    return _run_url(run_id) + "/job/" + str(job_id)


def _state(run):
    status = str(run.get("status") or "").lower()
    conclusion = str(run.get("conclusion") or "").lower()
    if status == "completed":
        return {
            "success": "Completed",
            "failure": "Failed",
            "cancelled": "Cancelled",
            "timed_out": "Failed",
            "action_required": "Needs action",
            "skipped": "Skipped",
            "neutral": "Completed",
        }.get(conclusion, "Completed — result unknown")
    if status == "in_progress":
        return "Running"
    if status in ("queued", "pending", "requested", "waiting"):
        return "Queued"
    return "Unknown"


def _format_pacific(utc_dt):
    return utc_dt.astimezone(PACIFIC).strftime("%b %d, %I:%M %p %Z") if utc_dt else "Unknown"


def _rows_for_window(runs, now, hours):
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=hours)
    seen = set()
    result = []
    for run in runs:
        run_id = run.get("id")
        stamp = _timestamp(run.get("created_at"))
        if not _run_url(run_id) or not stamp or stamp < cutoff or run_id in seen:
            continue
        seen.add(run_id)
        result.append({
            "id": run_id,
            "workflow": str(run.get("_label") or run.get("name") or "Scan"),
            "name": str(run.get("name") or "Scan"),
            "status": _state(run),
            "started": _format_pacific(stamp),
            "created_utc": stamp,
            "url": _run_url(run_id),
        })
    return sorted(result, key=lambda x: x["created_utc"], reverse=True)


@st.cache_data(ttl=75, show_spinner=False)
def _fetch_runs(_token: str, days: int):
    """Retrieve bounded recent runs per known workflow; report partial errors.

    A failed API request is never interpreted as zero runs. The API call
    count is deliberately bounded; historical completeness is NOT claimed.
    """
    results = []
    errors = []
    # A 7-day view still uses at most 50 runs from each workflow.
    for label, workflow in WORKFLOWS:
        path = urllib.parse.quote(workflow, safe="")
        url = API + "/actions/workflows/" + path + "/runs?per_page=50"
        try:
            response = _get_json(url, _token)
            rows = response.get("workflow_runs")
            if not isinstance(rows, list):
                raise ValueError("Missing workflow_runs list")
            for raw in rows:
                if isinstance(raw, dict):
                    results.append({**raw, "_label": label})
        except (OSError, ValueError, urllib.error.URLError) as exc:
            # Error classes only. Never leak request headers or access tokens.
            errors.append(label + " (" + type(exc).__name__ + ")")
    return results, errors, datetime.now(timezone.utc).isoformat()


@st.cache_data(ttl=45, show_spinner=False)
def _fetch_jobs(run_id: int, _token: str):
    if not _run_url(run_id):
        return [], "Invalid run ID"
    try:
        data = _get_json(API + "/actions/runs/" + str(run_id) + "/jobs?per_page=100", _token)
        jobs = data.get("jobs")
        if not isinstance(jobs, list):
            raise ValueError("Missing jobs list")
        return jobs, ""
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return [], "Job detail unavailable (" + type(exc).__name__ + ")"


@st.cache_data(ttl=75, show_spinner=False)
def _published_report(url, fallback):
    try:
        return _get_json(url, timeout=5), "Published GitHub report"
    except (OSError, ValueError, urllib.error.URLError):
        try:
            data = json.loads(Path(fallback).read_text(encoding="utf-8"))
            return (data, "Bundled repository snapshot — may be stale") if isinstance(data, dict) else ({}, "Unavailable")
        except (OSError, ValueError):
            return {}, "Unavailable"


def render_scans_activity():
    st.markdown("## SCANS — LIVE ACTIVITY & HISTORY")
    st.caption(
        "Read-only GitHub Actions status for scans that are running, queued, "
        "completed or failed. Times are Pacific. Job success does NOT certify "
        "FDA/SEC evidence, GEMS eligibility or permission to trade."
    )
    left, middle, right = st.columns([2, 2, 3])
    with left:
        span = st.selectbox("Time window", ["Last 24 hours", "Last 7 days"],
                            key="top_scans_window")
    with middle:
        state_filter = st.selectbox(
            "Show", ["All scans", "Running / queued", "Completed", "Failed / cancelled"],
            key="top_scans_filter")
    with right:
        st.write("")
        if st.button("↻ Refresh scan activity", use_container_width=True,
                     key="top_scans_refresh"):
            _fetch_runs.clear()
            _fetch_jobs.clear()
            _published_report.clear()
            st.rerun()

    hours = 24 if span == "Last 24 hours" else 168
    all_runs, errors, fetched = _fetch_runs(_github_token(), 1 if hours == 24 else 7)
    now = datetime.now(timezone.utc)
    all_rows = _rows_for_window(all_runs, now, hours)
    running = sum(x["status"] == "Running" for x in all_rows)
    queued = sum(x["status"] == "Queued" for x in all_rows)
    complete = sum(x["status"] == "Completed" for x in all_rows)
    problem = sum(x["status"] in ("Failed", "Cancelled", "Needs action") for x in all_rows)
    counts = st.columns(4)
    for panel, (label, value) in zip(
        counts, (("RUNNING", running), ("QUEUED", queued),
                 ("COMPLETED", complete), ("FAILED / CANCELLED", problem))):
        panel.metric(label, value)
    fetched_dt = _timestamp(fetched)
    st.caption(
        "Last checked: " + _format_pacific(fetched_dt) +
        " · Up to 50 newest runs per tracked workflow · "
        "Automatic retry noise and general CI excluded. "
        "Use GitHub Actions for the full history."
    )

    if errors:
        st.warning(
            "Some live run histories could not be loaded: " +
            ", ".join(errors[:6]) +
            (f" (and {len(errors) - 6} more)" if len(errors) > 6 else "") +
            ". Counts below are incomplete; open GitHub for full status."
        )

    if state_filter == "Running / queued":
        visible = [x for x in all_rows if x["status"] in ("Running", "Queued")]
    elif state_filter == "Completed":
        visible = [x for x in all_rows if x["status"] == "Completed"]
    elif state_filter == "Failed / cancelled":
        visible = [x for x in all_rows
                   if x["status"] in ("Failed", "Cancelled", "Needs action")]
    else:
        visible = all_rows

    if visible:
        frame = pd.DataFrame([
            {"Started (Pacific)": r["started"], "Scan": r["workflow"],
             "Execution": r["status"], "Open GitHub log": r["url"]}
            for r in visible
        ])
        st.dataframe(
            frame, hide_index=True, use_container_width=True,
            column_config={
                "Open GitHub log": st.column_config.LinkColumn(
                    "Job log", display_text="Open run ↗"),
            },
            height=min(690, 46 + 37 * len(frame)),
        )
        options = {f"{row['started']}  ·  {row['workflow']}  ·  {row['status']}  ·  #{row['id']}": row
                   for row in visible}
        selected = st.selectbox(
            "Inspect a run's jobs and current step", list(options),
            key="top_scans_selected_run")
        item = options[selected]
        st.link_button("Open all logs and downloadable artifacts for this run ↗",
                       item["url"])
        jobs, job_error = _fetch_jobs(item["id"], _github_token())
        if job_error:
            st.info(job_error + ". Use the GitHub run link above.")
        elif jobs:
            job_rows = []
            for j in jobs:
                step = next((v.get("name", "") for v in (j.get("steps") or [])
                             if v.get("status") == "in_progress"), "")
                job_rows.append({
                    "Job": str(j.get("name") or ""),
                    "Status": _state(j),
                    "Current step": str(step),
                    "Log": _job_url(item["id"], j.get("id")),
                })
            st.dataframe(
                pd.DataFrame(job_rows), hide_index=True,
                use_container_width=True,
                column_config={"Log": st.column_config.LinkColumn(
                    "Open job log", display_text="Open ↗")},
            )
        else:
            st.info("No GitHub job records have been published for this run yet.")
    elif errors:
        st.warning("No scan runs available from the currently accessible workflows.")
    else:
        st.info("No tracked scans match this window and filter.")

    st.markdown("### Published verification & GEMS reports")
    source, source_origin = _published_report(SOURCE_URL, "data/pdufa_source_report.json")
    gem, gem_origin = _published_report(GEM_URL, "data/gem_scan_block_report.json")
    c1, c2, c3 = st.columns(3)
    c1.metric("Required evidence gaps", source.get("required_findings_unresolved")
              if type(source.get("required_findings_unresolved")) is int else "Unknown")
    c2.metric("Verification", str(source.get("status") or "Unknown"))
    c3.metric("GEMS qualified entries",
              gem.get("strict_entry_gate_shortlist_count")
              if type(gem.get("strict_entry_gate_shortlist_count")) is int else "Unknown")
    st.caption(
        "Verification: " + str(source.get("updated_at_utc") or "Not published") +
        " (" + source_origin + ") · GEMS: " +
        str(gem.get("generated_at_utc") or "Not published") +
        " (" + gem_origin + "). These reports may predate active jobs."
    )
    links = st.columns(3)
    with links[0]:
        st.link_button("Source verification report", "https://github.com/" + REPO +
                       "/blob/main/data/pdufa_source_report.json", use_container_width=True)
    with links[1]:
        st.link_button("GEMS research report", "https://github.com/" + REPO +
                       "/blob/main/data/gem_scan_block_report.json", use_container_width=True)
    with links[2]:
        st.link_button("All GitHub Actions", ACTIONS_URL, use_container_width=True)
    st.caption(
        "For source exception queues, historical clinical changes and secured "
        "rescan controls, open PDUFA → SCANS. This activity page cannot place orders "
        "or change scan configuration."
    )
