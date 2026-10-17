"""Source-grounded candidate workbench shared by full-width GEM JR and GEM pages.

The dossier is a research surface. Missing clinical/SEC/market observations are
never converted into qualifications, simulated prices, scores or broker orders.
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_potential_list import build_potential_list
from gem_verified_snapshot import source_cleared_gems
from gem_membership_history import enrich_stage_rows, read_history
from gem_trading_advisory import (
    assess_gem_trade, load_market_rows, render_base_formation_chart,
    render_gem_trade_panel,
)
from gem_scans_ui import _saved_gem_scans, FILES
from gem_master_list import build_gem_master_list
from ticker_toggle_panel import _init_browser_selection, _toggle, clean_ticker
from gem_trade_navigation import open_trade_workspace


def source_date(value):
    """Accept only an unambiguous ISO date; missing values stay missing."""
    try:
        return date.fromisoformat(str(value or "").strip()[:10])
    except (TypeError, ValueError):
        return None


def exact_event(root, program):
    """Fail closed if multiple saved rows share the exact event key."""
    key = str(program or "").strip()
    if not key or key.startswith("TRIAL|"):
        return {}
    matches = []
    try:
        with (Path(root) / "pdufa_candidates.csv").open(
            newline="", encoding="utf-8-sig"
        ) as stream:
            for row in csv.DictReader(stream):
                if str(row.get("event_key") or "").strip() == key:
                    matches.append(row)
                    if len(matches) > 1:
                        return {}
    except (OSError, csv.Error, UnicodeError):
        return {}
    return matches[0] if len(matches) == 1 else {}


def timeline_events(record, event, today):
    """Only exact-program dates; do not infer a financing from a ticker."""
    phase3 = source_date(event.get("phase3_date")) or source_date(record.get("Phase 3 date"))
    first = source_date(record.get("First close"))
    second = source_date(record.get("Second close"))
    pdufa = source_date(event.get("pdufa_date")) or source_date(
        record.get("PDUFA saved") or record.get("PDUFA date (saved)")
    )
    items = [
        ("Phase 3 readout (saved)", phase3),
        ("Financing #1 (SEC source required)", first),
        ("Financing #2 (SEC source required)", second),
        ("PDUFA (date requires independent confirmation)", pdufa),
    ]
    rows = [{
        "Milestone": name, "Saved date": value.isoformat() if value else "NOT AVAILABLE",
        "Days from readout": (value - phase3).days if value and phase3 else None,
    } for name, value in items]
    if phase3 is None:
        status = "Dead zone cannot be calculated: exact-program Phase 3 readout date is missing."
    elif pdufa is None:
        status = f"Post-readout observation: {(today - phase3).days} days; PDUFA end unverified."
    elif pdufa < phase3:
        status = "CONFLICT: saved PDUFA precedes Phase 3. Source correction required."
    elif today <= pdufa:
        status = (
            f"Post-Phase 3 → PDUFA window: {(pdufa - phase3).days} days; "
            f"{(today - phase3).days} days since readout; "
            f"{(pdufa - today).days} days to reported PDUFA."
        )
    else:
        status = "PDUFA passed; historical record. No new pre-event entry."
    return rows, status


def scan_health(root):
    """Display published status verbatim, not a fabricated 'all complete'."""
    result = []
    for label, name in (
        ("Overnight sequence", "nightly_scan_report.json"),
        ("Clinical collectors", "overnight_scan_status.json"),
        ("GEM source checks", "gem_scan_block_report.json"),
    ):
        try:
            report = json.loads((Path(root) / name).read_text(encoding="utf-8"))
            if not isinstance(report, dict):
                raise ValueError("expected object")
            stamp = (report.get("updated_at_utc") or report.get("generated_at_utc")
                     or report.get("finished_at") or "NOT AVAILABLE")
            result.append({
                "Scan": label,
                "Published status": str(report.get("status") or "UNVERIFIED"),
                "Saved update": str(stamp),
                "Coverage": str(
                    (report.get("verification") or {}).get("all_source_coverage")
                    or report.get("artifact_integrity") or "NOT VERIFIED"
                ),
            })
        except (OSError, ValueError, TypeError):
            result.append({
                "Scan": label, "Published status": "UNAVAILABLE",
                "Saved update": "NOT AVAILABLE", "Coverage": "NOT VERIFIED",
            })
    return result


def scan_diagnostics(root, *, now=None):
    """Read-only, source-specific diagnostics for both GEM stage dashboards.

    This is a snapshot of saved reports, not a live execution or a proof of
    full-universe coverage. A child collector may finish while its parent
    scan stays PARTIAL. Missing, corrupt or undated reports fail closed.
    """
    from datetime import datetime, timezone

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Diagnostic clock must include a UTC offset")
    now = now.astimezone(timezone.utc)

    def stamp(value):
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
        except (ValueError, TypeError, OverflowError):
            return None

    def text(value, fallback="NOT VERIFIED"):
        if value is None or value == "":
            return fallback
        if isinstance(value, (dict, list, tuple)):
            return fallback
        return str(value)[:240]

    def link(value):
        url = str(value or "").strip()
        prefix = "https://github.com/pdufa/pdufa-command-center/actions/runs/"
        return url if url.startswith(prefix) and url[len(prefix):].split("/")[0].isdigit() else ""

    def state(raw):
        upper = str(raw or "").strip().upper()
        if any(marker in upper for marker in (
            "FAILED", "FAILURE", "ERROR", "BLOCKED", "STALE", "CANCELLED",
        )):
            return "hold"
        if upper in {"COMPLETE", "COMPLETED", "SUCCESS", "SUCCEEDED", "PASS"}:
            return "pass"
        if any(marker in upper for marker in ("PARTIAL", "HOLD", "WARNING", "REVIEW")):
            return "review"
        return "unknown"

    def child(label, status, *, date="", detail="", errors=None, coverage="SCOPE ONLY"):
        kind = state(status)
        # A finished collector is a scoped observation, never independent
        # clearance of the parent source universe.
        if kind == "pass" and ("SCOPE" in str(coverage).upper() or
                               "SELECTED SOURCES" in str(coverage).upper()):
            kind = "review"
        return {
            "label": text(label), "status": text(status), "type": kind,
            "date": text(date, ""), "detail": text(detail, ""),
            "errors": list(dict.fromkeys(str(v)[:240] for v in (errors or [])
                                            if v is not None))[:10],
            "coverage": text(coverage),
        }

    specs = (
        ("nightly", "Overnight scan sequence", "nightly_scan_report.json"),
        ("clinical", "Clinical collectors", "overnight_scan_status.json"),
        ("gem", "GEM source verification", "gem_scan_block_report.json"),
    )
    rows = []
    for key, label, filename in specs:
        path = Path(root) / filename
        report = None
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("Report is not an object")
            report = loaded
            error = ""
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            error = "Saved report missing or invalid (" + type(exc).__name__ + ")"
        if report is None:
            rows.append({
                "key": key, "label": label, "status": "UNAVAILABLE",
                "type": "unknown", "date": "", "freshness": "UNKNOWN",
                "age_hours": None, "coverage": "NOT VERIFIED",
                "run_url": "", "file": filename, "details": [],
                "issues": [error], "action": "Restore the saved report and inspect SCANS",
                "scope": "Saved reports only",
            })
            continue

        report_time = (report.get("updated_at_utc") or
                       report.get("generated_at_utc") or
                       report.get("finished_at"))
        when = stamp(report_time)
        age = (now - when).total_seconds() / 3600 if when else None
        freshness = ("UNKNOWN" if age is None else
                     "FUTURE DATE" if age < -1 else
                     "STALE" if age > 48 else "CURRENT")
        verified = report.get("verification") or {}
        if not isinstance(verified, dict):
            verified = {}
        if key == "nightly":
            coverage = text(verified.get("all_source_coverage"))
            integrity = text(verified.get("artifact_integrity"))
            issues = [str(x)[:240] for x in (
                report.get("missing_required_source_families") or [])
                if isinstance(x, str)]
            scans = report.get("scans") or []
            details = []
            for r in scans if isinstance(scans, list) else []:
                if not isinstance(r, dict):
                    continue
                metrics = r.get("metrics") if isinstance(r.get("metrics"), dict) else {}
                parts = [str(k).replace("_", " ") + ": " + str(v)
                         for k, v in list(metrics.items())[:4] if v is not None]
                errs = r.get("issues") if isinstance(r.get("issues"), list) else []
                if r.get("errors_count"):
                    parts.append("Reported errors: " + str(r["errors_count"]))
                child_status = (r.get("collector_status") or r.get("status"))
                if r.get("errors_count"):
                    child_status = "REVIEW — RECORDED ERRORS"
                details.append(child(
                    "Scan " + str(r.get("scan") or "?") + " · " + str(r.get("label") or "Collector"),
                    child_status,
                    date=r.get("collected_at_utc"), detail="; ".join(parts),
                    errors=errs, coverage="COLLECTOR SCOPE; global " + coverage,
                ))
            scope = text(report.get("scope"))
            run_url = link(report.get("latest_run_url"))
            if report.get("latest_run_conclusion") is None:
                issues.append("Latest GitHub run conclusion is not confirmed in saved report")
            if integrity != "PASS":
                issues.append("Artifact integrity: " + integrity)
        elif key == "clinical":
            coverage = ("NOT VERIFIED" if report.get("complete") is not True
                        else "COLLECTOR COMPLETE; full sources NOT VERIFIED")
            issues = [str(x)[:240] for x in (
                report.get("missing_required_source_families") or [])
                if isinstance(x, str)]
            checks = report.get("source_checks") or {}
            details = []
            if isinstance(checks, dict):
                for name, r in checks.items():
                    if not isinstance(r, dict):
                        continue
                    errs = r.get("errors") if isinstance(r.get("errors"), list) else []
                    child_status = r.get("status")
                    if errs or (r.get("exit_code") not in {0, None}):
                        child_status = "REVIEW — RECORDED ERRORS"
                    details.append(child(
                        str(name).replace("_", " ").title(),
                        child_status, date=r.get("finished_at"),
                        detail=text(r.get("source_scope"), ""),
                        errors=errs,
                        coverage="COLLECTOR SCOPE; full source verification not established",
                    ))
            scope = "Saved clinical registry and pipeline collectors"
            run_url = ""
        else:
            coverage = text(report.get("source_verification"))
            issues = [str(x)[:240] for x in (
                report.get("blocking_or_review_flags") or [])
                if isinstance(x, str)]
            errors = report.get("errors") if isinstance(report.get("errors"), list) else []
            issues.extend(str(x)[:240] for x in errors if x is not None)
            details = []
            for key_name, display in (
                ("sec_source_health", "SEC financing source"),
                ("market_source_health", "Market source"),
                ("insider_form4", "Insider Form 4"),
                ("hedge_fund_13f", "Institutional 13F"),
                ("cash_runway", "Cash / runway"),
            ):
                part = report.get(key_name) or {}
                if not isinstance(part, dict):
                    continue
                raw = part.get("status") or part.get("collector_status") or "UNVERIFIED"
                if key_name == "cash_runway":
                    raw = "PARTIAL" if part.get("missing_or_stale") else "UNVERIFIED"
                selected = [
                    str(k).replace("_", " ") + ": " + str(v)
                    for k, v in list(part.items())[:7]
                    if k not in {"status", "collector_status"} and
                    not isinstance(v, (dict, list)) and v is not None
                ]
                details.append(child(display, raw,
                                     detail="; ".join(selected),
                                     coverage="SELECTED SOURCES ONLY"))
            acceptance = report.get("acceptance_checks") or {}
            if isinstance(acceptance, dict):
                for k, v in acceptance.items():
                    if not isinstance(v, bool):
                        continue
                    details.append(child(
                        "Verification · " + str(k).replace("_", " "),
                        "PASS" if v else "NOT VERIFIED",
                        detail="Saved acceptance check; not a live recheck",
                        coverage="EXPLICIT SAVED CHECK ONLY",
                    ))
                    if not v:
                        issues.append("Unmet verification: " + str(k).replace("_", " "))
            scope = "GEM research-only source checks; no trading authorization"
            run_url = link(report.get("run_url"))

        status = text(report.get("status") or "UNVERIFIED")
        status_type = state(status)
        if freshness == "STALE" and status_type != "hold":
            status_type = "hold"
        if coverage.upper() not in {"VERIFIED", "COMPLETE", "FULLY VERIFIED"}:
            if status_type == "pass":
                status_type = "review"
        if freshness in {"UNKNOWN", "FUTURE DATE"} and status_type == "pass":
            status_type = "review"
        if freshness == "STALE":
            issues.insert(0, "Saved report is older than 48 hours; current status is unknown")
        if freshness == "FUTURE DATE":
            issues.insert(0, "Report timestamp is in the future; verify clock and artifact")
        if freshness == "UNKNOWN":
            issues.insert(0, "Saved report timestamp is missing or invalid")
        rows.append({
            "key": key, "label": label, "status": status,
            "type": status_type, "date": text(report_time, ""),
            "freshness": freshness,
            "age_hours": round(age, 1) if age is not None else None,
            "coverage": coverage, "run_url": run_url, "file": filename,
            "details": details, "issues": list(dict.fromkeys(issues))[:30],
            "action": "Open SCANS for live runs, failed steps and source recovery",
            "scope": scope,
        })
    return rows


def _display(value):
    text = str(value if value is not None else "").strip()
    return text if text and text.lower() not in {"nan", "nat", "none", "<na>"} else "NOT VERIFIED"


def _urls(record, event):
    fields = (
        ("Clinical primary source", record.get("Phase 3 source") or
         record.get("Clinical source") or event.get("trial_evidence_url")),
        ("Financing #1 SEC evidence", record.get("First SEC source")),
        ("Financing #2 SEC evidence", record.get("Second SEC source") or
         record.get("Financing SEC source")),
        ("PDUFA primary source", event.get("pdufa_evidence_url")),
    )
    return [(label, url.strip()) for label, url in fields
            if isinstance(url, str) and url.strip().startswith("https://")]


def _master_row(root, record, day):
    """Exact event AND ticker match only, never cross-program financing joins."""
    path = Path(root)
    signature = tuple(
        (name, (path / name).stat().st_mtime_ns if (path / name).exists() else 0)
        for name in FILES
    )
    items, status = _saved_gem_scans(str(path), signature, day)
    key = str(record.get("Exact program") or "")
    ticker = clean_ticker(record.get("Ticker"))
    rows = [row for row in build_gem_master_list(items)
            if str(row.get("Exact Program / Event") or "") == key
            and clean_ticker(row.get("Ticker")) == ticker]
    return (rows[0] if len(rows) == 1 else None), status


def render_stage_dossier(stage, root="data"):
    """Interactive per-program drilldown on the stage's full-width page."""
    junior = stage == "GEM JR"
    if stage not in ("GEM JR", "GEM"):
        raise ValueError("Unknown GEM stage")
    st.markdown("### CANDIDATE WORKBENCH — SOURCE DATA, CHARTS & TRADE REVIEW")
    st.caption("Select an exact Pipeline program. W saves Watchlist; T opens the "
               "existing WT trading-research workspace. Neither places an order.")
    _init_browser_selection("dossier_" + ("jr" if junior else "gem"))
    if junior:
        active, held = build_potential_list(root)
        cleared, historical, _ = source_cleared_gems(root)
        cleared_ids = {str(x.get("Pipeline ID") or "") for x in cleared + historical}
        active = [r for r in active if str(r.get("Pipeline ID") or "") not in cleared_ids]
        active = enrich_stage_rows(active, "GEM_JR", read_history(root))
    else:
        active, historical, _ = source_cleared_gems(root)
        active = enrich_stage_rows(active, "GEM", read_history(root))
        held = historical
    a, b, c = st.columns(3)
    a.metric("Active exact programs", len(active))
    b.metric("Historical / held", len(held))
    c.metric("Broker orders from this page", "NONE")
    if not active:
        st.info("No active exact-program candidates qualified for this stage in "
                "the saved evidence. No demonstration tickers have been inserted.")
    else:
        keys = list(range(len(active)))
        choice = st.selectbox(
            "Select exact company / drug / indication",
            keys, format_func=lambda i: (
                _display(active[i].get("Ticker")) + " · " +
                _display(active[i].get("Drug")) + " · " +
                _display(active[i].get("Indication")) + " · " +
                _display(active[i].get("NCT ID"))),
            key="dossier_select_" + ("jr" if junior else "gem"),
        )
        record = active[choice]
        ticker = clean_ticker(record.get("Ticker"))
        event = exact_event(root, record.get("Exact program"))
        w, t, heading = st.columns([1, 1, 7], vertical_alignment="center")
        with w:
            watch = ticker in {clean_ticker(v) for v in st.session_state.get("watchlist", [])}
            st.button("W", help="Add/remove " + ticker + " from Watchlist",
                      type="primary" if watch else "secondary",
                      key="dossier_w_" + stage, on_click=_toggle, args=(ticker, "watch"))
        with t:
            st.button("T", help="Open WT trading review for " + ticker + "; no order",
                      key="dossier_t_" + stage, on_click=open_trade_workspace,
                      args=(ticker,))
        with heading:
            st.markdown("**" + ticker + " · " + _display(record.get("Drug")) +
                        " · " + _display(record.get("Indication")) + "**")
            st.caption("Exact Pipeline ID: " + _display(record.get("Pipeline ID")) +
                       " · NCT: " + _display(record.get("NCT ID")))

        info, dates = st.columns(2)
        with info:
            st.markdown("**Clinical / financial evidence**")
            st.dataframe(pd.DataFrame([
                {"Check": "Phase 3 results", "Saved observation": _display(
                    record.get("Phase 3 status") or record.get("Evidence type"))},
                {"Check": "Published p-value (not independent verification)",
                 "Saved observation": _display(event.get("reported_p_values"))},
                {"Check": "Approval probability (saved estimate; not verified)",
                 "Saved observation": _display(event.get("approval_probability"))},
                {"Check": "Cash / market cap (saved)", "Saved observation":
                 _display(event.get("cash")) + " / " + _display(event.get("market_cap"))},
                {"Check": "Short interest / float (saved)", "Saved observation":
                 _display(event.get("short_interest")) + " / " +
                 _display(event.get("shares_float"))},
                {"Check": "Dilution / warrants", "Saved observation":
                 _display(event.get("new_dilution_flag")) +
                 " / WARRANTS NOT IN VERIFIED FEED"},
                {"Check": "Missing source reviews", "Saved observation":
                 _display(record.get("Still needed"))},
            ]), use_container_width=True, hide_index=True)
            st.markdown("**Dated source links**")
            links = _urls(record, event)
            if links:
                for label, url in links:
                    st.link_button(label, url)
            else:
                st.warning("No verified source URLs attached to this exact program.")
        with dates:
            rows, timing = timeline_events(
                record, event, datetime.now(ZoneInfo("America/Los_Angeles")).date())
            st.markdown("**Phase 3 → financing → PDUFA / dead-zone timeline**")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(timing)
            if junior:
                st.warning("GEM JR is an unqualified research queue. Phase 3 "
                           "claims and financing leads cannot clear GEM benchmarks.")
            else:
                st.success("Two program-level benchmarks were source-cleared in "
                           "the saved records; fresh SEC and trading checks "
                           "are still required before any order.")
            st.warning("PDUFA exit policy and broker hard-stop hierarchy "
                       "are NOT finalized. Saved PDUFA −3 is a research "
                       "warning, not an automatic exit.")

        with st.expander("PRICE BASE • SMA20 / SMA50 • RSI • MACD • RVOL • RISK GAPS",
                         expanded=True):
            day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
            market = load_market_rows(root)
            if junior:
                profile = assess_gem_trade(
                    {"Ticker": ticker, "_eligible": False}, market, {}, day)
                render_base_formation_chart(profile)
                st.caption(profile["reason"] + " · Latest verified EOD: " +
                           _display(profile["date"]))
                st.info("Entry score: UNAVAILABLE — GEM JR has not cleared GEM "
                        "qualification. Exit-risk signals are research warnings only.")
                st.caption("Missing technical / trade inputs: " + profile["gaps"])
            else:
                try:
                    master, status = _master_row(root, record, day)
                except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
                    master, status = None, {}
                if master is not None:
                    render_gem_trade_panel(master, market, status, day)
                else:
                    st.error("Exact scored GEM row unavailable or ambiguous. "
                             "No entry/exit score or verified chart is inferred.")
        with st.expander("NEWS / FDA / SEC / DILUTION — REVIEW QUEUE", expanded=False):
            st.caption("Use dated clinical, SEC and FDA links above and the "
                       "existing SCANS and WT pages for source checks, alerts "
                       "and paper/live account configuration. News / dilution "
                       "not present in the saved program is NOT VERIFIED.")
            st.markdown("**Outstanding review:** " + _display(record.get("Still needed")))
    with st.expander("SCANNER HEALTH — SAVED REPORTS (10 PM PACIFIC CHAIN)", expanded=False):
        st.dataframe(pd.DataFrame(scan_health(root)),
                     use_container_width=True, hide_index=True)
        st.caption("Published report status may lag a running workflow. Open "
                   "SCANS for live job IDs, errors, manual rechecks and reports; "
                   "a completed collector does not establish full source coverage.")
