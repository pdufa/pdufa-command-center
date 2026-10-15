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
from gem_scan_block_ui import (published_gem_block_report, latest_gem_block_run,
                               gem_block_summary_row, render_gem_scan_block_status)
from scan_status_ui import render_scan_status, required_issue_queue
from scripts.scan_recovery_triage import triage_source_rows
from sec_search_discovery import financing_discovery_links
from scripts.pdufa_morning_results import make_snapshot
import scripts.pdufa_morning_results as morning_results_module

REPO = "pdufa/pdufa-command-center"
REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/nightly_scan_report.json"
SOURCE_REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/pdufa_source_report.json"
API = "https://api.github.com/repos/" + REPO
WORKFLOW = "pdufa-scan-control.yml"
AM_REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/pdufa_am_6am_results.json"
LABELS = {"2": "PIPELINE · trial inventory", "3": "PIPELINE · clinical enrichment",
          "4": "GEM JR · Phase 3 readout", "PIPELINE": "PIPELINE",
          "GEM_JR": "GEM JR", "GEM": "GEM"}


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
        "Read-only summary of the previous day's 1:00 PM clinical, FDA, SEC, "
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
            clinical, published_source_report(), gem=published_gem_block_report(), now=now
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
    gem = report.get("gem") or {}
    if gem.get("overnight_report_published"):
        st.caption(
            "BLOCK 4 — GEM: " + str(gem.get("status", "PARTIAL")) +
            " · Phase 3 posted results stored: " +
            _number(gem.get("stored_results")) +
            " · verified Phase 3 tracking: " +
            _number(gem.get("verified_phase3_tracking")) +
            " · awaiting second financing: " +
            _number(gem.get("awaiting_second_financing")) +
            " · ALL ENTRY GATES: " +
            _number(gem.get("strict_entry_gate_shortlist_count")) +
            " · MANUAL REVIEW ONLY — NO TRADE APPROVAL"
        )
    else:
        st.caption("BLOCK 4 — GEM: latest overnight audit PENDING / STALE; "
                   "no new results or trade eligibility inferred.")
    gem_run_url = gem.get("run_url") if gem.get("overnight_report_published") else None
    if isinstance(gem_run_url, str) and gem_run_url.startswith(
            "https://github.com/" + REPO + "/actions/runs/"):
        st.link_button("OPEN OVERNIGHT GEM SCAN", gem_run_url)
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
        rows.append({
            "Scan": LABELS["GEM"],
            "Status": gem.get("status") if gem.get("overnight_report_published") else "PENDING_OR_STALE",
            "New records": gem.get("new_records") if gem.get("overnight_report_published") else None,
            "Changed trials": None,
        })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)



    # A late source reconciliation must not rewrite the immutable 6 AM
    # evidence cutoff. Show it as a SEPARATE, source-matched publication.
    clinical_latest, _ = published_report()
    # Streamlit Cloud may hot-reload the dashboard module before it refreshes
    # the imported morning helper. Missing optional post-6AM support must not
    # crash the entire PDUFA app while the deployment catches up.
    post_six = getattr(morning_results_module, "post_six_final_status", None)
    if not callable(post_six):
        import importlib
        try:
            importlib.reload(morning_results_module)
        except (ImportError, OSError, KeyError, SyntaxError):
            pass
        post_six = getattr(morning_results_module, "post_six_final_status", None)
    late = (post_six(clinical_latest, published_source_report(), now=now)
            if callable(post_six) else None)
    if not callable(post_six):
        st.caption("Post-6AM final report is waiting for Cloud deployment synchronization.")
    if late:
        st.markdown("### LATEST COMPLETED OVERNIGHT CHECK — AFTER 6 AM")
        st.caption(
            "New evidence became available after the 6 AM cutoff. "
            "This is not the 6 AM snapshot and does not authorize trading."
        )
        st.write(
            "Nightly GitHub run #" + str(late["run_id"]) +
            " · Source verification: **" + late["status"] + "**" +
            " · Source published (Pacific): " + late["source_published_pacific"]
        )
        pending = late.get("required_unresolved")
        st.metric("Required findings still unresolved",
                  f"{pending:,}" if type(pending) is int else "Unknown")
        if late["status"] != "COMPLETE" or pending is None or pending > 0:
            st.warning(
                "Source verification remains incomplete. Missing source evidence "
                "is not a pass; GEM trading stays blocked."
            )
        missing = late.get("missing_required_source_families") or []
        if missing:
            st.caption("Incomplete source families: " + ", ".join(str(s) for s in missing))
        if late.get("run_url"):
            st.link_button("OPEN COMPLETED OVERNIGHT WORKFLOW", late["run_url"])


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
    # Existing nightly SEC/FDA/ISSUER/FINANCIAL collectors make the next
    # primary-source rechecks. Show diagnostic actions for every unresolved
    # exact event, not only the top 24 examples in the JSON summary.
    st.markdown("### AUTOMATIC RECOVERY / EXCEPTION QUEUE")
    st.caption(
        "Rechecks run with the next scheduled source scan; eligible temporary "
        "CI failures may be retried once. Clinical, SEC and code disagreements "
        "are diagnosed, not automatically rewritten or approved for trading."
    )
    source_queue, queue_notice = required_issue_queue()
    source_recovery = triage_source_rows(
        source_queue.to_dict(orient="records"), report
    )
    if queue_notice:
        st.warning(queue_notice)
    queue_status = source_recovery.get("status", "INCOMPLETE_OR_STALE_QUEUE")
    if queue_status != "READY_FOR_NEXT_NIGHT_RECHECK":
        st.warning(
            "Recovery queue incomplete or not synchronized with the published "
            "source report. No outstanding source is auto-cleared."
        )
    breakdown = source_recovery.get("counts_by_action") or {}
    m1, m2, m3 = st.columns(3)
    m1.metric("Unresolved claims in recovery queue",
              source_recovery.get("findings_count", 0))
    m2.metric("SEC financing claims to recheck",
              breakdown.get("RECHECK_CIK_MATCHED_SEC_FINANCING", 0))
    m3.metric("Conflicting primary evidence on hold",
              breakdown.get("HOLD_CONFLICT_AND_RECHECK_PRIMARY", 0))
    if breakdown:
        with st.expander("Source-recheck actions and outstanding evidence"):
            st.dataframe(
                pd.DataFrame([
                    {"Next automatic check": action.replace("_", " ").title(),
                     "Pending": count}
                    for action, count in sorted(breakdown.items())
                ]), use_container_width=True, hide_index=True
            )
            items = source_recovery.get("items") or []
            st.dataframe(
                pd.DataFrame(items).reindex(columns=[
                    "ticker", "event_key", "category", "claim",
                    "verification_status", "priority", "next_scan_action",
                    "reason", "gem_trade_entry",
                ]), use_container_width=True, hide_index=True
            )
    st.caption(
        "Code-test failures remain manual-review holds unless a verified "
        "transient network error qualifies for one failed-job retry. "
        "See the nightly scoring → error check → safe repair workflow artifacts."
    )
    st.link_button(
        "VIEW NIGHTLY SCORING AND SELF-RECOVERY",
        "https://github.com/" + REPO +
        "/actions/workflows/pdufa-nightly-scoring-then-repair.yml"
    )
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
    # Search engines expose additional SEC leads but can never clear a source
    # alert themselves. The exact CIK comes from the saved company registry.
    with st.expander("SEARCH MISSING SEC FINANCING: YAHOO / BING / GOOGLE"):
        st.caption(
            "Search the original SEC archive for an unresolved company. "
            "A Yahoo Finance article may suggest a date. Only a freshly "
            "fetched, company-matched SEC document confirming that dated "
            "completed transaction can clear its SEC evidence claim."
        )
        unresolved_sec = sorted({
            str(row.get("ticker") or "").upper().strip()
            for row in source_queue.to_dict(orient="records")
            if row.get("category") == "SEC" and row.get("ticker")
        })
        registry_path = Path("data/company_registry.csv")
        try:
            registry = pd.read_csv(registry_path, dtype=str, keep_default_na=False)
            issuer_map = {
                str(r["ticker"]).upper(): r
                for r in registry.to_dict(orient="records")
            }
        except (OSError, KeyError, ValueError, pd.errors.ParserError) as exc:
            st.warning(
                "Company registry unavailable: " + type(exc).__name__ +
                ". No unvalidated company lookup is permitted."
            )
            issuer_map = {}
        options = [t for t in unresolved_sec if t in issuer_map]
        if not options:
            st.info("No unresolved SEC claims with a matched issuer registry CIK.")
        else:
            chosen_ticker = st.selectbox(
                "Unresolved issuer", options, key="scans_sec_discovery_ticker"
            )
            chosen_form = st.selectbox(
                "Look for SEC document", ("8-K", "10-Q", "10-K", "EX-99.1", "EX-10"),
                key="scans_sec_discovery_form",
            )
            company = issuer_map[chosen_ticker]
            try:
                links = financing_discovery_links(
                    chosen_ticker, company["company"], company["cik10"], chosen_form
                )
            except (ValueError, KeyError) as exc:
                st.warning("Cannot create exact-issuer SEC search: " + str(exc))
            else:
                buttons = st.columns(4)
                for col, (label, url) in zip(buttons, links.items()):
                    with col:
                        st.link_button(label, url, use_container_width=True)
                st.caption(
                    "Search results are discovery only. Open sec.gov, check the "
                    "issuer CIK, explicit close date, transaction and proceeds; "
                    "the verified source ledger must be refreshed before deleting alerts."
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
    for workflow in ("pdufa-overnight-sequential.yml", "pdufa-nightly-clinical.yml"):
        request = urllib.request.Request(
            API + "/actions/workflows/" + workflow + "/runs?branch=main&per_page=10",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "pdufa-command-center-dashboard"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.load(response)
            for run in data.get("workflow_runs") or []:
                if (workflow != "pdufa-overnight-sequential.yml" or
                        run.get("display_title") == "ALL + GEM — PDUFA overnight"):
                    return run
        except (ValueError, OSError, urllib.error.URLError):
            continue
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
    if scan not in {"ALL", "PIPELINE", "GEM_JR", "GEM"}:
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
                   (" for " + LABELS.get(scan, scan) if scan != "ALL" else " for PIPELINE → GEM JR → GEM") +
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
        "Checks automatically after completed nightly clinical, FDA/SEC, report and PIPELINE clinical feed refreshes. "
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
    # required evidence gaps, existing GEM, and manual controls.
    st.markdown("### GEMS — GITHUB SCAN LOGS")
    direct_gem, finance_gem = st.columns(2)
    with direct_gem:
        st.link_button(
            "GEMS PHASE 3 / RESEARCH SCAN ↗",
            "https://github.com/" + REPO +
            "/actions/workflows/gem-research-quality.yml",
            use_container_width=True,
        )
    with finance_gem:
        st.link_button(
            "GEMS FINANCING AUDIT SCAN ↗",
            "https://github.com/" + REPO +
            "/actions/workflows/gem-financing-full-coverage.yml",
            use_container_width=True,
        )
    render_am_results()
    st.divider()
    render_scan_status(published_source_report)
    st.divider()
    render_gem_scans()
    st.divider()
    st.markdown("## NIGHTLY SCAN REPORT")
    st.caption("Three qualification stages: PIPELINE / GEM JR / GEM. Three underlying clinical collectors still preserve their separate evidence audits; verify/recheck/rescan targets are consolidated. A finished workflow is not full FDA, SEC, issuer or market verification.")
    render_extended_source_report()

    report, loading_note = published_report()
    running = latest_run()
    gem_report = published_gem_block_report()
    gem_running = latest_gem_block_run()
    if loading_note:
        st.info(loading_note)
    if running and running.get("status") in ("queued", "in_progress", "waiting", "pending"):
        st.warning("Scan workflow run #" + str(running.get("id")) + " is " +
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
            st.success(f"PIPELINE + GEM JR clinical collectors: 3/3 completed; {warnings} with source warnings. "
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
        rows.append(gem_block_summary_row(gem_report))
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

    render_gem_scan_block_status(gem_report, gem_running)
    st.markdown("### Scan controls")
    st.link_button("OPEN SCAN CONTROLS IN GITHUB ACTIONS",
                   "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-scan-control.yml")
    st.caption("VERIFY ALL audits the three preserved clinical collectors and GEM source gates. REVERIFY PARTIAL rechecks selected stages; RESCAN ALL requests both PIPELINE collectors, GEM JR readouts and GEM full registry research. No action certifies trading readiness or executes an order.")
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
    scan_choice = st.selectbox("Target one scan block",
                               options=["PIPELINE", "GEM_JR", "GEM"],
                               format_func=lambda x: LABELS[x],
                               key="nightly_target_scan")
    target_reverify, target_verify, target_rescan = st.columns(3)
    with target_reverify:
        if st.button("REVERIFY SELECTED", disabled=not authorized,
                     use_container_width=True, key="nightly_reverify_selected"):
            _run_request("REVERIFY_PARTIAL", scan_choice, token)
    with target_verify:
        if st.button("VERIFY SAVED SOURCES", disabled=not authorized,
                     use_container_width=True, key="nightly_verify_selected"):
            _run_request("VERIFY_ALL", scan_choice, token)
    with target_rescan:
        if st.button("RESCAN SELECTED", disabled=not authorized,
                     use_container_width=True, key="nightly_rescan_selected"):
            _run_request("RESCAN_ALL", scan_choice, token)
    st.caption("VERIFY SAVED SOURCES audits all preserved clinical artifacts for PIPELINE or GEM JR; GEM uses its own saved-source audit. REVERIFY and RESCAN use the selected stage. All requests run on GitHub Actions: acceptance is not completion.")
    st.divider()
    # Keep the existing read-only Gmail/GitHub audit accessible after the
    # former top-level SCANS page was removed. The function applies its own
    # server-side PIN check and never initiates clinical scans.
    render_adhoc_error_check_controls()

