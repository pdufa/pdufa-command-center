"""GitHub-backed Nightly Scan Report, separate from Watchlist / Trading.

The scan report is a read-only published GitHub Actions audit. Mutating
controls require BOTH a server-side GitHub token and a dashboard PIN.
"""
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import streamlit as st
from gem_scans_ui import render_gem_scans
from scan_status_ui import render_scan_status
from scripts.pdufa_morning_results import make_snapshot

REPO = "pdufa/pdufa-command-center"
REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/nightly_scan_report.json"
SOURCE_REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/pdufa_source_report.json"
API = "https://api.github.com/repos/" + REPO
WORKFLOW = "pdufa-scan-control.yml"
AM_REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/pdufa_am_6am_results.json"
LABELS = {"2": "#2 PIPELINE", "3": "#3 PRE3", "4": "#4 POST3"}


@st.cache_data(ttl=60, show_spinner=False)
def published_source_report():
    request = urllib.request.Request(SOURCE_REPORT_URL, headers={"User-Agent": "pdufa-command-center-dashboard", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            report = json.load(response)
    except (OSError, ValueError):
        try:
            report = json.loads(Path("data/pdufa_source_report.json").read_text())
        except (OSError, ValueError):
            return {}
    return report if isinstance(report, dict) and report.get("schema_version") == 2 else {}


@st.cache_data(ttl=60, show_spinner=False)
def published_am_report():
    request = urllib.request.Request(
        AM_REPORT_URL,
        headers={"User-Agent": "pdufa-command-center-dashboard",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except (OSError, ValueError):
        try:
            payload = json.loads(
                Path("data/pdufa_am_6am_results.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return {}
    return (payload if isinstance(payload, dict) and
            payload.get("schema_version") == 1 and
            payload.get("report_type") == "PDUFA_6AM_PACIFIC_MORNING_RESULTS"
            else {})


def render_am_results():
    st.markdown("## 6:00 AM PACIFIC — MORNING SCAN RESULTS")
    st.caption(
        "Read-only summary of last night's 8:30 PM clinical, FDA, SEC, "
        "financial, market and issuer checks. The morning summary does not "
        "start a new scan or authorize a trade."
    )
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    report = published_am_report()
    today = now.date().isoformat()
    if now.hour >= 6 and report.get("snapshot_date_pacific") != today:
        # GitHub scheduled starts can be delayed. Show a clearly marked
        # provisional preview of already-published evidence rather than
        # yesterday's figures as if they were today's 6 AM report.
        clinical, _note = published_report()
        report = make_snapshot(
            clinical, published_source_report(), now=now
        )
        st.warning(
            "Today's scheduled 6 AM snapshot has not published yet. "
            "Showing a live preview from the latest published files. "
            "Missing overnight results remain PENDING."
        )
    elif not report:
        st.info("No 6 AM morning snapshot yet. The first scheduled morning report "
                "will appear after the next 6 AM Pacific publication.")
        return
    elif report.get("snapshot_date_pacific") != today:
        st.info(
            "Showing the preceding morning's report (" +
            str(report.get("snapshot_date_pacific")) +
            "). Today's report is scheduled for 6:00 AM Pacific."
        )
    clinical = report.get("clinical") or {}
    source = report.get("sources") or {}
    readiness = str(report.get("readiness") or "UNKNOWN")
    if readiness != "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS":
        st.warning(
            "OVERNIGHT RESULTS PENDING / STALE — at least one source family "
            "has not published tonight's evidence. No missing counts are "
            "interpreted as zero."
        )
    else:
        st.info(
            "Both overnight report families were published. Their results "
            "can still have unresolved evidence gaps and do not approve GEM entry."
        )
    c1, c2, c3, c4 = st.columns(4)
    percent = source.get("required_source_coverage_percent")
    pending = source.get("required_findings_unresolved")
    resolved = source.get("newly_resolved_claims")
    sec_found = source.get("sec_transactions_verified")
    c1.metric("Required source coverage", f"{percent:.1f}%" if type(percent) in (int, float) else "Pending")
    c2.metric("Unresolved required claims", f"{pending:,}" if type(pending) is int else "Pending")
    c3.metric("Claims newly cleared", f"{resolved:,}" if type(resolved) is int else "Not reported")
    c4.metric("Individual SEC closings matched", f"{sec_found:,}" if type(sec_found) is int else "Pending")
    st.caption(
        "Morning date (Pacific): " + str(report.get("snapshot_date_pacific", "unknown")) +
        " · Generated: " + str(report.get("generated_at_pacific", "unknown")) +
        " · Clinical: " + str(clinical.get("status", "PENDING")) +
        " · Extended source verification: " + str(source.get("status", "PENDING"))
    )
    st.caption(
        "Financing IR→SEC recheck: " + str(source.get("public_ir_sec_recheck_status", "PENDING")) +
        " · SEC lead checks: " + str(source.get("public_ir_sec_leads_checked") if
                                  source.get("public_ir_sec_leads_checked") is not None
                                  else "PENDING") +
        " · No trade entry is authorized by this summary."
    )
    links = [("CLINICAL", clinical.get("source_run_url")),
             ("SEC / SOURCES", source.get("source_run_url"))]
    for label, url in links:
        if isinstance(url, str) and url.startswith(
            "https://github.com/" + REPO + "/actions/runs/"
        ):
            st.link_button("OPEN " + label + " OVERNIGHT RUN", url)
    with st.expander("6 AM report — latest overnight clinical scan statuses"):
        rows = [
            {"Scan": LABELS.get(str(key), str(key)),
             "Status": row.get("collector_status"),
             "New records": row.get("new_records"),
             "Changed trials": row.get("changed_trials")}
            for key, row in (clinical.get("runs") or {}).items()
            if isinstance(row, dict)
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.write("No newly published overnight clinical detail available.")


def render_extended_source_report():
    report = published_source_report()
    if not report:
        return
    st.markdown("### FDA / SEC / FINANCIAL / MARKET / ISSUER")
    st.write("**Scan execution:** " + str(report.get("execution_status", "UNVERIFIED")) +
             " · **Required source verification:** " + str(report.get("status", "UNVERIFIED")))
    st.caption("Source checks finished: " + str(report.get("source_checked_at_utc", report.get("updated_at_utc", "unknown"))) +
               " · Report published: " + str(report.get("updated_at_utc", "unknown")) +
               ". Completion refers to the checks listed below; trading evidence and eligibility remain separate.")
    rows = [{"Scan": r["source"], "Status": r["status"], "Verified": r.get("findings_verified", 0),
             "Not applicable": r.get("findings_not_applicable", 0),
             "Required gaps": r.get("required_findings_unresolved", 0),
             "Supplemental unavailable": r.get("optional_findings_unavailable", 0)} for r in report.get("sources", [])]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    issues = report.get("required_issue_examples", [])
    if issues:
        with st.expander("Required evidence still needing attention"):
            st.dataframe(pd.DataFrame([{k:r.get(k) for k in ("ticker", "category", "claim", "verification_status", "reason")} for r in issues]), hide_index=True, use_container_width=True)
    if report.get("optional_findings_unavailable"):
        st.info("Some supplemental market fields are unavailable. Short shares are kept separate from short interest as a percentage of float; options IV and borrow data are not inferred from prices.")
    # Research confirmations remain visible when the subsequent SEC lookup is
    # blocked. Only a fresh, dated issuer-matched SEC document can verify one
    # financing transaction; no row can approve the required second financing.
    st.markdown("### FINANCING: INVESTOR RELATIONS → FRESH SEC RECHECK")
    ir = report.get("public_ir_sec_recheck") or {}
    ir_status = str(ir.get("status") or "NOT YET RUN")
    ir_rows = ir.get("results", [])
    st.caption(
        "Research-only evidence. Google/Bing/Yahoo and company IR provide leads; "
        "every SEC scan re-opens matching issuer filings. A verified SEC transaction "
        "is NOT proof of two distinct closes after Phase 3, nor a trade signal."
    )
    a, b = st.columns(2)
    a.metric("Public/IR closing leads rechecked", ir.get("leads_checked", 0))
    b.metric("Individual SEC transactions confirmed", ir.get("sec_transactions_verified", 0))
    if ir_status != "COMPLETE_RESEARCH_ONLY":
        st.warning("Fresh IR → SEC confirmation results unavailable: " + ir_status +
                   ". Earlier research leads remain provisional; do not infer a closing.")
    if isinstance(ir_rows, list) and ir_rows:
        display = pd.DataFrame(ir_rows).reindex(columns=[
            "ticker", "event_key", "company_ir_status", "ir_close_date",
            "transaction_type", "company_ir_url", "sec_recheck_status",
            "sec_url", "checked_at_utc", "reason", "gem_entry_authorized",
        ])
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "EXPORT INVESTOR RELATIONS / SEC FINANCING RECHECK",
            data=display.to_csv(index=False), mime="text/csv",
            file_name="pdufa_financing_ir_sec_recheck.csv",
            key="pdufa_financing_ir_sec_recheck_export",
        )
    st.link_button(
        "REVIEW ALL 45 PUBLIC-SOURCE RESEARCH FINDINGS",
        "https://github.com/" + REPO +
        "/blob/main/reports/missing_sources/public_web_cross_check_2026-10-13.csv",
    )
    run_url = report.get("latest_run_url", "")
    if run_url.startswith("https://github.com/" + REPO + "/actions/runs/"):
        st.link_button("VIEW SOURCE SCAN AND EVIDENCE", run_url)
    st.link_button("RERUN SOURCE CHECKS IN GITHUB", "https://github.com/" + REPO + "/actions/workflows/pdufa-nightly-missing-sources.yml")
    st.download_button("DOWNLOAD SOURCE VERIFICATION SUMMARY", json.dumps(report, indent=2),
                       file_name="pdufa_source_verification_summary.json", mime="application/json")


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
    # Single SCANS home for live GitHub execution health, historical results,
    # required evidence gaps, existing GEMS, and manual controls.
    render_am_results()
    st.divider()
    render_scan_status(published_source_report)
    st.divider()
    render_gem_scans()
    st.divider()
    st.markdown("## NIGHTLY SCAN REPORT")
    st.caption("Clinical-source #2 PIPELINE / #3 PRE3 / #4 POST3 · automatic nightly scan + archived-source integrity check · last published results. FDA, SEC, issuer and full market verification remain separate.")
    render_extended_source_report()

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
        scan_rows = [r for r in report.get("scans", []) if isinstance(r, dict)]
        completed_collectors = [r for r in scan_rows
                                if r.get("collector_status") in ("COMPLETE", "COMPLETE WITH WARNINGS")
                                and r.get("artifact_integrity") == "PASS"]
        if len(scan_rows) == 3 and len(completed_collectors) == 3:
            warnings = sum(r.get("collector_status") == "COMPLETE WITH WARNINGS"
                           for r in completed_collectors)
            st.success(f"Clinical scans #2, #3, #4: 3/3 completed; {warnings} with source warnings. "
                       "Overall PDUFA-source verification remains separate.")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall source coverage", str(report.get("status", "UNVERIFIED")))
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
                "Clinical collector": scan.get("collector_status", "UNVERIFIED"),
                "Overall coverage": scan.get("status", "UNVERIFIED"),
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
    st.divider()
    # Keep the existing read-only Gmail/GitHub audit accessible after the
    # former top-level SCANS page was removed. The function applies its own
    # server-side PIN check and never initiates clinical scans.
    render_adhoc_error_check_controls()

