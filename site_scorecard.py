"""Evidence-based operational site scorecard for the PDUFA Command Center.

Scores only observations that are independently present in the checked-in scan
manifests or the public GitHub Actions API. Missing evidence is UNKNOWN, not PASS.
This measures verified operational checks, not uptime, prediction accuracy, or
security certification.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "pdufa/pdufa-command-center"
WORKFLOWS = (
    "ci.yml",
    "streamlit-validation.yml",
    "live-streamlit-audit.yml",
    "pdufa-nightly-clinical.yml",
    "pdufa-nightly-missing-sources.yml",
    "pdufa-adhoc-error-check.yml",
    "email-delivery-test.yml",
)
BASE = "https://github.com/" + REPO + "/actions/workflows/"
UTC = timezone.utc


def _date(value):
    if not value:
        return None
    try:
        obj = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return obj.replace(tzinfo=UTC) if obj.tzinfo is None else obj.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def recent(value, now, hours):
    parsed = _date(value)
    return parsed is not None and 0 <= (now - parsed).total_seconds() <= hours * 3600


def read_json(path, root="."):
    try:
        with (Path(root) / path).open(encoding="utf-8") as handle:
            obj = json.load(handle)
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _get_workflow(name):
    url = "https://api.github.com/repos/" + REPO + "/actions/workflows/" + name + "/runs?per_page=12"
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "pdufa-site-scorecard",
    })
    try:
        with urlopen(request, timeout=6) as response:
            data = response.read(512001)
        if len(data) > 512000:
            raise ValueError("API response too large")
        rows = json.loads(data).get("workflow_runs", [])
        return {"runs": rows if isinstance(rows, list) else [], "error": ""}
    except (HTTPError, URLError, ValueError, OSError) as exc:
        return {"runs": [], "error": type(exc).__name__}


def fetch_workflow_runs():
    """Collect read-only GitHub workflow metadata without credentials."""
    with ThreadPoolExecutor(max_workers=len(WORKFLOWS)) as pool:
        return dict(zip(WORKFLOWS, pool.map(_get_workflow, WORKFLOWS)))


def _status_workflow(workflow_data, name, now, *, event=None, age_hours=168):
    record = workflow_data.get(name, {})
    if record.get("error"):
        return "UNKNOWN", "GitHub unavailable: " + str(record["error"]), BASE + name
    runs = record.get("runs")
    if runs is None:
        return "UNKNOWN", "No API observations", BASE + name
    relevant = [r for r in runs if r.get("head_branch") == "main"
                and (event is None or r.get("event") == event)]
    if not relevant:
        return "UNKNOWN", "No matching main-branch run", BASE + name
    latest = max(relevant, key=lambda r: str(r.get("created_at", "")))
    observed = str(latest.get("conclusion") or latest.get("status") or "unknown").upper()
    when = latest.get("updated_at") or latest.get("created_at")
    url = str(latest.get("html_url") or BASE + name)
    if not recent(when, now, age_hours):
        return "UNKNOWN", f"{observed}; last run outside {age_hours}h review window", url
    if latest.get("status") != "completed":
        return "UNKNOWN", f"Run still {observed}", url
    if latest.get("conclusion") == "success":
        return "PASS", "Successful workflow run; does not prove data completeness", url
    return "FAIL", "Latest run: " + observed, url


def build_checks(*, root=".", workflows=None, now=None):
    """Return scored checks, fixed denominator of 100 points."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    wf = workflows or {}
    report = read_json("data/nightly_scan_report.json", root)
    status = read_json("data/step7_live_status.json", root)
    checks = []

    def add(category, title, weight, state, detail, evidence=""):
        checks.append({
            "Category": category, "Check": title, "Weight": weight,
            "Status": state, "Earned": weight if state == "PASS" else 0,
            "Evidence": evidence, "Observation": detail,
        })

    for label, path, weight in (
        ("Main application exists", "app.py", 5),
        ("Local smoke test exists", "smoke_test.py", 5),
    ):
        present = (Path(root) / path).is_file()
        add("Application structure", label, weight, "PASS" if present else "FAIL",
            "File present (execution not implied)" if present else "Required file missing", path)

    for name, label, weight, category, event in (
        ("ci.yml", "Main CI run", 8, "CI & deployment", None),
        ("streamlit-validation.yml", "Streamlit validation", 6, "CI & deployment", None),
        ("live-streamlit-audit.yml", "Live browser audit", 6, "CI & deployment", None),
        ("pdufa-nightly-clinical.yml", "Scheduled clinical scan job", 10, "Scan execution", "schedule"),
        ("pdufa-nightly-missing-sources.yml", "Scheduled extended-source scan job", 10, "Scan execution", "schedule"),
        ("pdufa-adhoc-error-check.yml", "On-demand Gmail/GitHub error check", 5, "Alert checks", "workflow_dispatch"),
        ("email-delivery-test.yml", "Gmail SMTP submission test", 5, "Alert checks", "workflow_dispatch"),
    ):
        state, detail, link = _status_workflow(wf, name, now, event=event)
        add(category, label, weight, state, detail, link)

    scans = report.get("scans")
    if scans is None:
        scans = []
    integrity = bool(len(scans) == 3 and
                     {str(x.get("scan")) for x in scans if isinstance(x, dict)} == {"2", "3", "4"} and
                     all(x.get("artifact_integrity") == "PASS" for x in scans if isinstance(x, dict)) and
                     report.get("verification", {}).get("artifact_integrity") == "PASS")
    add("Scan evidence", "Three archived scan artifacts match audit",
        10, "PASS" if integrity else ("FAIL" if report else "UNKNOWN"),
        "Integrity verified for #2/#3/#4; not full-source completeness" if integrity
        else "Missing or incomplete integrity audit", report.get("latest_run_url", ""))

    clean = integrity and all(
        type(s.get("errors_count")) is int and s["errors_count"] == 0
        for s in scans if isinstance(s, dict))
    add("Scan evidence", "Audited clinical scan error counters clear",
        5, "PASS" if clean else ("FAIL" if report else "UNKNOWN"),
        "Zero recorded errors across the three clinical collectors" if clean
        else "Errors or incomplete error counters", report.get("latest_run_url", ""))

    coverage = (report.get("status") == "COMPLETE" and
                report.get("verification", {}).get("all_source_coverage") == "VERIFIED" and
                report.get("missing_required_source_families") == [])
    add("Source coverage", "Independent FDA/SEC/issuer/market source verification",
        15, "PASS" if coverage else ("FAIL" if report else "UNKNOWN"),
        "All required families explicitly verified" if coverage else
        ("Full-source coverage not verified; scan success cannot substitute" if report else "No coverage audit"),
        report.get("latest_run_url", ""))

    add("Freshness", "Latest archived scan report within 36h", 5,
        "PASS" if recent(report.get("updated_at_utc"), now, 36)
        else ("FAIL" if report else "UNKNOWN"),
        str(report.get("updated_at_utc") or "No scan timestamp"), report.get("latest_run_url", ""))

    add("Freshness", "Live source status inventory updated within 36h", 5,
        "PASS" if recent(status.get("generated_at_utc"), now, 36)
        else ("FAIL" if status else "UNKNOWN"),
        str(status.get("generated_at_utc") or "No inventory timestamp"),
        "data/step7_live_status.json")

    assert sum(item["Weight"] for item in checks) == 100
    return checks, report, status


def summarize(checks):
    return {
        "earned": sum(c["Earned"] for c in checks),
        "maximum": sum(c["Weight"] for c in checks),
        "passed": sum(c["Status"] == "PASS" for c in checks),
        "failed": sum(c["Status"] == "FAIL" for c in checks),
        "unknown": sum(c["Status"] == "UNKNOWN" for c in checks),
    }


def render_site_scorecard():
    """Side-by-side diagnostics: operations are never mixed with stock inputs."""
    import streamlit as st
    from score_input_audit import render_score_input_audit

    ops, inputs = st.tabs(["SITE OPERATIONS", "SCORING INPUTS & OVERLAP"])
    with ops:
        render_operational_scorecard()
    with inputs:
        render_score_input_audit()


def render_operational_scorecard():
    import pandas as pd
    import streamlit as st

    st.markdown("## SITE SCORECARD — OPERATIONS & VERIFICATION")
    st.caption("Live evidence-based score for the dashboard itself, not a biotech stock score, "
               "FDA approval probability, uptime percentage, or investment signal.")
    st.info("100 points are available. Only checks with observable PASS evidence earn points. "
            "FAIL and UNKNOWN earn zero; UNKNOWN means not verified, not necessarily broken. "
            "GitHub results refresh about every five minutes.")
    @st.cache_data(ttl=300, show_spinner=False)
    def _fetch():
        return fetch_workflow_runs()

    a, b = st.columns([1, 2])
    with a:
        if st.button("REFRESH SITE SCORE", use_container_width=True, key="site_score_refresh"):
            _fetch.clear()
            st.rerun()
    with b:
        st.link_button("OPEN GITHUB ACTIONS", "https://github.com/" + REPO + "/actions",
                       use_container_width=True)

    checks, report, status = build_checks(workflows=_fetch())
    total = summarize(checks)
    grade = ("A" if total["earned"] >= 90 else "B" if total["earned"] >= 80 else
             "C" if total["earned"] >= 70 else "D" if total["earned"] >= 60 else "F")
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Verified points", f"{total['earned']}/100")
    v2.metric("Provisional grade", grade)
    v3.metric("Checks passed", str(total["passed"]))
    v4.metric("Failed / unknown", f"{total['failed']} / {total['unknown']}")
    st.progress(total["earned"] / 100)
    st.caption("Provisional letter grade reflects verified checks only. It does not certify "
               "production readiness, all-source market coverage, email delivery, or live UI performance.")

    results = pd.DataFrame(checks)
    by_group = results.groupby("Category", sort=False)[["Earned", "Weight"]].sum().reset_index()
    by_group["Points"] = by_group["Earned"].astype(str) + " / " + by_group["Weight"].astype(str)
    st.markdown("### Scoring by system")
    st.dataframe(by_group[["Category", "Points"]], hide_index=True, use_container_width=True)
    st.markdown("### Verification checklist")
    st.dataframe(results[["Category", "Check", "Status", "Earned", "Weight", "Observation", "Evidence"]],
                 hide_index=True, use_container_width=True)
    st.download_button("DOWNLOAD CURRENT SCORECARD CSV",
                       data=results.to_csv(index=False).encode("utf-8"),
                       file_name="pdufa_site_scorecard.csv", mime="text/csv",
                       use_container_width=True)

    st.markdown("### Outstanding source and operational gaps")
    missing = report.get("missing_required_source_families", [])
    if missing:
        st.warning("This scan manifest is PARTIAL. The following sources are not independently verified:")
        for family in missing:
            st.write("• " + str(family))
    else:
        st.caption("No unverified families listed; consult the independent coverage check above.")

    sources = status.get("source_checks", [])
    if sources:
        st.markdown("### Source-status inventory")
        st.dataframe(pd.DataFrame(sources), hide_index=True, use_container_width=True)

    with st.expander("Score interpretation and controls"):
        st.write("Structure: 10; CI and live browser checks: 20; scheduled scans: 20; "
                 "clinical artifact integrity/errors: 15; independent source coverage: 15; "
                 "timestamp freshness: 10; email and error-watch tests: 10.")
        st.write("Successful GitHub Actions jobs do not prove full-source scan completion. "
                 "A successful Gmail test means SMTP submission, not proof of inbox delivery. "
                 "Auto-repair runs are intentionally not credited without verified corrective outcomes. "
                 "Live uptime, response latency, security, and trading performance are not yet measured.")
        st.write("Refresh is a read-only status fetch; it does not start scans, send mail, "
                 "change clinical evidence, or perform repairs.")
