"""Combined SCANS command center: evidence scores, drilldowns and authenticated scans.

A score means verified/resolved *reported checks*, not FDA approval probability,
trading suitability, or universe completeness. No unknown denominator becomes 100%.
"""
from __future__ import annotations
import hmac
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from scan_status_ui import current_job_steps, recent_github_runs, pacific_time
from gem_scan_block_ui import published_gem_block_report

REPO = "pdufa/pdufa-command-center"
API = "https://api.github.com/repos/" + REPO
RAW = "https://raw.githubusercontent.com/" + REPO + "/main/data/individual_source_scans/"
SOURCE_NAMES = ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER")
SECTIONS = ("PIPELINE", "GEM JR", "GEM", *SOURCE_NAMES, "SCAN HEALTH")
WORKFLOWS = {
    "PIPELINE": "pdufa-individual-clinical-scan.yml",
    "GEM JR": "pdufa-individual-clinical-scan.yml",
    "GEM": "gem-research-quality.yml",
    **{k: "pdufa-individual-source-scan.yml" for k in SOURCE_NAMES},
    "SCAN ALL": "pdufa-overnight-sequential.yml",
    "SCAN HEALTH": "pdufa-adhoc-error-check.yml",
}
ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}
SCOPES = {
    "PIPELINE": "All tracked clinical programs: inventory and linked Phase 2/3 enrichment",
    "GEM JR": "Phase 3 registered trial results and exact-program qualification evidence",
    "GEM": "Phase 3 readouts, second-financing evidence and research gates",
    "FDA": "FDA regulatory decisions, applications, milestones and verified source claims",
    "SEC": "SEC filings, issuer matching, financing closure and dilution evidence",
    "FINANCIAL": "Financing, cash, runway and corresponding source claims",
    "MARKET": "Price/volume, market capitalization and optional options/borrow data",
    "ISSUER": "Issuer announcements, press releases and exact-program evidence",
    "SCAN HEALTH": "Nightly orchestration, actual job execution, source and email checks",
}


def numbers(numerator, denominator):
    try:
        a, b = int(numerator), int(denominator)
        if a < 0 or b <= 0 or a > b:
            return None
        return round(100 * a / b, 1)
    except (TypeError, ValueError, OverflowError):
        return None


def tally_source(source):
    """Always distinguish verified, resolved N/A, missing and optional unavailable."""
    try:
        due = int(source["findings_due"])
        verified = int(source["findings_verified"])
        na = int(source.get("findings_not_applicable") or 0)
    except (KeyError, ValueError, TypeError):
        return None
    if due <= 0 or verified < 0 or na < 0 or verified + na > due:
        return None
    unresolved = due - verified - na
    return {
        "score": numbers(verified + na, due), "due": due, "verified": verified,
        "not_applicable": na, "outstanding": unresolved,
        "required": int(source.get("required_findings_unresolved") or 0),
        "optional": int(source.get("optional_findings_unavailable") or 0),
        "status": str(source.get("status") or "UNVERIFIED"),
    }


def reasons(name, row, source_report=None):
    """Reasons are explanatory, not a guessed attribution."""
    messages = []
    if name in SOURCE_NAMES:
        if row.get("required"):
            messages.append(
                f"{row['required']:,} required findings still need exact source verification."
            )
        if row.get("optional"):
            messages.append(
                f"{row['optional']:,} supplemental checks unavailable; these may need "
                "provider/broker access (for example options IV or borrow data)."
            )
        if row.get("not_applicable"):
            messages.append(f"{row['not_applicable']:,} checks were explicitly not applicable.")
        if row.get("outstanding") and not (row.get("required") or row.get("optional")):
            messages.append(f"{row['outstanding']:,} checks are not yet verified or resolved.")
        if row.get("score") == 100 and "WARNINGS" not in row.get("status", ""):
            messages.append("All reported checks in this section are resolved. This does not prove complete real-world coverage.")
        if "WARNINGS" in row.get("status", ""):
            messages.append("Collector reported source limitations even if required claims passed.")
    else:
        if name == "PIPELINE":
            messages.append("Tracked-trial coverage measures checked saved IDs only; FDA, SEC, financing, issuer and market verification are separate.")
            if row.get("score") is None:
                messages.append("No trustworthy all-universe expected trial total was reported.")
            if source_report and source_report.get("status") != "COMPLETE":
                messages.append("Five-source verification remains PARTIAL; PIPELINE coverage is not end-to-end evidence approval.")
        elif name == "GEM JR":
            messages.append("Registry studies checked and matching Phase 3 results are discovery counts, not a verified denominator for research completion.")
            messages.append("The independent exact-trial/issuer/financing qualification baseline is not fully verified.")
        elif name == "GEM":
            messages.append("Entry-gate qualification is separate from scan completion and is not an FDA approval score.")
            messages.append("Missing or stale Phase 3 readout and independently verified second-financing evidence prevents qualification.")
        elif name == "SCAN HEALTH":
            messages.append("Successful GitHub jobs do not certify completed FDA/SEC evidence or inbox delivery.")
            messages.append("Unknown or incomplete stages cannot be counted as passing.")
    return messages


def collect_cards(clinical, sources, gem, jobs=None, standalone=None, individual_clinical=None):
    cards = []
    scans = {str(s.get("scan")): s for s in (clinical.get("scans") or []) if isinstance(s, dict)}
    scan_scopes = {}
    # Newer individual collectors replace only their section's display,
    # never the archived all-night clinical or five-source aggregate.
    for section, raw in (individual_clinical or {}).items():
        expected = ("2", "3") if section == "PIPELINE" else ("4",)
        if not isinstance(raw, dict) or raw.get("section") != (
            "GEM_JR" if section == "GEM JR" else section
        ) or raw.get("schema_version") != 1:
            continue
        if not _when(raw.get("published_at_utc")) or (
            _when(clinical.get("updated_at_utc")) and
            _when(raw.get("published_at_utc")) <= _when(clinical.get("updated_at_utc"))
        ):
            continue
        report = raw.get("collector_reports") or {}
        if not all(isinstance(report.get(k), dict) and
                   report[k].get("scan") == k for k in expected):
            continue
        for k in expected:
            detail = report[k]
            metrics = {key: value for key, value in detail.items()
                       if isinstance(value, int) and not isinstance(value, bool)}
            scans[k] = {"scan": k, "metrics": metrics, "run_id": raw.get("run_id"),
                        "collector_status": detail.get("collector_status"),
                        "artifact_integrity": "VALIDATED AT INDIVIDUAL PUBLICATION",
                        "status": detail.get("status")}
            scan_scopes[k] = "Newer individual " + section + " run"
    inventory = scans.get("2", {})
    enrichment = scans.get("3", {})
    gm = scans.get("4", {})
    m = inventory.get("metrics") or {}
    checked, total = m.get("tracked_trials_checked"), m.get("tracked_trials_total")
    pscore = numbers(checked, total)
    p = dict(name="PIPELINE", score=pscore, checked=checked, due=total,
             outstanding=(int(total)-int(checked)) if pscore is not None else None,
             status=str(inventory.get("collector_status") or "NOT REPORTED"),
             source_run_id=inventory.get("run_id"),
             details={"Companies checked": m.get("companies_checked"),
                      "Companies due": m.get("companies_due"),
                      "Tracked trials checked": checked,
                      "Total tracked": total,
                      "Enrichment studies examined": (enrichment.get("metrics") or {}).get("studies_checked"),
                      "Enrichment matched trials": (enrichment.get("metrics") or {}).get("matched_trials"),
                      "Collector 2 integrity": inventory.get("artifact_integrity"),
                      "Collector 3 integrity": enrichment.get("artifact_integrity"),
                      "Evidence origin": scan_scopes.get("2", "Last complete nightly clinical report")})
    cards.append(p)
    junior_metrics = gm.get("metrics") or {}
    cards.append(dict(name="GEM JR", score=None,
                      checked=junior_metrics.get("studies_checked"), due=None,
                      outstanding=None, status=str(gm.get("collector_status") or "NOT REPORTED"),
                      source_run_id=gm.get("run_id"),
                      details={"Studies examined": junior_metrics.get("studies_checked"),
                               "Matched posted-result records": junior_metrics.get("matched_posted_results"),
                               "Registered companies": junior_metrics.get("registry_companies"),
                               "Clinical artifact integrity": gm.get("artifact_integrity"),
                               "Evidence origin": scan_scopes.get("4", "Last complete nightly clinical report")}))
    six = gem.get("two_benchmark_candidate_count")
    qualified = gem.get("strict_entry_gate_shortlist_count")
    cards.append(dict(name="GEM", score=None, checked=gem.get("observed_phase3_rows"),
                      due=None, outstanding=None,
                      status=str(gem.get("research_status") or gem.get("status") or "UNVERIFIED"),
                      source_run_id=gem.get("run_id"),
                      details={"Phase 3 rows reviewed": gem.get("observed_phase3_rows"),
                               "Potential two-benchmark candidates": six,
                               "Strict entry-gate qualified": qualified,
                               "Gate pass rate (NOT a scan score)": (
                                   f"{numbers(qualified, six)}%" if numbers(qualified, six) is not None
                                   else "Not measurable"),
                               "Source verification": gem.get("source_verification"),
                               "Blocking flags": ", ".join(str(v) for v in
                                                          gem.get("blocking_or_review_flags", []))}))
    source_rows = {str(s.get("source")): s for s in (sources.get("sources") or []) if isinstance(s, dict)}
    for name in SOURCE_NAMES:
        record = source_rows.get(name, {})
        origin = "Five-source reconciliation"
        # A newer standalone scan has its own verified scope. Never write it
        # into the five-source aggregate, which remains the original run.
        item = (standalone or {}).get(name, {})
        if item and item.get("schema_version") == 1 and item.get("source") == name:
            prior_dt = _when(sources.get("updated_at_utc"))
            new_dt = _when(item.get("published_at_utc"))
            if new_dt and (not prior_dt or new_dt > prior_dt):
                record, origin = item, "Standalone section-only recheck"
        score = tally_source(record)
        if score is None:
            cards.append(dict(name=name, score=None, due=None, checked=None,
                              outstanding=None, status="NO VERIFIED DENOMINATOR",
                              source_run_id=record.get("run_id") or sources.get("latest_run_id"),
                              details={"Scope": origin}))
            continue
        cards.append(dict(name=name, score=score["score"],
                          checked=score["verified"] + score["not_applicable"],
                          due=score["due"],
                          outstanding=score["outstanding"], required=score["required"],
                          optional=score["optional"],
                          not_applicable=score["not_applicable"],
                          status=score["status"],
                          source_run_id=record.get("run_id") or sources.get("latest_run_id"),
                          details={"Evidence scope": origin,
                                   "Verified": score["verified"],
                                   "Not applicable": score["not_applicable"],
                                   "Required unresolved": score["required"],
                                   "Optional unavailable": score["optional"],
                                   "Total checked": score["due"]}))
    valid_jobs = [j for j in (jobs or []) if isinstance(j, dict)
                  and str(j.get("name") or "") not in ("", "Complete job")]
    completed = sum(j.get("status") == "completed" and j.get("conclusion") == "success"
                    for j in valid_jobs)
    hscore = numbers(completed, len(valid_jobs))
    cards.append(dict(name="SCAN HEALTH", score=hscore,
                      checked=completed if valid_jobs else None,
                      due=len(valid_jobs) if valid_jobs else None,
                      outstanding=(len(valid_jobs)-completed) if valid_jobs else None,
                      status="GITHUB EXECUTION ONLY" if valid_jobs else "RUN JOBS NOT AVAILABLE",
                      source_run_id=None,
                      details={"Successful jobs": completed if valid_jobs else None,
                               "Jobs returned": len(valid_jobs) if valid_jobs else None,
                               "Evidence family status": sources.get("status"),
                               "Required source claims unresolved":
                                   sources.get("required_findings_unresolved")}))
    for row in cards:
        row["reasons"] = reasons(row["name"], row, sources)
    return cards


def _when(iso):
    try:
        parsed = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=90, show_spinner=False)
def individual_snapshot(name):
    if name not in SOURCE_NAMES:
        return {}
    url = RAW + name.lower() + ".json"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "pdufa-scan-unified"})
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        try:
            data = json.loads(
                (Path("data/individual_source_scans") / (name.lower() + ".json"))
                .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return data if isinstance(data, dict) and data.get("source") == name else {}


@st.cache_data(ttl=90, show_spinner=False)
def individual_clinical_snapshot(section):
    if section not in ("PIPELINE", "GEM JR"):
        return {}
    name = "gem_jr" if section == "GEM JR" else "pipeline"
    url = ("https://raw.githubusercontent.com/" + REPO +
           "/main/data/individual_clinical_scans/" + name + ".json")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "pdufa-scan-unified"})
        with urllib.request.urlopen(req, timeout=6) as response:
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        try:
            payload = json.loads(
                (Path("data/individual_clinical_scans") / (name + ".json"))
                .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return payload if isinstance(payload, dict) and payload.get("section") == (
        "GEM_JR" if section == "GEM JR" else "PIPELINE") else {}


def workflow_request(section, mode):
    """Strict mapping from UI section to a real collector and its inputs."""
    if section not in WORKFLOWS or mode not in ("DELTA", "FULL"):
        raise ValueError("Invalid scan section or mode")
    if section == "SCAN ALL":
        args = {"scan_mode": mode, "gem_action": (
            "RESCAN_ALL" if mode == "FULL" else "REVERIFY_PARTIAL")}
    elif section in SOURCE_NAMES:
        args = {"source": section, "scan_mode": mode}
    elif section in ("PIPELINE", "GEM JR"):
        args = {"section": "GEM_JR" if section == "GEM JR" else "PIPELINE",
                "scan_mode": mode}
    elif section == "SCAN HEALTH":
        args = {}  # Standalone Gmail/GitHub status audit (not a collector).
    else:
        args = {"action": "RESCAN_ALL" if mode == "FULL" else "REVERIFY_PARTIAL"}
    return WORKFLOWS[section], args


def dispatch_section(section, mode, token):
    if not token:
        raise ValueError("GitHub write token is not configured")
    workflow, inputs = workflow_request(section, mode)
    body = json.dumps({"ref": "main", "inputs": inputs}).encode("utf-8")
    request = urllib.request.Request(
        API + "/actions/workflows/" + workflow + "/dispatches",
        data=body, method="POST", headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "pdufa-unified-scan-center"})
    with urllib.request.urlopen(request, timeout=22) as response:
        if response.status != 204:
            raise RuntimeError("GitHub did not accept the scan request")


def secret(key):
    try:
        return str(st.secrets.get(key, "") or "").strip()
    except (OSError, KeyError, AttributeError):
        return ""


def authorized_controls():
    token, pin = secret("PDUFA_GITHUB_TOKEN"), secret("PDUFA_SCAN_CONTROL_PIN")
    entered = st.text_input("Scan authorization PIN", type="password",
                            key="unified_scan_control_pin")
    known = str(st.session_state.get("filings_scan_control_pin", ""))
    ok = bool(token and pin and (
        hmac.compare_digest(entered.encode(), pin.encode())
        or hmac.compare_digest(known.encode(), pin.encode())))
    if not token or not pin:
        st.warning("Scan dispatch is locked. Configure PDUFA_GITHUB_TOKEN and "
                   "PDUFA_SCAN_CONTROL_PIN in Streamlit secrets. Reports remain visible.")
    elif not ok:
        st.caption("Enter your scan PIN to unlock section and SCAN ALL buttons.")
    return token, ok


def recent_active(runs, section):
    """Avoid double clicks dispatching duplicate queued runs in one session."""
    workflow = WORKFLOWS[section]
    for run in runs:
        if (str(run.get("path") or "").split("/")[-1] == workflow
                and run.get("status") in ACTIVE):
            if section in SOURCE_NAMES:
                if str(run.get("display_title") or "").startswith(section + " —"):
                    return run
            elif section in ("PIPELINE", "GEM JR"):
                expected = "GEM_JR" if section == "GEM JR" else "PIPELINE"
                if str(run.get("display_title") or "").startswith(expected + " —"):
                    return run
            else:
                return run
    return None


def latest_section_run(runs, section):
    """The last matching *requested* section scan, never a different source."""
    if section not in WORKFLOWS:
        return {}
    for run in runs:
        if not isinstance(run, dict) or str(run.get("path") or "").split("/")[-1] != WORKFLOWS[section]:
            continue
        title = str(run.get("display_title") or "")
        if section in SOURCE_NAMES and not title.startswith(section + " —"):
            continue
        if section in ("PIPELINE", "GEM JR") and not title.startswith(
            ("GEM_JR" if section == "GEM JR" else "PIPELINE") + " —"
        ):
            continue
        if section == "SCAN ALL" and (run.get("event") != "workflow_dispatch"
                                      or title != "ALL + GEM — PDUFA overnight"):
            continue
        return run
    return {}


def _print_count(value):
    if value is None:
        return "Not reported"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)


def render_unified_scans(clinical_loader, sources_loader, latest_night_loader):
    """One concise operations scorecard; all underlying research remains intact."""
    st.markdown("## UNIFIED SCANS — CONTROL CENTER")
    st.caption(
        "Each score = resolved / checked evidence for that exact scope. "
        "A successful run is not a verified FDA decision, a valid trading signal "
        "or evidence of complete coverage. Unknown denominators show N/A."
    )
    if st.button("↻ REFRESH SCAN SCORES & LIVE JOB STATUS", key="unified_scans_refresh"):
        recent_github_runs.clear()
        current_job_steps.clear()
        individual_snapshot.clear()
        individual_clinical_snapshot.clear()
        clinical_loader.clear()
        sources_loader.clear()
        st.rerun()
    clinical, note = clinical_loader()
    clinical = clinical if isinstance(clinical, dict) else {}
    sources = sources_loader() or {}
    gem = published_gem_block_report() or {}
    runs, error = recent_github_runs()
    candidates = [x for x in runs if isinstance(x, dict) and
                  str(x.get("path") or "").split("/")[-1] ==
                  "pdufa-overnight-sequential.yml" and
                  x.get("display_title") == "ALL + GEM — PDUFA overnight"]
    latest = (max(candidates, key=lambda x: str(x.get("created_at") or ""))
              if candidates else latest_night_loader() or {})
    # Do not present a clinical-only fallback as the complete ALL + GEM chain.
    if (str(latest.get("path") or "").split("/")[-1] !=
            "pdufa-overnight-sequential.yml"):
        latest = {}
    run_id = latest.get("id")
    jobs = current_job_steps(run_id) if isinstance(run_id, int) else []
    standalone = {name: individual_snapshot(name) for name in SOURCE_NAMES}
    clinical_standalone = {
        "PIPELINE": individual_clinical_snapshot("PIPELINE"),
        "GEM JR": individual_clinical_snapshot("GEM JR"),
    }
    cards = collect_cards(clinical, sources, gem, jobs, standalone, clinical_standalone)
    scoreable = [r for r in cards if r["score"] is not None and r["name"] in SOURCE_NAMES]
    due = sum(r["due"] for r in scoreable)
    cleared = sum(r["due"] - r["outstanding"] for r in scoreable)
    total_pct = numbers(cleared, due)
    required = sources.get("required_findings_due")
    outstanding_required = sources.get("required_findings_unresolved")
    required_pct = (numbers(int(required)-int(outstanding_required), required)
                    if isinstance(required, int) and isinstance(outstanding_required, int) else None)
    # Never combine current stand-alone counts with the original full audit.
    whole_score = (numbers(int(sources.get("findings_verified", 0)) +
                           int(sources.get("findings_not_applicable", 0)),
                           sources.get("findings_due"))
                   if sources.get("findings_due") else None)
    a, b, c, d = st.columns(4)
    a.metric("Five-source resolved score", f"{whole_score:.1f}%" if whole_score is not None else "N/A")
    b.metric("Required verification", f"{required_pct:.1f}%" if required_pct is not None else "N/A")
    c.metric("Required outstanding", _print_count(outstanding_required))
    d.metric("Last full workflow", str(latest.get("status") or "Unknown").replace("_", " ").upper())
    if note:
        st.caption("Clinical report: " + str(note))
    if error:
        st.warning("GitHub run list incomplete: " + str(error))
    st.caption("Five-source score uses ONLY the reconciled five-source report. A newer "
               "standalone source recheck never silently overwrites the aggregate.")
    st.markdown("### Start scans")
    token, authorized = authorized_controls()
    mode = st.radio("Run mode", ["DELTA", "FULL"], index=0, horizontal=True,
                    format_func=lambda x: ("DELTA — new/changed" if x == "DELTA" else
                                           "FULL — refresh entire configured scope"),
                    key="unified_scan_mode")
    running_all = recent_active(runs, "SCAN ALL")
    if st.button("SCAN ALL — PIPELINE → GEM JR → GEM → FDA / SEC / FINANCIAL / MARKET / ISSUER",
                 key="unified_scan_all", use_container_width=True,
                 type="primary", disabled=not authorized or bool(running_all)):
        _submit("SCAN ALL", mode, token, clinical_loader, sources_loader)
    if running_all:
        st.info("A full overnight scan is already queued or running. Open GitHub "
                "to inspect progress before starting another.")
    else:
        st.caption("SCAN ALL runs the existing awaited overnight sequence, "
                   "including source reconciliation, scoring and error checks. "
                   "FULL performs full rechecks; DELTA checks changes.")
    f, g = st.columns([1.3, 1])
    with f:
        focus = st.selectbox("Display section", ["ALL SECTIONS", *SECTIONS],
                             key="unified_scans_section")
    with g:
        status_filter = st.selectbox("Show score", ["ALL", "OUTSTANDING", "100% REPORTED", "NOT MEASURABLE"],
                                     key="unified_scans_score_filter")
    st.markdown("### Section scorecards")
    for card in cards:
        name = card["name"]
        if focus not in ("ALL SECTIONS", name):
            continue
        pct = card["score"]
        if status_filter == "OUTSTANDING" and (pct is None or pct >= 100):
            continue
        if status_filter == "100% REPORTED" and pct != 100:
            continue
        if status_filter == "NOT MEASURABLE" and pct is not None:
            continue
        with st.container(border=True):
            heading, stats, button_col = st.columns([1.75, 1.2, 1])
            with heading:
                st.markdown(f"**{name}**")
                st.caption(SCOPES[name])
                st.caption("Latest report: " + str(card.get("status", "UNVERIFIED")))
            with stats:
                st.metric("Resolved scan score" if pct is not None else "Coverage score",
                          f"{pct:.1f}%" if pct is not None else "N/A")
                if pct is not None:
                    st.progress(min(max(pct/100, 0), 1.0))
                if name in SOURCE_NAMES:
                    st.caption("Available verified: " +
                               _print_count(card.get("details", {}).get("Verified")) +
                               " · Resolved (incl. N/A): " +
                               _print_count(card.get("checked")) + "/" +
                               _print_count(card.get("due")))
                    st.caption("Outstanding: " + _print_count(card.get("outstanding")) +
                               " · Required: " + _print_count(card.get("required")) +
                               " · Supplemental unavailable: " + _print_count(card.get("optional")))
                else:
                    st.caption(
                        "Available checked: " + _print_count(card.get("checked")) +
                        " / " + _print_count(card.get("due")) +
                        " · Outstanding: " + _print_count(card.get("outstanding"))
                    )
            with button_col:
                if name in WORKFLOWS:
                    busy = recent_active(runs, name)
                    last = latest_section_run(runs, name)
                    if st.button(("RUN SCAN HEALTH CHECK" if name == "SCAN HEALTH" else
                                  "RUN " + name + " SCAN"),
                                 key="unified_run_"+name.replace(" ","_"),
                                 disabled=not authorized or bool(busy),
                                 use_container_width=True):
                        _submit(name, mode, token, clinical_loader, sources_loader)
                    if busy:
                        st.caption("Already queued or running")
                    elif name in SOURCE_NAMES:
                        st.caption("Section-only source run")
                    elif name == "SCAN HEALTH":
                        st.caption("Gmail/GitHub error audit only")
                    else:
                        st.caption("Individual clinical/GEM run")
                    if last:
                        conclusion = (str(last.get("conclusion") or "UNKNOWN").upper()
                                      if last.get("status") == "completed"
                                      else str(last.get("status") or "UNKNOWN").upper())
                        st.caption("Latest request: " + conclusion +
                                   " · " + pacific_time(last.get("created_at")))
                        href = last.get("html_url")
                        if isinstance(href, str) and href.startswith(
                            "https://github.com/" + REPO + "/actions/runs/"
                        ):
                            st.link_button("VIEW RUN LOG", href, use_container_width=True)
            if pct is None or pct < 100:
                st.info("WHY NOT 100% — " + " ".join(card["reasons"][:2]))
            with st.expander("WHY NOT 100%? · NUMBERS · SOURCE / OUTSTANDING DETAILS", expanded=False):
                for reason in card["reasons"]:
                    st.write("• " + reason)
                if card.get("score") is None:
                    st.warning("No defensible complete-scope denominator has been published; "
                               "the score is deliberately unavailable, not zero.")
                if card.get("outstanding"):
                    st.warning(f"{int(card['outstanding']):,} items have not been verified or resolved "
                               "within the displayed scope.")
                if card.get("details"):
                    details = [{"Measure": k, "Value": _print_count(v) if isinstance(v, int) else
                                str(v) if v is not None else "Not reported"}
                               for k,v in card["details"].items()]
                    st.dataframe(pd.DataFrame(details), use_container_width=True,
                                 hide_index=True)
                if name in SOURCE_NAMES:
                    matching = [x for x in sources.get("required_issue_examples", [])
                                if str(x.get("category","")).upper().startswith(name)]
                    if matching:
                        st.dataframe(pd.DataFrame(matching), use_container_width=True,
                                     hide_index=True)
                run_number = card.get("source_run_id")
                if run_number and str(run_number).isdigit():
                    st.link_button("OPEN SOURCE RUN #" + str(run_number),
                                   "https://github.com/" + REPO + "/actions/runs/" +
                                   str(run_number))
    st.caption("RUN accepts a GitHub workflow dispatch; it does not declare a scan "
               "complete. The latest individual-source score replaces that source's "
               "card only when its separately published, dated report is newer. "
               "All-source aggregate numbers remain those of the last full reconciliation.")
    st.markdown("### Operational details")
    if latest:
        text = ("**Last full chain:** #" + str(latest.get("id", "Unknown")) +
                " · " + str(latest.get("status") or "UNKNOWN") +
                " · started " + pacific_time(latest.get("created_at")))
        if latest.get("status") == "completed":
            text += " · finished " + pacific_time(latest.get("updated_at"))
        st.write(text)
    if jobs:
        with st.expander("Full-chain job list / failures / timings", expanded=False):
            st.dataframe(pd.DataFrame([{
                "Job": j.get("name"), "Status": j.get("status"),
                "Conclusion": j.get("conclusion"),
                "Started Pacific": pacific_time(j.get("started_at")),
                "Finished Pacific": pacific_time(j.get("completed_at")),
            } for j in jobs]), hide_index=True, use_container_width=True)
    st.caption("Email START/END delivery cannot be established from GitHub workflow "
               "success alone; receipt confirmation remains a separate verification.")


def _submit(name, mode, token, clinical_loader, sources_loader):
    try:
        dispatch_section(name, mode, token)
        recent_github_runs.clear()
        clinical_loader.clear()
        sources_loader.clear()
        individual_snapshot.clear()
        individual_clinical_snapshot.clear()
        st.success(name + " " + mode + " scan requested. GitHub accepted the job; "
                   "refresh status to confirm the actual run and completion.")
    except urllib.error.HTTPError as exc:
        st.error(f"Scan request rejected (HTTP {exc.code}). "
                 "Check the GitHub token's Actions write permission.")
    except (OSError, ValueError, RuntimeError) as exc:
        st.error("Scan request failed: " + type(exc).__name__)
