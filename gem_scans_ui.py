"""Read-only Streamlit GEM scanner surface inside the existing SCANS sub-tab."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_scans import SCAN_QUALIFIERS, STAGES, WEIGHTS, build_gem_scans
from gem_phase3_discovery import DISCOVERY_COLUMNS, discover_phase3_results, gem_discrimination_audit
from gem_readiness_audit import build_readiness_report
from gem_calibration_ui import render_gem_calibration

FILES = (
    "pdufa_candidates.csv",
    "step7_live_status.json",
    "step7_financing_review.csv",
    "second_financing_status.csv",
    "step7_market_status.csv",
    "step7_pre_phase3_feed.csv",
    "post_phase3_discoveries.csv",
    "phase3_announcements.csv",
)
STAGE_COLUMNS = {
    "Phase 3": (
        "Phase 3 evidence", "Clinical evidence /30", "Trading setup /20",
        "Market activity /10", "NCT ID", "Phase 3 source",
        "Days to PDUFA",
    ),
    "Post-Financing": (
        "2nd Financing Completed", "Financing #2", "Financing evidence /20",
        "Trading setup /20", "Market activity /10", "Financing source",
        "Days to PDUFA",
    ),
    "PDUFA": (
        "PDUFA verification", "Days to PDUFA", "PDUFA date",
        "PDUFA evidence /15", "Clinical evidence /30",
        "Financing evidence /20", "PDUFA source",
    ),
}


@st.cache_data(ttl=120, show_spinner=False)
def _saved_gem_scans(root, signature, pacific_day):
    # Source file signature, plus local calendar day, prevents a cached
    # "current" rating from surviving an updated feed or Pacific midnight.
    return build_gem_scans(root, as_of=pacific_day)


@st.cache_data(ttl=120, show_spinner=False)
def _discovery(root, signature, pacific_day):
    return discover_phase3_results(root, as_of=pacific_day)


def _gems_table(items):
    """Accessible, escaped two-row GEMS header with its three subcolumns."""
    style = """<style>
    .gems-scroll {overflow-x:auto;border:2px solid #161616;border-radius:8px;background:#fff}
    .gems-table {border-collapse:collapse;width:100%;min-width:640px;font-size:13px;color:#101010}
    .gems-table th,.gems-table td {border:1px solid #999;padding:7px 9px;text-align:center;white-space:nowrap}
    .gems-table thead th {background:#e7f5e9;color:#111;font-weight:800}
    .gems-table thead tr:first-child th:first-child {background:#196b42;color:#fff}
    .gems-table td.ticker {font-weight:800}
    .gems-table td.ranked {color:#08652e;font-weight:800}
    </style>"""
    header = (
        '<div class="gems-scroll"><table class="gems-table">'
        '<thead><tr><th colspan="3">GEMS</th>'
        '<th rowspan="2">Ticker</th><th rowspan="2">Drug / program</th>'
        '</tr><tr><th>Phase 3</th><th>Post-Financing</th><th>PDUFA</th>'
        '</tr></thead><tbody>'
    )
    rows = []
    for item in items:
        cells = []
        for stage in STAGES:
            value = str(item.get(stage + " GEM", "—"))
            cls = ' class="ranked"' if value != "—" else ""
            cells.append(f"<td{cls}>{html.escape(value)}</td>")
        ticker = html.escape(str(item.get("Ticker") or ""))
        drug = html.escape(str(item.get("Drug") or ""))
        rows.append("<tr>" + "".join(cells) +
                    f'<td class="ticker">{ticker}</td><td>{drug}</td></tr>')
    return style + header + "".join(rows) + "</tbody></table></div>"


def render_gem_scans(root="data"):
    st.markdown("## 💎 GEMS — PHASE 3 / POST-FINANCING / PDUFA")
    st.caption(
        "Three independent source-gated research rankings. Each entry shows "
        "#rank (evidence score /100) in its own classification. GEMS is nested "
        "over three columns immediately before Ticker. Research scores are "
        "NOT FDA approval probabilities, return forecasts, or entry approval."
    )
    path = Path(root)
    signature = tuple(
        (name, (path / name).stat().st_mtime_ns if (path / name).exists() else 0)
        for name in FILES
    )
    day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        items, status = _saved_gem_scans(str(path), signature, day)
    except (OSError, ValueError, TypeError, KeyError, pd.errors.ParserError):
        st.error("GEM scan source load failed; no stocks were qualified or scored.")
        return

    if not status.get("feed_current"):
        st.warning(
            "SOURCE SNAPSHOT STALE: no GEM score or rank may be issued until "
            "the saved clinical, financing and market evidence is refreshed."
        )
    st.caption(
        f"Saved data as of (Pacific): {status.get('as_of', 'unknown')} · "
        "Scan output derives from existing clinical, SEC, FDA and market "
        "evidence. This button-free read-only view does not dispatch a new scan."
    )
    counts = status["scan_counts"]
    track_metrics = st.columns(2)
    track_metrics[0].metric(
        "Verified Phase 3 under tracking", status["phase3_tracking_count"]
    )
    track_metrics[1].metric(
        "Before second-financing closure",
        status["phase3_tracking_before_second_financing"],
    )
    st.caption(
        "GEM discovery begins when a source-linked successful Phase 3 "
        "result is verified. A completed trial without a verified successful "
        "readout does not qualify. Tracking starts BEFORE financing #2 "
        "closes and is distinct from trade-entry approval."
    )
    early = [
        record for record in items
        if record.get("Phase 3 tracking", "").startswith("TRACKING")
    ]
    with st.expander(
        "EARLY GEM WATCH — VERIFIED PHASE 3 BEFORE SECOND FINANCING",
        expanded=True,
    ):
        waiting = [
            record for record in early
            if record.get("2nd Financing Completed") != "YES — VERIFIED (HISTORICAL)"
        ]
        if waiting:
            fields = [
                "Ticker", "Drug", "Indication", "NCT ID",
                "Phase 3 result date (source)", "Phase 3 tracking",
                "Financing watch", "Financing cycle (separate)",
                "Phase 3 GEM", "Days to PDUFA", "Phase 3 source",
                "Exact event",
            ]
            st.dataframe(
                pd.DataFrame(waiting).reindex(columns=fields),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info(
                "No currently source-verified successful Phase 3 programs "
                "awaiting independently verified second-financing closure. "
                "This is not evidence that no such programs exist outside "
                "the saved scan universe."
            )
        st.caption(
            "Early watch is read-only and refreshes with the saved clinical "
            "and financing feeds. It does not execute trades or trigger an "
            "independent continuous SEC search. A blank Phase 3 GEM rank "
            "means some ranking gates remain incomplete."
        )
    st.markdown("### BROAD PHASE 3 DISCOVERY — BEFORE FINANCING #2")
    st.caption(
        "The saved clinical #4 results-intake ledger includes posted trial "
        "results and separately sourced issuer readout announcements. These "
        "are **discovery leads**, NOT proof that primary endpoints succeeded. "
        "Only the verified-success gate above can start confirmed GEM tracking."
    )
    try:
        discovery, discovery_meta = _discovery(str(path), signature, day)
    except (OSError, ValueError, TypeError, KeyError):
        discovery, discovery_meta = [], {"status":"REVIEW_SOURCE_UNAVAILABLE", "source_rows":0}
    d1, d2, d3 = st.columns(3)
    d1.metric("Results for clinical review", len(discovery))
    d2.metric("Saved source records", discovery_meta.get("source_rows", 0))
    d3.metric("Ambiguous source identities", discovery_meta.get("rejected_ambiguous_identity", 0) +
              discovery_meta.get("ambiguous_duplicates", 0))
    st.caption(
        "Discovery status: " + str(discovery_meta.get("status", "REVIEW")) +
        ". Neither these records nor their published p-values automatically "
        "promote a trial to GEM-qualified successful Phase 3."
    )
    with st.expander("REVIEW SOURCE-LINKED PHASE 3 RESULTS / ISSUER READOUTS", expanded=False):
        if discovery:
            source_rows = pd.DataFrame(discovery).reindex(columns=DISCOVERY_COLUMNS)
            st.dataframe(source_rows.head(250), hide_index=True, use_container_width=True)
            if len(source_rows) > 250:
                st.caption(f"First 250 of {len(source_rows):,} saved review leads shown.")
            st.download_button(
                "EXPORT PHASE 3 DISCOVERY REVIEW QUEUE",
                source_rows.to_csv(index=False).encode("utf-8"),
                file_name=f"gem_phase3_discovery_review_{day:%Y%m%d}.csv",
                mime="text/csv", key="gem_discovery_review_csv",
            )
        else:
            st.info("No source-valid posted Phase 3 results or readout leads in the saved ledger.")
        st.caption(
            "Clinical #4 collector and nightly scans may be incomplete. "
            "This list is restricted to the saved source ledger; issuer success, "
            "effect size, safety, and exact program identity still require "
            "independent clinical verification."
        )
    st.markdown("### GEM SOURCE & MODEL READINESS")
    report = build_readiness_report(
        path, items, status, discovery, discovery_meta, as_of=day
    )
    stat1, stat2, stat3 = st.columns(3)
    stat1.metric("Ranking source feed",
                 "CURRENT" if status.get("feed_current") else "STALE / UNVERIFIED")
    stat2.metric("Clinical collector", report["clinical_collector"]["status"].replace("_", " "))
    stat3.metric("Validated historical trades", "NOT ESTABLISHED")
    if report["research_status"].startswith("HOLD"):
        st.warning(
            "RESEARCH SOURCE HOLD: saved required inputs are missing or the "
            "ranking source snapshot is not verified current. No stale source "
            "may be treated as a new trade-ready GEM signal."
        )
    st.caption(
        "Coverage is NOT independently verified across all US-listed biotechnology "
        "issuers. GEM scores are research rankings, not proven stock-return "
        "forecasts. The collection audit distinguishes clinical results from "
        "verified clinical success and SEC closing evidence."
    )
    with st.expander("GEM SOURCE COVERAGE, VALIDATION GAPS & DOWNLOADABLE AUDIT",
                     expanded=False):
        missing = report["missing_required_inputs"]
        if missing:
            st.write("Missing or invalid saved inputs: " + ", ".join(missing))
        st.write("Unresolved audit flags: " +
                 (", ".join(report["blocking_or_review_flags"]) or "None from saved inputs"))
        inventory = [
            {"Input": key, "State": value["state"],
             "Saved rows": value.get("rows", "—")}
            for key, value in {**report["required_source_inventory"],
                               **report["historical_data_inventory"]}.items()
        ]
        st.dataframe(pd.DataFrame(inventory), use_container_width=True, hide_index=True)
        checks = report["acceptance_checks"]
        st.caption(
            "100% acceptance checklist — every gate must pass independently; "
            "a missing or unverified source counts as NOT MET."
        )
        st.dataframe(
            pd.DataFrame([
                {"Required acceptance gate": k.replace("_", " ").title(),
                 "Result": "PASS" if passed else "NOT MET"}
                for k, passed in checks.items()
            ]), use_container_width=True, hide_index=True,
        )
        st.caption(
            f"Verified requirements met: {sum(checks.values())}/{len(checks)}. "
            "This is a requirements audit, not a prediction-accuracy score."
        )
        st.download_button(
            "DOWNLOAD GEM READINESS AUDIT",
            json.dumps(report, indent=2, sort_keys=True).encode("utf-8"),
            file_name=f"gem_readiness_audit_{day:%Y%m%d}.json",
            mime="application/json", key="gem_readiness_export",
        )
    cols = st.columns(3)
    for col, stage in zip(cols, STAGES):
        col.metric(stage + " qualified", counts[stage]["qualified"])
        col.caption(f"{counts[stage]['review']:,} require review")

    mode = st.radio(
        "GEMS rows", ("All candidates, including review", "Qualified in any classification"),
        horizontal=True, key="gem_scan_row_mode",
    )
    eligible = [
        item for item in items
        if any(item[stage + " rank"] is not None for stage in STAGES)
    ]
    shown = eligible if mode.startswith("Qualified") else items
    shown = sorted(
        shown,
        key=lambda r: (
            min((r[stage + " rank"] for stage in STAGES
                 if r[stage + " rank"] is not None), default=1000000),
            str(r.get("Ticker") or ""),
            str(r.get("Exact event") or ""),
        ),
    )
    if not eligible:
        st.info(
            "No currently verified GEM qualifiers pass all requirements. "
            "Research candidates remain below for evidence review; no ranks are invented."
        )
    if shown:
        st.markdown(_gems_table(shown[:75]), unsafe_allow_html=True)
        if len(shown) > 75:
            st.caption(f"Showing the first 75 of {len(shown):,} candidates in the grouped GEMS display.")
    else:
        st.info("No candidates match the selected GEMS view.")

    st.caption(
        "GEM entry cutoff is PDUFA -3. The original POST PHASE 3 Stage 1 "
        "workspace still has its legacy -7-day entry gate; its entry status "
        "is labeled separately in the GEM detail exports to avoid confusion."
    )
    discrimination = gem_discrimination_audit(items, STAGES)
    with st.expander("GEM RANKING QUALITY — TIES & EVIDENCE LIMITS", expanded=False):
        st.dataframe(pd.DataFrame([
            {
                "Scan": stage, "Qualified": discrimination[stage]["qualified"],
                "Distinct scores": discrimination[stage]["unique_scores"],
                "Stocks tied on score": discrimination[stage]["tied_candidates"],
                "Largest tie": discrimination[stage]["largest_tied_group"],
                "Status": discrimination[stage]["status"].replace("_", " "),
            } for stage in STAGES
        ]), use_container_width=True, hide_index=True)
        st.caption(
            "A high number of tied scores indicates that strict evidence gates "
            "leave little remaining ranking discrimination. It does NOT establish "
            "which stock will appreciate the most. Historical GEM calibration "
            "must be independently validated before adjusting weights."
        )
    st.markdown("### GEM SCAN QUALIFIERS & FULL COLUMNS")
    tabs = st.tabs(list(STAGES))
    for tab, stage in zip(tabs, STAGES):
        with tab:
            st.caption(
                "Research-only rubric: " +
                "; ".join(f"{column}: {points} points"
                          for column, points in WEIGHTS[stage].items())
            )
            with st.expander(stage + " — required qualifiers", expanded=False):
                for index, qualifier in enumerate(SCAN_QUALIFIERS[stage], 1):
                    st.write(f"{index}. {qualifier}")
            filter_mode = st.radio(
                "Scan results for " + stage,
                ("Qualified only", "All including review"),
                horizontal=True, key="gem_stage_filter_" + stage,
            )
            stage_rows = [
                record for record in items
                if filter_mode == "All including review"
                or record[stage + " score"] is not None
            ]
            stage_rows.sort(key=lambda r: (
                r[stage + " rank"] is None,
                r[stage + " rank"] if r[stage + " rank"] is not None else 1000000,
                str(r.get("Ticker") or ""), str(r.get("Exact event") or ""),
            ))
            ordered = (
                [stage + " GEM", "Ticker", "Drug", "Indication",
                 "Phase 3 tracking", "Financing watch",
                 "Phase 3 result date (source)",
                 stage + " qualifier", stage + " missing"]
                + list(STAGE_COLUMNS[stage])
                + ["Exact event", "Entry qualification",
                   "Rating limitations", "As of Pacific"]
            )
            table = pd.DataFrame(stage_rows).reindex(columns=ordered)
            table = table.rename(columns={
                stage + " GEM": "GEM rank (score)",
                stage + " qualifier": "Qualification",
                stage + " missing": "Missing qualifiers",
                "Entry qualification": "Legacy Stage 1 entry gate (PDUFA -7)",
            })
            st.caption(
                f"{len(table):,} rows · {counts[stage]['qualified']:,} "
                "strictly qualified in this classification. A blank rank "
                "means REVIEW, not a score of zero."
            )
            st.dataframe(table.head(250), use_container_width=True, hide_index=True)
            if len(table) > 250:
                st.caption("First 250 rows shown; export includes all filtered rows.")
            st.download_button(
                "EXPORT " + stage.upper() + " GEM SCAN",
                table.to_csv(index=False).encode("utf-8"),
                file_name="gem_" + stage.lower().replace("-", "_").replace(" ", "_")
                          + "_" + day.isoformat() + ".csv",
                mime="text/csv",
                key="gem_export_" + stage,
            )
    st.divider()
    render_gem_calibration(root)
    st.caption(
        "Qualification here means a source-supported research ranking only. "
        "Do not place trades from these scores alone: cash runway, valuation, "
        "current dilution and independently backtested return expectations "
        "still require individual review."
    )
