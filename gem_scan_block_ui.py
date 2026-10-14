"""GEMS — fourth read-only SCANS dashboard block beside clinical #2/#3/#4.

Never identify a registry posting with a verified successful Phase 3 readout
or use historical financing mentions to authorize a broker trade.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

REPO = "pdufa/pdufa-command-center"
REPORT_URL = "https://raw.githubusercontent.com/" + REPO + "/main/data/gem_scan_block_report.json"
WORKFLOW = "gem-research-quality.yml"
LABEL = "BLOCK 4 — GEMS"
STAGES = ("Phase 3", "Post-Financing", "PDUFA")


@st.cache_data(ttl=60, show_spinner=False)
def published_gem_block_report():
    request = urllib.request.Request(
        REPORT_URL,
        headers={"User-Agent": "pdufa-command-center-dashboard",
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        try:
            data = json.loads(Path("data/gem_scan_block_report.json").read_text(
                encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return data if valid_gem_report(data) else {}


def valid_gem_report(report):
    return (
        isinstance(report, dict)
        and report.get("schema_version") == 1
        and report.get("scan") == "GEM"
        and report.get("trade_entry_authorized") is False
        and report.get("status") in ("PARTIAL", "FAILED")
        and isinstance(report.get("clinical_registry"), dict)
    )


@st.cache_data(ttl=60, show_spinner=False)
def latest_gem_block_run():
    request = urllib.request.Request(
        "https://api.github.com/repos/" + REPO +
        "/actions/workflows/" + WORKFLOW + "/runs?per_page=1",
        headers={"User-Agent": "pdufa-command-center-dashboard",
                 "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            results = json.load(response).get("workflow_runs")
        return results[0] if isinstance(results, list) and results else {}
    except (OSError, ValueError, TypeError, urllib.error.URLError):
        return {}


def gem_block_summary_row(report):
    """Same report columns as #2/#3/#4, without inventing missing counts."""
    valid = valid_gem_report(report)
    report = report if valid else {}
    clinical = report.get("clinical_registry") or {}
    return {
        "Scan": LABEL,
        "Clinical collector": report.get("collector_status", "NOT PUBLISHED"),
        "Overall coverage": report.get("status", "UNVERIFIED"),
        "Report check": report.get("artifact_integrity", "NOT CHECKED"),
        "Studies checked": clinical.get("studies_checked"),
        "Trials checked": clinical.get("matched_posted_results"),
        "New records": clinical.get("new_records"),
        "Changed trials": None,  # Registry scan does not track this field.
        "Errors": len(report["errors"]) if isinstance(report.get("errors"), list) else None,
        "Run ID": report.get("run_id"),
    }


def report_recent(report, *, now=None):
    try:
        stamp = datetime.fromisoformat(str(report["generated_at_utc"]).replace("Z", "+00:00"))
        now = now or datetime.now(timezone.utc)
        return bool(stamp.tzinfo and 0 <= (now - stamp).total_seconds() <= 48 * 3600)
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def _count(x):
    return f"{x:,}" if type(x) is int else "—"


def render_gem_scan_block_status(report=None, run=None):
    st.markdown("### BLOCK 4 — GEMS · PHASE 3 / POST-FINANCING / PDUFA")
    st.caption("Fourth scan block: same daily automation, PIN-controlled verify/"
               "reverify/full rescan, Github run status, Gmail START/END, archived "
               "reports, and CSV/JSON exports. Existing #4 POST3 stays intact.")
    report = report if valid_gem_report(report) else {}
    run = run if isinstance(run, dict) else {}
    if run.get("status") in ("queued", "in_progress", "waiting", "pending"):
        st.warning("GEMS workflow queued/running. Saved report may describe a prior scan.")
    if not report:
        st.warning("Fourth-block audit not published yet. "
                   "No successful collection or source verification is inferred.")
    else:
        if not report_recent(report):
            st.warning("GEMS published research report is stale or undated. "
                       "No stored ranking is a current entry signal.")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("GEMS source status", report.get("status", "UNVERIFIED"))
        clinical = report["clinical_registry"]
        c2.metric("Registry observations", _count(clinical.get("stored_results")))
        c3.metric("Phase 3 tracking", _count(report.get("verified_phase3_tracking")))
        c4.metric("Awaiting financing #2", _count(report.get("awaiting_second_financing")))
        c5.metric("2-BENCHMARK CANDIDATES",
                  _count(report.get("two_benchmark_candidate_count")))
        st.caption("The primary candidate list requires exactly two verified "
                   "events: published Phase 3 results for the exact trial and "
                   "a second separate post-readout financing close. "
                   "Runway, dilution, market and timing factors rank or warn; "
                   "they do not impose further entry benchmarks. No buy orders.")
        runway = report.get("cash_runway") or {}
        st.caption(
            "SEC runway (12-month advisory ranking threshold): "
            f"{runway.get('source_backed_pass', 0)} pass, "
            f"{runway.get('missing_or_stale', 0)} unverified, "
            f"{runway.get('under_12_months', 0)} below minimum; "
            f"{runway.get('deteriorating', 0)} declining, "
            f"{runway.get('dilution_alerts', 0)} dilution flags. "
            f"SEC runway recheck: {runway.get('collector_status', 'NOT VERIFIED')} "
            f"({runway.get('collected_count', 0)}/{runway.get('target_count', 0)} targeted)."
        )
        hedge = report.get("hedge_fund_13f") or {}
        st.caption(
            "Specialist-manager SEC 13F: "
            f"{hedge.get('managers_complete', 0)}/{hedge.get('managers_targeted', 0)} "
            "selected manager filings collected; "
            f"{hedge.get('matched_programs', 0)} matched GEM rows; "
            f"{hedge.get('with_manager_accumulation', 0)} with increases. "
            f"Status: {hedge.get('collector_status', 'NOT VERIFIED')}. "
            "Quarterly delayed holdings, never a third entry benchmark."
        )
        comparable = report.get("bpw_comparable") or {}
        matrix = comparable.get("capability_matrix")
        if isinstance(matrix, list) and matrix:
            with st.expander("GEM vs BPW — CAPABILITY COMPARISON", expanded=False):
                st.caption(
                    "These are GEM data-coverage measures against BPW's publicly "
                    "described features, not comparisons of proprietary BPW "
                    "approval scores or actual stock returns."
                )
                st.dataframe(pd.DataFrame(matrix)[
                    ["capability", "state", "observed_gem_rows",
                     "total_gem_rows", "data_coverage_pct", "caveat"]
                ], hide_index=True, use_container_width=True)
        else:
            st.caption("GEM vs BPW comparison not yet source-audited in saved scan.")
        st.caption("Last audit " + str(report.get("generated_at_utc") or "unknown") +
                   " · action " + str(report.get("action") or "UNKNOWN") +
                   " · archive integrity " + str(report.get("artifact_integrity") or "NOT CHECKED") +
                   " · all-source / return validation NOT VERIFIED")
        with st.expander("GEMS — detailed audit and research rankings"):
            ranked = report.get("ranked_research_only") or {}
            st.dataframe(pd.DataFrame([
                {"Stage": name, "Research-ranked": ranked.get(name),
                 "Scope": "RESEARCH ONLY — NO TRADE APPROVAL"}
                for name in STAGES
            ]), hide_index=True, use_container_width=True)
            st.write("Collector:", report.get("collector_status", "NOT REPORTED"))
            st.write("Optional conservative research subset:",
                     report.get("strict_entry_gate_shortlist_count", "NOT VERIFIED"))
            st.write("SEC:", (report.get("sec_source_health") or {}).get("status", "UNVERIFIED"))
            st.write("Market:", (report.get("market_source_health") or {}).get("status", "UNVERIFIED"))
            st.write("Blocking source issues:", report.get("blocking_or_review_flags") or "No issues listed")
            st.write("Collector errors:", report.get("errors") or "None reported")
            st.dataframe(pd.DataFrame([
                {"Requirement": name.replace("_", " "),
                 "Status": "PASS" if value else "NOT VERIFIED"}
                for name, value in (report.get("acceptance_checks") or {}).items()
            ]), hide_index=True, use_container_width=True)
            st.download_button(
                "DOWNLOAD GEMS BLOCK 4 AUDIT JSON",
                data=json.dumps(report, indent=2), mime="application/json",
                file_name="pdufa_gems_block4_audit.json", key="gems_block4_audit_json",
            )
        if (report.get("status") == "FAILED" or
                (report.get("sec_source_health") or {}).get("status") != "CURRENT_SOURCE_ONLY"):
            st.warning("Research only — source coverage or SEC financing verification "
                       "is blocked/partial/stale. Even a previously documented second "
                       "close never bypasses the current entry gates.")
        link = report.get("run_url")
        if isinstance(link, str) and link.startswith(
                "https://github.com/" + REPO + "/actions/runs/"):
            st.link_button("VIEW PUBLISHED GEMS SCAN", link)
    if run:
        st.caption("Latest GEMS workflow run #" + str(run.get("id", "?")) +
                   " · " + str(run.get("status", "unknown")) +
                   " · " + str(run.get("conclusion") or "not finished"))
        link = run.get("html_url")
        if isinstance(link, str) and link.startswith(
                "https://github.com/" + REPO + "/actions/runs/"):
            st.link_button("OPEN LATEST GEMS SCAN", link)
    st.link_button("OPEN GEMS WORKFLOW / ARCHIVES",
                   "https://github.com/" + REPO + "/actions/workflows/" + WORKFLOW)
