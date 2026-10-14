"""GEM first-tab three-level, source-auditable master list with shared W/T labels.

Level 1: every exact stock/program (paged, never truncated).
Level 2: the six actual 100-point GEM factors.
Level 3: the real input values, model arithmetic and source provenance.
No manufactured subfactor weights, unverified scores or extra entry gates.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_master_list import MASTER_COLUMNS, build_gem_master_list
from gem_scans_ui import FILES, _saved_gem_scans
from ticker_toggle_panel import _init_browser_selection, _toggle, clean_ticker


FACTOR_FIELDS = (
    ("Phase 3 clinical quality", "Phase 3 Quality /30", 30),
    ("Financial runway", "Financial Runway /20", 20),
    ("Trading activity", "Trading Activity /20", 20),
    ("Dilution overhang", "Dilution /15", 15),
    ("Hedge-fund accumulation", "Hedge-Fund Accumulation /10", 10),
    ("PDUFA timing", "PDUFA Timing /5", 5),
)
assert sum(cap for _, _, cap in FACTOR_FIELDS) == 100
PAGE_SIZE = 15


def _value(value):
    """Keep missing evidence missing, rather than converting it to zero."""
    if value is None:
        return "Unverified / unavailable"
    if isinstance(value, float) and not math.isfinite(value):
        return "Unverified / unavailable"
    text = str(value).strip()
    return text if text and text.lower() not in ("nan", "none", "nat") else "Unverified / unavailable"


def _num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _input(name, value, calculation, source=""):
    return {
        "Model input": name,
        "Actual saved value": _value(value),
        "Contribution / rule": calculation,
        "Source / provenance": _value(source),
    }


def score_factor_inputs(item, row, field, *, feed_current=True):
    """Return the ACTUAL score's inputs, not invented independent subweights.

    Some factors have one aggregate research score; only trading activity
    has a genuine 12+8 mathematical decomposition in GEM's current model.
    Context observations cannot be counted again as points.
    """
    item = item or {}
    eligible = row.get("_eligible") is True
    observed = row.get(field) if eligible else None
    actual = f"{observed} / {next(cap for _, col, cap in FACTOR_FIELDS if col == field)}" if eligible and observed is not None else "Not scored — entry benchmarks pending"
    phase_url = row.get("Phase 3 Source")
    financing_url = row.get("Financing Source")
    pdufa_url = row.get("PDUFA Source")
    if field == "Phase 3 Quality /30":
        rows = [
            _input("Clinical evidence source score /30", item.get("Clinical evidence /30"),
                   "Research input; not a separate additive component", phase_url),
            _input("Exact-event Phase 3 readout status", item.get("GEM clinical readout status"),
                   "Negative readout: 0; non-positive status: capped at 12", phase_url),
            _input("Clinical/regulatory conflict flag", item.get("GEM clinical conflict flag"),
                   "Unresolved conflict forces this factor to 0", phase_url),
        ]
    elif field == "Financial Runway /20":
        rows = [
            _input("Cash runway (months)", row.get("Cash Runway (months)"),
                   "Model brackets: >=24:20; >=18:17; >=12:13; >=6:7; >=0:2; missing:0",
                   item.get("Cash runway source")),
            _input("Cash runway trend", row.get("Cash Runway Trend"),
                   "Risk warning only; no additional points",
                   item.get("Cash runway source")),
        ]
    elif field == "Trading Activity /20":
        setup = _num(item.get("Trading setup /20"))
        market = _num(item.get("Market activity /10"))
        setup_pts = 12 * max(0.0, min(20.0, setup or 0.0)) / 20
        market_pts = 8 * max(0.0, min(10.0, market or 0.0)) / 10
        rows = [
            _input("Trading setup research score /20", item.get("Trading setup /20"),
                   f"12 × bounded(input, 0..20) / 20 = {setup_pts:.2f} / 12, before rounding"),
            _input("Market activity research score /10", item.get("Market activity /10"),
                   f"8 × bounded(input, 0..10) / 10 = {market_pts:.2f} / 8, before rounding"),
            _input("Clinical/market feed current", "YES" if feed_current else "NO",
                   "Model uses round(sum of both contributions) when current, otherwise 0"),
        ]
    elif field == "Dilution /15":
        rows = [
            _input("Post-readout dilution flag", item.get("GEM financing dilution flag"),
                   "Full 15 only for NO / NONE / FALSE / 0; otherwise 0", financing_url),
            _input("Financing watch", row.get("Financing Watch"),
                   "Context only, no separate points", financing_url),
            _input("Dilution warning", row.get("Dilution Warning"),
                   "Context only, no separate points", financing_url),
        ]
    elif field == "Hedge-Fund Accumulation /10":
        rows = [
            _input("Underlying 13F accumulation points /10",
                   item.get("Hedge-fund accumulation /10"),
                   "Bounded to 0..10, included only with source-verified quarterly 13F",
                   row.get("Hedge-Fund Source Links")),
            _input("13F evidence status", row.get("Hedge-Fund Signal"),
                   "Must be SOURCE-VERIFIED QUARTERLY 13F HOLDINGS to score",
                   row.get("Hedge-Fund Source Links")),
            _input("Specialist managers adding", row.get("Hedge-Fund Managers Adding"),
                   "Context; already reflected in underlying score, not counted twice",
                   row.get("Hedge-Fund Source Links")),
            _input("13F quarter end", item.get("Hedge-fund quarter end"),
                   "Quarterly positions are delayed, not real-time purchases",
                   row.get("Hedge-Fund Source Links")),
        ]
    elif field == "PDUFA Timing /5":
        rows = [
            _input("Days to PDUFA", row.get("Days to PDUFA"),
                   "Verified days 30..90:5; 14..29:4; 91..180:3; >=181:2; 4..13:1; else:0",
                   pdufa_url),
            _input("PDUFA date verification", item.get("PDUFA verification"),
                   "Must be VERIFIED — SOURCE LINKED; otherwise 0", pdufa_url),
            _input("Planned exit (PDUFA −3)", row.get("Planned Exit (-3 days)"),
                   "Manual exit plan / warning, not an entry benchmark", pdufa_url),
        ]
    else:
        raise ValueError(f"Unknown GEM score factor: {field}")
    rows.append(_input("FACTOR SUBTOTAL (only counted line)", actual,
                       "This is the saved GEM model's awarded factor points, not an extra input"))
    if not eligible:
        for detail in rows:
            if "before rounding" in detail["Contribution / rule"]:
                detail["Contribution / rule"] = "Formula reference only — candidate is not scored"
    return rows


def _unique_sources(items):
    """Never attach another trial's evidence to a duplicated event identity."""
    by_key = {}
    duplicates = set()
    for item in items:
        event = str(item.get("Exact event") or "")
        if event in by_key:
            duplicates.add(event)
        else:
            by_key[event] = item
    return {key: value for key, value in by_key.items() if key and key not in duplicates}


def _score_check(row):
    if not row.get("_eligible"):
        return None
    values = [row.get(field) for _, field, _ in FACTOR_FIELDS]
    if any(_num(value) is None for value in values):
        return False
    return int(sum(_num(value) for value in values)) == row.get("GEM Score /100")


def render_gem_nested_master(root="data", *, selections_ready=False):
    """Render in first/renamed GEM tab, above the historical clinical cards."""
    st.markdown("## #1 GEM — THREE-LEVEL NESTED MASTER LIST")
    st.caption(
        "Stock → six 100-point factors → individual saved inputs, formulas and evidence. "
        "Every saved GEM candidate stays in this single sortable-ranked universe. "
        "Only source-verified Phase 3 results release AND second distinct post-readout "
        "financing closure enable a GEM rank or score; W/T choices are manual labels, "
        "never trade execution or another qualification benchmark."
    )
    data_path = Path(root)
    signature = tuple(
        (name, (data_path / name).stat().st_mtime_ns if (data_path / name).exists() else 0)
        for name in FILES
    )
    day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        items, status = _saved_gem_scans(str(data_path), signature, day)
        rows = build_gem_master_list(items)
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
        st.error("GEM source data could not be loaded; no scores or eligibility inferred.")
        return
    sources = _unique_sources(items)
    if not selections_ready:
        _init_browser_selection("gem_nested_master")
    watch = {clean_ticker(v) for v in st.session_state.get("watchlist", [])}
    trading = {clean_ticker(v) for v in st.session_state.get("trading_tickers", [])}
    if not status.get("feed_current") or not status.get("sec_financing_source_current"):
        st.warning(
            "SOURCE RECHECK PARTIAL / STALE: recorded qualifications must be reverified "
            "before acting. A displayed score is research context, not a buy signal."
        )
    m1, m2, m3 = st.columns(3)
    m1.metric("GEM programs", len(rows))
    m2.metric("Verified 2-benchmark eligible", sum(r["_eligible"] for r in rows))
    m3.metric("Watch / source review", sum(not r["_eligible"] for r in rows))
    filters = st.columns([2, 2, 1])
    view = filters[0].selectbox(
        "Candidate filter", ["All candidates", "Entry-eligible only", "Watch / review"],
        key="gem_nested_view",
    )
    query = filters[1].text_input(
        "Search ticker / drug / indication / event",
        key="gem_nested_query",
    ).strip().casefold()
    stage = filters[2].selectbox(
        "Stage",
        ["All", "PDUFA", "Post-Financing", "Phase 3", "Research / Unverified"],
        key="gem_nested_stage",
    )
    matching = [
        r for r in rows
        if (view == "All candidates"
            or (view == "Entry-eligible only" and r["_eligible"])
            or (view == "Watch / review" and not r["_eligible"]))
        and (stage == "All" or r["GEM Stage"] == stage)
        and (not query or any(query in str(r.get(col) or "").casefold()
                              for col in ("Ticker", "Drug", "Indication",
                                          "Exact Program / Event")))
    ]
    total_pages = max(1, (len(matching) + PAGE_SIZE - 1) // PAGE_SIZE)
    if st.session_state.get("gem_nested_page", 1) not in range(1, total_pages + 1):
        st.session_state["gem_nested_page"] = 1
    page = st.selectbox(
        "Master list page (all candidates accessible)",
        range(1, total_pages + 1),
        format_func=lambda n: f"Page {n} / {total_pages}",
        key="gem_nested_page",
    )
    first = (page - 1) * PAGE_SIZE
    visible = matching[first:first + PAGE_SIZE]
    st.caption(
        f"Showing {first + 1 if visible else 0}–{first + len(visible)} of "
        f"{len(matching):,} matching programs ({len(rows):,} total). "
        "W = Watchlist; T = Trading research list. Both synchronize with WT "
        "in this browser; they do not place broker orders."
    )
    if not visible:
        st.info("No GEM programs match the current filters.")
    for offset, r in enumerate(visible):
        ticker = clean_ticker(r.get("Ticker"))
        identity = str(r.get("Exact Program / Event") or
                       f"{r.get('Ticker')}|{r.get('Drug')}|{r.get('Indication')}|{first + offset}")
        uid = hashlib.sha256(f"{identity}|{first + offset}".encode("utf-8")).hexdigest()[:14]
        score = f"{r['GEM Score /100']}/100" if r["_eligible"] else "UNSCORED"
        rank = f"#{r['GEM Rank']}" if r["_eligible"] else "—"
        with st.container(border=True):
            head = st.columns([8, 1, 1], gap="small")
            head[0].markdown(
                f"**{rank} · {_value(ticker)} · {_value(r.get('Drug'))}**  "
                f"— {_value(r.get('GEM Stage'))} · **GEM {score}**"
            )
            if ticker:
                head[1].button(
                    "W", key=f"gem_nested_w_{uid}",
                    type="primary" if ticker in watch else "secondary",
                    help=f"{'Remove' if ticker in watch else 'Add'} {ticker} from WT Watchlist",
                    on_click=_toggle, args=(ticker, "watch"),
                )
                head[2].button(
                    "T", key=f"gem_nested_t_{uid}",
                    type="primary" if ticker in trading else "secondary",
                    help=f"{'Remove' if ticker in trading else 'Add'} {ticker} from WT Trading research list — no broker order",
                    on_click=_toggle, args=(ticker, "trade"),
                )
            with st.expander(
                f"OPEN STOCK → six factors → inputs | {_value(r.get('Indication'))} | {_value(r.get('GEM Status'))}",
                expanded=False,
            ):
                benchmarks = pd.DataFrame([
                    {"Entry benchmark": "1. Phase 3 results released",
                     "Verification": _value(r.get("Phase 3 Verified")),
                     "Date": _value(r.get("Phase 3 Result Date")),
                     "Evidence": _value(r.get("Phase 3 Source"))},
                    {"Entry benchmark": "2. Second separate financing closed",
                     "Verification": _value(r.get("Second Financing Closed")),
                     "Date": _value(r.get("Second Financing Close Date")),
                     "Evidence": _value(r.get("Financing Source"))},
                ])
                st.dataframe(benchmarks, use_container_width=True, hide_index=True)
                if not r["_eligible"]:
                    st.info("WATCH / REVIEW — one or both benchmarks not verified. Raw inputs "
                            "are available below, but no GEM rank or score has been assigned.")
                else:
                    score_ok = _score_check(r)
                    if score_ok is False:
                        st.error("GEM FACTOR SUM DOES NOT MATCH THE SAVED TOTAL — review scoring evidence.")
                st.markdown("**Level 2 — select a factor to expand its Level 3 inputs**")
                source_item = sources.get(str(r.get("Exact Program / Event") or ""))
                if source_item is None:
                    st.warning("Event identity is missing or ambiguous; underlying inputs are withheld.")
                for index, (factor_name, field, cap) in enumerate(FACTOR_FIELDS):
                    if source_item is None:
                        continue
                    factor_value = r.get(field) if r["_eligible"] else None
                    label = (f"{factor_name} — {factor_value}/{cap}" if factor_value is not None
                             else f"{factor_name} — not scored (maximum {cap})")
                    open_key = f"gem_nested_factor_open_{uid}"
                    factor_col, point_col = st.columns([8, 1])
                    if factor_col.button(
                        ("▼ " if st.session_state.get(open_key) == field else "▶ ") + label,
                        key=f"gem_nested_factor_button_{uid}_{index}",
                        use_container_width=True,
                    ):
                        st.session_state[open_key] = (
                            None if st.session_state.get(open_key) == field else field
                        )
                    point_col.markdown(
                        f"**{factor_value}/{cap}**" if factor_value is not None else f"—/{cap}"
                    )
                    if st.session_state.get(open_key) == field:
                        st.caption("Level 3 — actual inputs (non-additive context is labeled)")
                        st.dataframe(
                            pd.DataFrame(score_factor_inputs(
                                source_item, r, field,
                                feed_current=bool(status.get("feed_current")),
                            )),
                            use_container_width=True, hide_index=True,
                        )
                st.markdown(f"**TOTAL GEM SCORE: {score}**")
                st.caption(
                    f"Risk flags: {_value(r.get('Risks / Evidence Gaps'))} · "
                    f"PDUFA: {_value(r.get('PDUFA Date'))} · "
                    f"Planned exit (−3 days): {_value(r.get('Planned Exit (-3 days)'))}"
                )
                if st.checkbox("Show additional risk and source observations", key=f"gem_nested_more_{uid}"):
                    details = pd.DataFrame([
                        {"Observation": name, "Value": _value(r.get(column))}
                        for name, column in (
                            ("Financial cash runway", "Cash Runway (months)"),
                            ("Dilution warning", "Dilution Warning"),
                            ("Hedge-fund signal", "Hedge-Fund Signal"),
                            ("Insider Form 4 signal (advisory)", "Insider Form 4 Signal"),
                            ("Insider source links", "Insider Source Links"),
                            ("Exact program / event", "Exact Program / Event"),
                        )
                    ])
                    st.dataframe(details, use_container_width=True, hide_index=True)
    st.download_button(
        "EXPORT ALL MATCHING GEM CANDIDATES",
        pd.DataFrame(matching).reindex(columns=MASTER_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name=f"gem_unified_master_{day:%Y%m%d}.csv",
        mime="text/csv",
        key="gem_nested_full_export",
    )
    st.caption(
        "100 points = Phase 3 30 + runway 20 + trading activity 20 + "
        "dilution 15 + hedge funds 10 + PDUFA timing 5. "
        "Subtables show the genuine underlying formula and measured inputs, "
        "not independently invented subweights. Quarterly 13F data are delayed. "
        "Source gaps are not positive evidence."
    )
