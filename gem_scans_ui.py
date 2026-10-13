"""Read-only Streamlit GEM scanner surface inside the existing SCANS sub-tab."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_scans import SCAN_QUALIFIERS, STAGES, WEIGHTS, build_gem_scans

FILES = (
    "pdufa_candidates.csv",
    "step7_live_status.json",
    "step7_financing_review.csv",
    "second_financing_status.csv",
    "step7_market_status.csv",
    "step7_pre_phase3_feed.csv",
    "post_phase3_discoveries.csv",
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
    st.caption(
        "Qualification here means a source-supported research ranking only. "
        "Do not place trades from these scores alone: cash runway, valuation, "
        "current dilution and independently backtested return expectations "
        "still require individual review."
    )
