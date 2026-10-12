"""GitHub-backed Nightly Scan Report, separate from Watchlist / Trading.

The scan report is a read-only published GitHub Actions audit. Mutating
controls require BOTH a server-side GitHub token and a dashboard PIN.
"""
import hmac
import json
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

REPO = "pdufa/pdufa-command-center"
REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/nightly_scan_report.json"
API = "https://api.github.com/repos/" + REPO
WORKFLOW = "pdufa-scan-control.yml"
LABELS = {"2": "#2 PIPELINE", "3": "#3 PRE3", "4": "#4 POST3"}


@st.cache_data(ttl=90, show_spinner=False)
def published_report():
    request = urllib.request.Request(REPORT_URL, headers={
        "User-Agent": "pdufa-command-center-dashboard",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.load(response)
        if isinstance(result, dict) and result.get("schema_version") == 1:
            return result, None
        return {}, "Published report is not in the expected format."
    except (ValueError, OSError, urllib.error.URLError) as exc:
        local = Path("data/nightly_scan_report.json")
        if local.exists():
            try:
                data = json.loads(local.read_text(encoding="utf-8"))
                if data.get("schema_version") == 1:
                    return data, "Showing the deployed snapshot; live report fetch unavailable."
            except (OSError, ValueError, AttributeError):
                pass
        return {}, "No published nightly scan report yet (" + type(exc).__name__ + ")."


@st.cache_data(ttl=60, show_spinner=False)
def latest_run():
    request = urllib.request.Request(
        API + "/actions/workflows/pdufa-nightly-clinical.yml/runs?per_page=1",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "pdufa-command-center-dashboard"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.load(response)
        return (data.get("workflow_runs") or [{}])[0]
    except (ValueError, OSError, urllib.error.URLError):
        return {}


def dashboard_secret(key):
    try:
        value = st.secrets.get(key, "")
        return str(value).strip() if value else ""
    except (FileNotFoundError, KeyError, AttributeError):
        return ""


def dispatch_action(action, scan, token):
    if action not in {"VERIFY_ALL", "REVERIFY_PARTIAL", "RESCAN_ALL"}:
        raise ValueError("Invalid control action")
    if scan not in {"ALL", "2", "3", "4"}:
        raise ValueError("Invalid scan")
    body = json.dumps({"ref": "main", "inputs": {
        "action": action, "scan": scan,
    }}).encode("utf-8")
    req = urllib.request.Request(
        API + "/actions/workflows/" + WORKFLOW + "/dispatches",
        data=body, method="POST", headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "pdufa-command-center-dashboard",
        })
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("GitHub did not accept the workflow request")


def _run_request(action, scan, token):
    try:
        dispatch_action(action, scan, token)
        latest_run.clear()
        st.success("GitHub accepted " + action.replace("_", " ") +
                   (" for #" + scan if scan != "ALL" else " for clinical scans #2/#3/#4") +
                   ". Results appear after the workflow finishes and publishes its audit.")
    except urllib.error.HTTPError as exc:
        st.error("GitHub rejected the request (HTTP " + str(exc.code) +
                 "). Check Actions permission and the configured token.")
    except (OSError, ValueError, RuntimeError) as exc:
        st.error("Could not submit scan request: " + type(exc).__name__)



ADHOC_WORKFLOW = "pdufa-adhoc-error-check.yml"
ADHOC_URL = ("https://github.com/" + REPO + "/actions/workflows/" + ADHOC_WORKFLOW)


def dispatch_adhoc_error_check(token):
    """Authenticated, PIN-gated manual dispatch; 204 means accepted, not complete."""
    if not token:
        raise ValueError("GitHub dashboard token is not configured")
    req = urllib.request.Request(
        API + "/actions/workflows/" + ADHOC_WORKFLOW + "/dispatches",
        data=json.dumps({"ref": "main"}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "pdufa-command-center-dashboard",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("GitHub did not accept ad hoc error check")


@st.cache_data(ttl=45, show_spinner=False)
def latest_adhoc_check_run():
    req = urllib.request.Request(
        API + "/actions/workflows/" + ADHOC_WORKFLOW +
        "/runs?per_page=1",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "pdufa-command-center-dashboard"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.load(response)
        return (data.get("workflow_runs") or [{}])[0]
    except (ValueError, OSError, urllib.error.URLError):
        return {}


def render_adhoc_error_check_controls():
    """Protected direct dispatch when configured; otherwise honest GitHub fallback."""
    st.markdown("### AD HOC — GMAIL + GITHUB ERROR CHECK")
    st.caption(
        "Checks automatically after completed nightly clinical, FDA/SEC, report and PRE3 runs. "
        "You can also check GitHub failures and Gmail alert headers immediately. "
        "The audit does not rescan clinical/FDA/SEC data, change evidence, "
        "send emails, or change your automatic schedule."
    )
    token = dashboard_secret("PDUFA_GITHUB_TOKEN")
    pin = dashboard_secret("PDUFA_SCAN_CONTROL_PIN")

    if not token or not pin:
        st.warning(
            "One-click dispatch is not configured in Streamlit yet: "
            "PDUFA_GITHUB_TOKEN or PDUFA_SCAN_CONTROL_PIN is missing. "
            "Use the GitHub Actions manual-run option below."
        )
        st.link_button(
            "▶ RUN AD HOC CHECK IN GITHUB",
            ADHOC_URL,
            use_container_width=True,
        )
        st.caption(
            "In GitHub Actions, select **Run workflow → main → Run workflow**. "
            "To enable this page's direct one-click control, add both named "
            "secrets in Streamlit Community Cloud app settings. "
            "Do not paste a token or PIN into the public dashboard."
        )
    else:
        supplied = st.text_input(
            "Ad hoc check PIN", type="password", key="pdufa_adhoc_check_pin",
            help="Uses your existing scan-control PIN; never written to GitHub logs.",
        )
        authorized = bool(supplied and hmac.compare_digest(supplied, pin))
        clicked = st.button(
            "▶ RUN AD HOC GMAIL + GITHUB ERROR CHECK",
            key="pdufa_adhoc_error_check_button",
            use_container_width=True,
            disabled=not authorized,
        )
        # Recheck on the server; a disabled UI alone is not authorization.
        if clicked and authorized:
            try:
                dispatch_adhoc_error_check(token)
                latest_adhoc_check_run.clear()
                st.success(
                    "GitHub accepted the read-only audit request. "
                    "A queued request is not a completed check; open the run for results."
                )
            except urllib.error.HTTPError as exc:
                st.error(
                    "GitHub rejected the request (HTTP " + str(exc.code) +
                    "). Check Actions write permission for the configured token."
                )
            except (OSError, RuntimeError, ValueError) as exc:
                st.error("Could not start ad hoc audit: " + type(exc).__name__)
        if not authorized:
            st.caption("Enter your scan-control PIN to enable direct dispatch.")
        st.link_button("OPEN AD HOC ERROR CHECK / RESULTS IN GITHUB", ADHOC_URL)

    last = latest_adhoc_check_run()
    if last:
        st.caption(
            "Latest automatic/manual error check: #" + str(last.get("id", "?")) +
            " · " + str(last.get("status", "unknown")) +
            " · " + str(last.get("conclusion") or "not finished") +
            " · started " + str(last.get("created_at") or "unknown")
        )
        url = last.get("html_url")
        if isinstance(url, str) and url.startswith("https://github.com/"):
            st.link_button("VIEW LAST AD HOC CHECK RUN", url)
    st.caption(
        "The run archives a JSON report. Gmail uses GitHub's existing "
        "app-password credentials; unavailable checks remain UNAVAILABLE."
    )

def _number(v):
    return f"{v:,}" if type(v) is int else "—"


def render_nightly_scan_report():
    st.markdown("## NIGHTLY SCAN REPORT")
    st.caption("Clinical-source #2 PIPELINE / #3 PRE3 / #4 POST3 · automatic nightly scan + archived-source integrity check · last published results. FDA, SEC, issuer and full market verification remain separate.")

    report, loading_note = published_report()
    running = latest_run()
    if loading_note:
        st.info(loading_note)
    if running and running.get("status") in ("queued", "in_progress", "waiting", "pending"):
        st.warning("Collector run #" + str(running.get("id")) + " is " +
                   str(running.get("status")).replace("_", " ") +
                   ". The report below may describe a previous run.")
    if report:
        summary = report.get("metrics", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Coverage status", str(report.get("status", "UNVERIFIED")))
        c2.metric("New records", _number(summary.get("new_records")))
        c3.metric("Changed trials", _number(summary.get("changed_trials")))
        c4.metric("Reported errors", _number(summary.get("errors")))
        st.caption("Last published: " + str(report.get("updated_at_utc", "unknown")) +
                   " · GitHub run #" + str(report.get("latest_run_id", "unknown")) +
                   " · workflow: " + str(report.get("latest_run_conclusion", "unknown")))
        last_link = report.get("latest_run_url")
        if isinstance(last_link, str) and last_link.startswith("https://github.com/"):
            st.link_button("View source scan in GitHub Actions", last_link)
        verify = report.get("verification", {})
        st.write("**Archive integrity verification:** " +
                 str(verify.get("artifact_integrity", "NOT CHECKED")) +
                 " · **All-source evidence verification:** NOT VERIFIED")
        st.caption(str(verify.get("description", "No verification report available.")))
        rows = []
        for scan in report.get("scans", []):
            if not isinstance(scan, dict):
                continue
            metrics = scan.get("metrics") or {}
            rows.append({
                "Scan": LABELS.get(str(scan.get("scan")), str(scan.get("scan"))),
                "Result": scan.get("status", "UNVERIFIED"),
                "Report check": scan.get("artifact_integrity", "NOT CHECKED"),
                "Studies checked": metrics.get("studies_checked"),
                "Trials checked": metrics.get("tracked_trials_checked"),
                "New records": scan.get("new_records"),
                "Changed trials": scan.get("changed_trials_this_execution"),
                "Errors": scan.get("errors_count"),
                "Run ID": scan.get("run_id"),
            })
        if rows:
            st.markdown("### What was newly scanned and verified?")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("New records/changed trials are only shown if the scanner actually returned a count; a blank field means not reported, not zero. Report check verifies saved clinical scanner JSON against its source-state JSON.")
            for scan in report.get("scans", []):
                sid = str(scan.get("scan"))
                if sid not in LABELS:
                    continue
                with st.expander(LABELS[sid] + " — detailed audit"):
                    st.write("Collector status:", scan.get("collector_status", "Not reported"))
                    st.write("Latest scan:", scan.get("collected_at_utc", "Not reported"))
                    st.write("Source counts:", scan.get("metrics", {}))
                    issues = scan.get("issues") or []
                    if issues:
                        st.warning("Verification exceptions: " + "; ".join(map(str, issues)))
                    else:
                        st.success("Archived clinical source-state and count checks passed. Full all-source PDUFA verification remains outstanding.")
        with st.expander("Unverified source families — why coverage is PARTIAL"):
            for family in report.get("missing_required_source_families", []):
                st.write("• " + str(family))
        hist = report.get("history", [])
        if hist:
            with st.expander("Prior nightly run history (latest 30)"):
                st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
        st.download_button("DOWNLOAD SCAN AUDIT JSON",
                           data=json.dumps(report, indent=2),
                           file_name="pdufa_nightly_scan_report.json",
                           mime="application/json")
    else:
        st.warning("No published clinical report is available. The next completed nightly scan will publish a source-audited summary; no completion counts are inferred.")

    st.markdown("### Scan controls")
    st.link_button("OPEN SCAN CONTROLS IN GITHUB ACTIONS",
                   "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-scan-control.yml")
    st.caption("VERIFY ALL checks the archived #2/#3/#4 collector reports and saved source-state counts; it cannot certify missing FDA/SEC/issuer/market sources. REVERIFY PARTIAL recollects selected clinical data and checks the new archive. RESCAN ALL reruns all three clinical collectors. These actions do not place trades.")
    token = dashboard_secret("PDUFA_GITHUB_TOKEN")
    pin = dashboard_secret("PDUFA_SCAN_CONTROL_PIN")
    supplied = st.text_input("Scan controls PIN", type="password",
                             key="pdufa_nightly_control_pin",
                             help="PIN never appears in scan logs or published reports.")
    authorized = bool(token and pin and hmac.compare_digest(supplied, pin))
    if not token or not pin:
        st.warning("Scan controls are locked until PDUFA_GITHUB_TOKEN and PDUFA_SCAN_CONTROL_PIN are set in Streamlit app secrets. Report viewing remains available.")
    elif not authorized:
        st.caption("Enter the control PIN to enable verified GitHub Actions requests.")
    a, b, c = st.columns(3)
    with a:
        if st.button("REVERIFY PARTIAL", disabled=not authorized, use_container_width=True,
                     key="nightly_reverify_all"):
            _run_request("REVERIFY_PARTIAL", "ALL", token)
    with b:
        if st.button("VERIFY ALL", disabled=not authorized, use_container_width=True,
                     key="nightly_verify_all"):
            _run_request("VERIFY_ALL", "ALL", token)
    with c:
        if st.button("RESCAN ALL", disabled=not authorized, use_container_width=True,
                     key="nightly_rescan_all"):
            _run_request("RESCAN_ALL", "ALL", token)
    scan_choice = st.selectbox("Target one partial clinical scan",
                               options=["2", "3", "4"],
                               format_func=lambda x: LABELS[x],
                               key="nightly_target_scan")
    if st.button("REVERIFY SELECTED PARTIAL SCAN", disabled=not authorized,
                 key="nightly_reverify_selected"):
        _run_request("REVERIFY_PARTIAL", scan_choice, token)
    st.caption("All controls execute on GitHub Actions; a queued request is not a completed scan. The next published audit is the record of results.")
