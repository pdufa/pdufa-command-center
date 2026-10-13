"""Read-only GitHub run health and mandatory evidence monitoring for SCANS.

GitHub Actions completion and clinical/FDA/source *verification* are distinct.
The UI never dispatches jobs or invents missing source evidence.
"""
from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

REPO = "pdufa/pdufa-command-center"
BASE = "https://github.com/" + REPO
API = "https://api.github.com/repos/" + REPO
RAW = "https://raw.githubusercontent.com/" + REPO + "/main/data/"
WORKFLOWS = {
    "Clinical #2 → #3 → #4": "pdufa-nightly-clinical.yml",
    "Clinical report publisher": "pdufa-nightly-report.yml",
    "FDA / SEC / Financial / Market / Issuer": "pdufa-nightly-missing-sources.yml",
    "Scoring → Error check → Repair": "pdufa-nightly-scoring-then-repair.yml",
    "Code validation": "ci.yml",
    "Streamlit tests": "streamlit-validation.yml",
    "Source verification tests": "pdufa-extended-source-tests.yml",
    "Gmail + GitHub ad hoc audit": "pdufa-adhoc-error-check.yml",
}
ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}
FAMILIES = ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER")
QUEUE_COLUMNS = ("ticker", "category", "claim", "verification_status", "reason", "source_url")


def verification_numbers(report):
    """A verified or not-applicable check is resolved; execution is separate."""
    try:
        total = max(0, int(report["required_findings_due"]))
        remaining = max(0, min(total, int(report["required_findings_unresolved"])))
    except (KeyError, TypeError, ValueError):
        return None
    if total == 0:
        return None
    resolved = total - remaining
    return {"total": total, "remaining": remaining, "resolved": resolved,
            "percent": round(resolved * 100.0 / total, 1)}


def run_state(run):
    """A successful GitHub workflow never implies source evidence is verified."""
    state = str(run.get("status") or "").lower()
    result = str(run.get("conclusion") or "").lower()
    if state in ACTIVE:
        return "RUNNING" if state == "in_progress" else "QUEUED"
    if state == "completed":
        return {"success": "FINISHED · success",
                "failure": "FAILED", "timed_out": "TIMED OUT",
                "cancelled": "CANCELLED", "skipped": "SKIPPED",
                "neutral": "FINISHED · neutral"}.get(result, "FINISHED · " + (result or "unknown"))
    return "UNKNOWN"


def workflow_snapshots(runs):
    """Latest known workflow for each stage, ignoring unrelated repair spam."""
    found = {}
    for run in sorted(runs, key=lambda x: x.get("created_at") or "", reverse=True):
        path = str(run.get("path") or "").split("/")[-1]
        if path and path not in found and path in WORKFLOWS.values():
            found[path] = run
    return found


def pacific_time(timestamp):
    if not timestamp:
        return "—"
    try:
        moment = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            return "—"
        return moment.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%b %d, %I:%M %p %Z")
    except (ValueError, TypeError):
        return "—"


def run_link(run):
    url = run.get("html_url")
    if isinstance(url, str) and re.fullmatch(re.escape(BASE) + r"/actions/runs/\d+", url):
        return url
    return ""


def _json_get(url, *, timeout=10):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "pdufa-command-center-scans-status"}
    try:
        token = str(st.secrets.get("PDUFA_GITHUB_TOKEN", "") or "").strip()
    except (OSError, KeyError, AttributeError):
        token = ""
    if token and url.startswith(API + "/"):
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


@st.cache_data(ttl=105, show_spinner=False)
def recent_github_runs():
    """One paginated request, cached; errors must not masquerade as 'no runs'."""
    try:
        payload = _json_get(API + "/actions/runs?per_page=100")
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list):
            raise ValueError("Missing GitHub workflow run list")
        return runs, ""
    except (OSError, ValueError, urllib.error.URLError, TypeError) as exc:
        return [], "GitHub live status unavailable (" + type(exc).__name__ + ")"


@st.cache_data(ttl=105, show_spinner=False)
def current_job_steps(run_id):
    """Fetch jobs only for the active source chain, never for every workflow."""
    if not isinstance(run_id, int) or run_id <= 0:
        return []
    try:
        payload = _json_get(API + "/actions/runs/" + str(run_id) + "/jobs?per_page=100")
        return payload.get("jobs", []) if isinstance(payload.get("jobs"), list) else []
    except (OSError, ValueError, urllib.error.URLError, TypeError):
        return []


@st.cache_data(ttl=105, show_spinner=False)
def required_issue_queue():
    request = urllib.request.Request(
        RAW + "pdufa_source_review_queue.csv",
        headers={"User-Agent": "pdufa-command-center-scans-status",
                 "Accept": "text/csv"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(1_000_001)
        result = pd.read_csv(io.BytesIO(raw), dtype=str).fillna("")
        if not set(QUEUE_COLUMNS).issubset(result.columns):
            raise ValueError("Unexpected review queue schema")
        return result, ""
    except (OSError, ValueError, pd.errors.ParserError):
        try:
            result = pd.read_csv(Path("data/pdufa_source_review_queue.csv"), dtype=str).fillna("")
            if set(QUEUE_COLUMNS).issubset(result.columns):
                return result, "Showing local review queue; latest GitHub copy is unavailable."
        except (OSError, ValueError, pd.errors.ParserError):
            pass
        return pd.DataFrame(columns=QUEUE_COLUMNS), "Full review queue unavailable."


def _refresh(published_report_loader):
    recent_github_runs.clear()
    current_job_steps.clear()
    required_issue_queue.clear()
    published_report_loader.clear()


@st.fragment(run_every="120s")
def render_scan_status(published_report_loader):
    """Live run metadata updates independently inside the existing SCANS tab."""
    st.markdown("## SCAN STATUS & ISSUES")
    st.caption("Live GitHub workflow status + last **published** evidence audit. Refreshes about every two minutes while SCANS is open. All times Pacific.")
    st.button("↻ Refresh scan status", key="pdufa_refresh_live_runs",
              on_click=_refresh, args=(published_report_loader,))

    report = published_report_loader()
    runs, error = recent_github_runs()
    latest = workflow_snapshots(runs)
    sources = latest.get(WORKFLOWS["FDA / SEC / Financial / Market / Issuer"], {})
    validation = latest.get(WORKFLOWS["Code validation"], {})
    clinical = latest.get(WORKFLOWS["Clinical #2 → #3 → #4"], {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Extended source scan", run_state(sources) if sources else "NOT AVAILABLE")
    c2.metric("Code validation", run_state(validation) if validation else "NOT AVAILABLE")
    c3.metric("Clinical scans", run_state(clinical) if clinical else "NOT AVAILABLE")

    links = st.columns(3)
    with links[0]:
        st.link_button("OPEN SOURCE SCAN", run_link(sources) or
                       BASE + "/actions/workflows/pdufa-nightly-missing-sources.yml",
                       use_container_width=True)
    with links[1]:
        st.link_button("OPEN CODE VALIDATION", run_link(validation) or
                       BASE + "/actions/workflows/ci.yml", use_container_width=True)
    with links[2]:
        st.link_button("ALL GITHUB ACTIONS", BASE + "/actions", use_container_width=True)

    if error:
        st.warning(error + ". The saved audit below may still be available.")
    else:
        active = [(label, latest.get(path, {})) for label, path in WORKFLOWS.items()
                  if latest.get(path, {}).get("status") in ACTIVE]
        if active:
            st.info("Currently active: " + ", ".join(label + " (" + run_state(run) + ")"
                                                    for label, run in active))
        else:
            st.caption("No active runs appear among the 100 latest GitHub Actions results; open Actions to inspect any older active run.")

        if sources.get("status") in ACTIVE:
            jobs = current_job_steps(sources.get("id"))
            running_jobs = [str(job.get("name")) for job in jobs
                            if job.get("status") == "in_progress"]
            if running_jobs:
                st.write("**Current source stage:** " + " · ".join(running_jobs[:3]))
            elif sources.get("status") in {"queued", "waiting", "pending"}:
                st.write("**Current source stage:** Waiting for GitHub to start")
        failures = [(label, last) for label, path in WORKFLOWS.items()
                    if (last := latest.get(path, {})).get("status") == "completed"
                    and last.get("conclusion") in {"failure", "timed_out"}]
        for label, last in failures:
            st.error(label + ": " + run_state(last) +
                     ". Open the linked workflow run to inspect the failing step.")

    st.markdown("### Latest workflow results")
    table = []
    for label, path in WORKFLOWS.items():
        run = latest.get(path)
        if run:
            table.append({"Scan / check": label, "Run status": run_state(run),
                          "Trigger": run.get("event", "unknown"),
                          "Started (Pacific)": pacific_time(run.get("run_started_at") or run.get("created_at")),
                          "Run ID": str(run.get("id", "")),
                          "GitHub run": run_link(run)})
        else:
            table.append({"Scan / check": label, "Run status": "NOT IN RECENT RESULTS",
                          "Trigger": "—", "Started (Pacific)": "—",
                          "Run ID": "—", "GitHub run": ""})
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True,
                 column_config={"GitHub run": st.column_config.LinkColumn(
                     "GitHub run", display_text="Open run")})
    st.caption("GitHub 'success' means the workflow executed; it does **not** mean FDA/SEC evidence passed. "
               "Only the latest run for each listed workflow is shown above, including manual or test runs.")

    # Keep recent history visible without conflating a prior successful run
    # with a currently active new run. Older runs may be beyond the API page.
    history_paths = {
        WORKFLOWS["Clinical #2 → #3 → #4"],
        WORKFLOWS["FDA / SEC / Financial / Market / Issuer"],
        WORKFLOWS["Scoring → Error check → Repair"],
    }
    history = [r for r in sorted(runs, key=lambda x: x.get("created_at") or "", reverse=True)
               if str(r.get("path") or "").split("/")[-1] in history_paths][:12]
    if history:
        with st.expander("RECENT SCAN RUNS — last 12 visible"):
            past = [{"Workflow": str(r.get("name") or "Unknown"),
                     "Status": run_state(r),
                     "Started (Pacific)": pacific_time(r.get("run_started_at") or r.get("created_at")),
                     "Trigger": r.get("event") or "—",
                     "Run ID": str(r.get("id") or ""),
                     "GitHub run": run_link(r)} for r in history]
            st.dataframe(pd.DataFrame(past), hide_index=True, use_container_width=True,
                         column_config={"GitHub run": st.column_config.LinkColumn(
                             "GitHub run", display_text="Open run")})

    if not report:
        st.warning("No published source verification report is available. Execution status above is not proof of evidence coverage.")
        return

    st.markdown("### Mandatory evidence verification")
    numbers = verification_numbers(report)
    if numbers:
        a, b, c = st.columns(3)
        a.metric("Checks resolved", f"{numbers['resolved']:,} / {numbers['total']:,}")
        b.metric("Checks unresolved", f"{numbers['remaining']:,}")
        c.metric("Evidence coverage", f"{numbers['percent']:.1f}%")
        st.progress(numbers["resolved"] / numbers["total"])
    st.caption("**Last published audit:** " + pacific_time(report.get("source_checked_at_utc")) +
               " · run #" + str(report.get("latest_run_id") or "unknown") +
               " · coverage: " + str(report.get("status", "UNVERIFIED")) +
               ". Unresolved items include missing evidence and conflicting claims, not unfinished compute jobs.")

    comparison = report.get("comparison") or {}
    if comparison.get("available"):
        st.markdown("#### Change from previous published scan")
        x, y, z = st.columns(3)
        x.metric("Issues resolved", int(comparison.get("resolved_count", 0)))
        y.metric("New unresolved", int(comparison.get("new_count", 0)))
        z.metric("Net fewer unresolved", int(comparison.get("net_reduction", 0)))
        st.caption("Compared with run #" + str(comparison.get("previous_run_id") or "unknown") +
                   ". Changes are matched by event, source and claim; a lower total alone is not evidence of a fix.")
        if comparison.get("new_count"):
            st.warning("New verification gaps were detected; inspect the affected candidates below.")
        if comparison.get("resolved_examples") or comparison.get("new_examples"):
            with st.expander("Exactly which issues changed?"):
                for name, key in (("Resolved since prior audit", "resolved_examples"),
                                  ("New or reopened mandatory issues", "new_examples")):
                    examples = comparison.get(key) or []
                    if examples:
                        st.write("**" + name + "**")
                        st.dataframe(pd.DataFrame(examples), use_container_width=True,
                                     hide_index=True)
                st.caption("Up to 12 examples per group; complete changes are reflected in the counts.")
    elif comparison.get("reason"):
        st.caption("Run-to-run comparison not available: " + str(comparison["reason"]))

    history = report.get("verification_history") or []
    if len(history) >= 2:
        previous_counts = [
            {"Run": str(x.get("run_id") or "")[-9:],
             "Unresolved": int(x["remaining"])}
            for x in history
            if isinstance(x, dict) and str(x.get("remaining", "")).isdigit()
        ]
        if len(previous_counts) >= 2:
            with st.expander("Mandatory evidence gaps over recent published scans"):
                st.line_chart(pd.DataFrame(previous_counts), x="Run", y="Unresolved")
                st.caption("These are saved publication snapshots, not repeated displays of one run.")

    if sources.get("id") and str(sources["id"]) != str(report.get("latest_run_id")):
        if sources.get("status") in ACTIVE:
            st.info("The newest source scan is still running or queued; these evidence totals belong to an earlier published audit.")
        elif sources.get("status") == "completed":
            st.warning("The newest GitHub source run differs from the published audit. Check whether its report has been published before comparing totals.")

    rows = [{"Source": name,
             "Unresolved": next((int(s.get("required_findings_unresolved", 0)) for s in report.get("sources", [])
                                 if s.get("source") == name), 0)}
            for name in FAMILIES]
    breakdown = pd.DataFrame(rows)
    st.bar_chart(breakdown, x="Source", y="Unresolved", horizontal=True)
    st.caption("Current outstanding mandatory items by source. A count of zero does not mean the overall trade-entry gate has passed.")

    issues, note = required_issue_queue()
    if note:
        st.caption(note)
    if issues.empty and report.get("required_issue_examples"):
        issues = pd.DataFrame(report["required_issue_examples"]).fillna("")
        st.caption("Showing only the examples included in the audit; the full queue could not be retrieved.")
    if not issues.empty:
        st.markdown("### Issues requiring attention")
        options = ["ALL"] + sorted(str(x) for x in issues["category"].dropna().unique())
        selection = st.selectbox("Filter unresolved items by source", options,
                                 key="pdufa_live_issue_source")
        shown = issues if selection == "ALL" else issues[issues["category"] == selection]
        st.caption(f"{len(shown):,} unresolved rows shown" +
                   (f" out of {len(issues):,}" if selection != "ALL" else "") +
                   ". Each issue stays open until matching primary evidence is verified.")
        visible = [field for field in QUEUE_COLUMNS if field in shown.columns]
        st.dataframe(shown[visible], hide_index=True, use_container_width=True,
                     column_config={"source_url": st.column_config.LinkColumn("Evidence link",
                                                                               display_text="Open source")})
        st.download_button("DOWNLOAD REVIEW QUEUE CSV",
                           data=issues.to_csv(index=False).encode("utf-8"),
                           file_name="pdufa_remaining_evidence_checks.csv",
                           mime="text/csv", key="pdufa_live_review_queue_export")
    else:
        st.caption("No issue queue rows are available. Verify the published audit before interpreting an empty table as zero unresolved.")
