"""Current, read-only overnight scan status displayed at the top of SCANS.

GitHub execution, archived clinical reports, and source verification are shown
separately; no retired scan-status file is treated as the current run.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import re
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from scan_status_ui import current_job_steps, recent_github_runs, pacific_time

PACIFIC = ZoneInfo("America/Los_Angeles")
RUN_TITLE = "ALL + GEM — PDUFA overnight"
WORKFLOW = "pdufa-overnight-sequential.yml"
REPO = "pdufa/pdufa-command-center"
STALE_SOURCE = "UNKNOWN / NO MATCHING PUBLISHED REPORT"


def _parse(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def pacific_schedule_for(created_at):
    """Scheduled 10 PM Pacific for the run night; supports daylight saving."""
    when = _parse(created_at)
    if when is None:
        return None
    local = when.astimezone(PACIFIC)
    if local.hour >= 22:
        night = local.date()
    elif local.hour < 4:
        night = local.date() - timedelta(days=1)
    else:
        return None  # Manual daytime run: not a delayed night kickoff.
    return datetime.combine(night, time(hour=22), tzinfo=PACIFIC)


def run_delay_minutes(run):
    scheduled = pacific_schedule_for(run.get("created_at"))
    dispatched = _parse(run.get("created_at"))
    if scheduled is None or dispatched is None:
        return None
    return max(0, round((dispatched - scheduled).total_seconds() / 60))


def _status(job):
    state = str(job.get("status") or "UNKNOWN").upper()
    conclusion = str(job.get("conclusion") or "").upper()
    if state == "COMPLETED":
        return conclusion or "COMPLETED (NO RESULT)"
    return state


def _fmt_short(value):
    dt = _parse(value)
    return (dt.astimezone(PACIFIC).strftime("%b %d, %I:%M %p %Z")
            if dt else "Not reported")


def _duration(job):
    start, end = _parse(job.get("started_at")), _parse(job.get("completed_at"))
    if not start or not end:
        return "—"
    return f"{max(0, round((end-start).total_seconds()/60))} min"


def _stage_name(name):
    name = str(name or "")
    if name.startswith("clinical / "):
        return "Clinical"
    if name.startswith("sources / "):
        return "Primary sources / publication"
    if name.startswith("scoring-and-repair / "):
        return "Scoring / error checks / repair"
    if name.startswith("report / "):
        return "Clinical report"
    if name == "validate":
        return "Configuration validation"
    if name == "result":
        return "Final outcome"
    return "Other"


def stage_rows(jobs):
    return [{
        "Stage": _stage_name(j.get("name")),
        "Scan / check": j.get("name", "UNKNOWN"),
        "GitHub execution": _status(j),
        "Started (Pacific)": _fmt_short(j.get("started_at")),
        "Finished (Pacific)": _fmt_short(j.get("completed_at")),
        "Duration": _duration(j),
    } for j in jobs if isinstance(j, dict)]


def choose_run(runs, report, sources):
    """Use the newest real entire-chain run, falling back to matched report ID."""
    candidates = [r for r in runs if isinstance(r, dict) and
                  str(r.get("path") or "").split("/")[-1] == WORKFLOW and
                  r.get("event") == "workflow_dispatch" and
                  r.get("display_title") == RUN_TITLE]
    if candidates:
        return max(candidates, key=lambda r: r.get("created_at") or "")
    # Data-only fallback: no status or times invented if GitHub API unavailable.
    for payload in (sources, report):
        if str(payload.get("latest_run_id") or "").isdigit():
            return {"id": int(payload["latest_run_id"]), "status": "UNAVAILABLE",
                    "html_url": payload.get("latest_run_url"), "data_only": True}
    return {}


def source_matches_run(run, report):
    return bool(run.get("id") and
                str(run["id"]) == str(report.get("latest_run_id")) and
                report.get("schema_version") == 2)


@st.fragment(run_every="120s")
def render_overnight_execution(report_loader, source_loader, run_loader):
    """Active and last completed real scan, stage timings, source gaps, email proof."""
    st.markdown("## 10 PM PACIFIC — OVERNIGHT SCAN CONTROL & DETAILS")
    st.caption(
        "GitHub's timer is best-effort. Scheduled retries check every 10 minutes "
        "after the 10 PM target, and a recorded nightly run suppresses duplicates. "
        "Shows the actual dispatch and exact workflow jobs, not an assumed on-time start. "
        "Times below are Pacific; refreshes while SCANS is open."
    )
    if st.button("↻ CHECK LATEST OVERNIGHT RUN", key="overnight_status_refresh"):
        recent_github_runs.clear()
        current_job_steps.clear()
        report_loader.clear()
        source_loader.clear()
        run_loader.clear()
        st.rerun(scope="fragment")
    clinical, clinical_note = report_loader()
    sources = source_loader()
    clinical = clinical if isinstance(clinical, dict) else {}
    sources = sources if isinstance(sources, dict) else {}
    runs, runs_note = recent_github_runs()
    # Dedicated workflow endpoint avoids unrelated CI/repair runs pushing the
    # latest complete overnight chain out of the general GitHub results page.
    direct = run_loader()
    verified_runs = ([direct] if isinstance(direct, dict) and direct.get('id') else [])
    run = choose_run(verified_runs + runs, clinical, sources)
    if not run:
        st.error("No verified nightly scan found in current GitHub results or saved audits.")
        if runs_note:
            st.caption(runs_note)
        return

    run_id = run.get("id")
    created = run.get("created_at")
    scheduled = pacific_schedule_for(created)
    delay = run_delay_minutes(run)
    completed = run.get("updated_at") if run.get("status") == "completed" else None
    scheduled_text = (scheduled.strftime("%b %d, %I:%M %p %Z")
                      if scheduled else "10:00 PM Pacific · night unverified")
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Target start", scheduled_text)
    p2.metric("Actual dispatch", _fmt_short(created))
    p3.metric("Start delay", f"{delay:,} min" if delay is not None else "Not verified")
    p4.metric("Workflow finished", _fmt_short(completed) if completed else
              str(run.get("status") or "Not verified").replace("_", " ").title())

    if run.get("status") == "completed" and run.get("conclusion") == "success":
        st.success(f"GitHub scan sequence #{run_id}: EXECUTION SUCCESS. Evidence still requires separate verification.")
    elif run.get("status") == "completed":
        st.error(f"GitHub scan sequence #{run_id}: {str(run.get('conclusion') or 'unknown').upper()}.")
    elif run.get("status") in ("queued", "in_progress", "waiting", "pending"):
        st.info(f"Overnight chain #{run_id} is {str(run['status']).replace('_',' ').upper()}.")
    else:
        st.warning("GitHub live status unavailable. Only saved reports below can be confirmed.")

    if delay is not None and delay > 15:
        st.warning(f"LATE NIGHTLY START: GitHub dispatched this chain {delay} minutes after 10 PM Pacific. "
                   "Extra retries reduce missed starts but cannot guarantee GitHub schedule timing.")
    if runs_note:
        st.caption("GitHub status warning: " + str(runs_note))
    if clinical_note:
        st.caption("Clinical snapshot: " + str(clinical_note))
    if isinstance(run.get("html_url"), str) and run["html_url"].startswith(
        "https://github.com/" + REPO + "/actions/runs/"
    ):
        st.link_button("OPEN THIS EXACT OVERNIGHT GITHUB RUN", run["html_url"])

    jobs = current_job_steps(run_id) if isinstance(run_id, int) else []
    # Show evidence of *actual* GitHub timer wake-ups for the same Pacific
    # night. Missing early ticks are not proof of a cause; schedules are best
    # effort, and GitHub's general run listing is bounded.
    start_ticks = []
    if scheduled is not None:
        for tick in runs:
            if (isinstance(tick, dict) and tick.get("event") == "schedule" and
                    str(tick.get("path") or "").split("/")[-1] ==
                    "pdufa-nightly-pacific-start.yml"):
                slot = pacific_schedule_for(tick.get("created_at"))
                if slot is not None and slot.date() == scheduled.date():
                    start_ticks.append(tick)
    with st.expander("10 PM SCHEDULER / RECOVERY ATTEMPTS", expanded=False):
        st.caption(
            "GitHub timer wake-ups recorded for this Pacific night, including "
            "extra recovery checks. Successful timer jobs are not the same as "
            "a successfully completed scan. The recent Actions list may omit "
            "older timer attempts."
        )
        if start_ticks:
            timer_rows = [{
                "Timer invoked (Pacific)": _fmt_short(t.get("created_at")),
                "Job status": _status(t),
                "GitHub run": (
                    t.get("html_url") if str(t.get("html_url", "")).startswith(
                        "https://github.com/" + REPO + "/actions/runs/") else ""),
            } for t in sorted(start_ticks, key=lambda x: x.get("created_at") or "")[:20]]
            st.dataframe(pd.DataFrame(timer_rows), hide_index=True,
                         use_container_width=True,
                         column_config={
                             "GitHub run": st.column_config.LinkColumn(
                                 "GitHub run", display_text="Open timer")})
        else:
            st.info("No timer wake-up records for this scan night were found "
                    "in the available recent GitHub results.")

    if jobs:
        details = pd.DataFrame(stage_rows(jobs))
        st.markdown("### EACH SCAN / STAGE — START, FINISH, RESULT")
        st.dataframe(details, use_container_width=True, hide_index=True, height=420)
        failed = details[details["GitHub execution"].isin(
            ["FAILURE", "TIMED_OUT", "CANCELLED"])]
        if not failed.empty:
            st.error("Failed or cancelled stages: " +
                     "; ".join(failed["Scan / check"].astype(str).tolist()))
    else:
        st.warning("Individual GitHub stage details not available from the API. "
                   "This is NOT a confirmation that those stages ran.")

    st.markdown("### SAVED EVIDENCE — MUST MATCH THIS RUN")
    matched_clinical = str(clinical.get("latest_run_id")) == str(run_id)
    matched_source = source_matches_run(run, sources)
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Clinical report", str(clinical.get("status") or "NOT PUBLISHED")
              if matched_clinical else "STALE / DIFFERENT RUN")
    k2.metric("Source verification", str(sources.get("status") or "UNVERIFIED")
              if matched_source else "STALE / DIFFERENT RUN")
    k3.metric("Required gaps", str(sources.get("required_findings_unresolved", "Unknown"))
              if matched_source else "Unknown")
    k4.metric("Verified source families",
              (f"{sources.get('sources_passed', '?')}/{sources.get('sources_due', '?')}"
               if matched_source else "Unknown"))
    if not matched_clinical:
        st.warning("Clinical report does not identify this same GitHub run; "
                   "older data is NOT counted as tonight's result.")
    if not matched_source:
        st.warning("The published FDA/SEC/financial/market/issuer report has not "
                   "matched this GitHub run. Prior figures are not current scan results.")
    else:
        source_rows = [
            {"Source": item.get("source", "UNKNOWN"),
             "Verification": item.get("status", "UNVERIFIED"),
             "Findings verified": item.get("findings_verified"),
             "Required unresolved": item.get("required_findings_unresolved"),
             "Supplemental unavailable": item.get("optional_findings_unavailable")}
            for item in sources.get("sources", []) if isinstance(item, dict)
        ]
        if source_rows:
            st.dataframe(pd.DataFrame(source_rows), use_container_width=True,
                         hide_index=True)
        unresolved = sources.get("missing_required_source_families") or []
        if unresolved:
            st.error("Required source families still incomplete: " +
                     ", ".join(str(x) for x in unresolved))
        with st.expander("EXACT EVIDENCE GAPS / NEXT REVIEW", expanded=False):
            issues = sources.get("required_issue_examples") or []
            if issues:
                fields = ("ticker", "category", "claim", "verification_status", "reason")
                st.dataframe(pd.DataFrame([{field: x.get(field, "") for field in fields}
                                           for x in issues if isinstance(x, dict)]),
                             use_container_width=True, hide_index=True)
            else:
                st.caption("No individual issue examples in the published report.")

    st.markdown("### GMAIL START / END SUBMISSION CHECK")
    st.caption(
        "Each row below is the actual GitHub step that attempted a mail action. "
        "SUCCESS proves the step exited successfully, not that Gmail delivered "
        "a message to your inbox. START/END delivery remains UNVERIFIED "
        "until independent mailbox or provider evidence is available."
    )
    mail_steps = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        for step in (job.get("steps") or []):
            name = str(step.get("name") or "")
            if re.search(r"\b(?:gmail|smtp|e-?mail|notification)\b", name, flags=re.I):
                mail_steps.append({
                    "Scan stage": str(job.get("name") or ""),
                    "Email action": name,
                    "GitHub step result": _status(step),
                    "Started (Pacific)": _fmt_short(step.get("started_at")),
                    "Finished (Pacific)": _fmt_short(step.get("completed_at")),
                    "Inbox delivery": "NOT INDEPENDENTLY VERIFIED",
                })
    if mail_steps:
        st.dataframe(pd.DataFrame(mail_steps), use_container_width=True,
                     hide_index=True, height=min(390, 70 + 36 * len(mail_steps)))
        if any(x["GitHub step result"] in ("FAILURE", "TIMED_OUT", "CANCELLED")
               for x in mail_steps):
            st.error("At least one email-related GitHub step failed. Check its run log.")
    else:
        st.warning("No individual email submission steps are available for this run. "
                   "Email submission and delivery cannot be confirmed.")
    st.write("**Inbox delivery:** NOT VERIFIED · **Scan archival:** "
             + ("matching" if matched_clinical and matched_source else "pending / mismatched"))
    st.caption(
        "Legacy data/overnight_scan_status.json may be older than the latest "
        "nightly run; it is deliberately not used to determine these metrics. "
        "Scan execution success is not permission to trade an unverified program."
    )
