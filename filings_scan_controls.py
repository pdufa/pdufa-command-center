"""Authenticated, section-specific manual controls for the existing filings tables."""
from __future__ import annotations

import hmac
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import streamlit as st

from scan_status_ui import ACTIVE, API, BASE, _json_get, pacific_time, run_link, run_state
from scripts.filings_section_scan import SECTIONS, SNAPSHOTS, load_snapshot, section_config

WORKFLOW = "pdufa-filings-section-scan.yml"
WORKFLOW_URL = BASE + "/actions/workflows/" + WORKFLOW
DATA = Path(__file__).resolve().parent / "data"


def secret(name):
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except (OSError, KeyError, AttributeError):
        return ""


def authorized(token, pin, *supplied):
    return bool(token and pin and any(
        hmac.compare_digest(str(value or "").encode(), pin.encode()) for value in supplied))


def render_section_scan_unlock():
    st.text_input("Section scan PIN", type="password", key="filings_scan_control_pin",
                  help="Use your existing scan-control PIN to enable the four section buttons.")
    if not secret("PDUFA_GITHUB_TOKEN") or not secret("PDUFA_SCAN_CONTROL_PIN"):
        st.info("Direct section scans need the existing dashboard token and scan PIN configured "
                "in Streamlit. The Run section scan in GitHub link is available below.")
    st.link_button("Run section scan in GitHub", WORKFLOW_URL)


def dispatch_section_scan(section, token, pin, supplied):
    section_config(section)
    # Check at the mutation boundary, in addition to disabling the UI button.
    if not authorized(token, pin, supplied):
        raise PermissionError("Scan controls are locked")
    request = urllib.request.Request(
        API + "/actions/workflows/" + WORKFLOW + "/dispatches",
        data=json.dumps({"ref": "main", "inputs": {"section": section}}).encode(),
        method="POST", headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "pdufa-filings-section-controls",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("GitHub did not accept the section scan")


@st.cache_data(ttl=30, show_spinner=False)
def section_runs():
    try:
        payload = _json_get(API + "/actions/workflows/" + WORKFLOW + "/runs?branch=main&per_page=50")
        runs = payload["workflow_runs"]
        if not isinstance(runs, list):
            raise ValueError("Missing section run list")
        return runs, ""
    except (OSError, ValueError, KeyError, TypeError):
        return [], "Live section status unavailable. Open GitHub results for the latest run."


def section_run(runs, section):
    section_config(section)
    matches = [r for r in runs if str(r.get("display_title", "")).startswith(section + " —")]
    return max(matches, key=lambda r: r.get("created_at", ""), default={})


@st.fragment(run_every=30)
def render_section_scan(section):
    _, mode = section_config(section)
    token, pin = secret("PDUFA_GITHUB_TOKEN"), secret("PDUFA_SCAN_CONTROL_PIN")
    supplied = st.session_state.get("filings_scan_control_pin", "")
    if not authorized(token, pin, supplied):
        supplied = st.session_state.get("pdufa_nightly_control_pin", "")
    unlocked = authorized(token, pin, supplied)
    runs, notice = section_runs()
    current = section_run(runs, section)
    pending_key = "filings_scan_pending_" + section
    pending_at = st.session_state.get(pending_key, 0)
    pending = bool(pending_at and time.time() - pending_at < 90
                   and (not current or current.get("created_at", "") <
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(pending_at))))
    active = current.get("status") in ACTIVE
    clicked = st.button("▶ Scan this section", key="scan_section_" + section,
                 disabled=not unlocked or pending or active,
                 help=("Recheck this agency's complete saved baseline." if mode == "FULL" else
                       "Check this agency's new/changed filings and unresolved evidence; retain unchanged verified claims."))
    if clicked and unlocked and not pending and not active:
        try:
            dispatch_section_scan(section, token, pin, supplied)
            st.session_state[pending_key] = time.time()
            section_runs.clear()
            st.success("Request accepted. This section is waiting to start; results publish after it finishes.")
        except urllib.error.HTTPError as error:
            st.error(f"GitHub rejected the section scan (HTTP {error.code}). Check Actions write permission.")
        except (OSError, ValueError, RuntimeError, PermissionError):
            st.error("Section scan could not be submitted. Check the scan controls and try again.")
    if pending:
        st.caption("Request accepted · waiting for GitHub to start.")
    elif current:
        st.caption(run_state(current) + " · started " + pacific_time(current.get("created_at")))
    if not unlocked:
        st.caption("Enter the existing scan-control PIN above to enable this button.")
    if notice:
        st.caption(notice)
    folder = DATA / SNAPSHOTS / section.lower()
    if (folder / "report.json").is_file():
        try:
            report = load_snapshot(folder, DATA, section)["report"]
            st.caption("Last published check: " + pacific_time(report["finished_at"]) +
                       " · " + report["evidence_status"] + " · " +
                       str(report["required_findings_unresolved"]) + " evidence gaps remaining.")
        except (OSError, ValueError, KeyError, TypeError):
            st.caption("Previous section results need a fresh scan for the current candidate list.")
    st.link_button("View section scan results", run_link(current) or WORKFLOW_URL,
                   key="section_results_" + section)
