"""Reference-image layout for GEM JR / GEM, using real saved source records only.

Presentation layer only. The existing GEM eligibility, scan, scoring, trial-history,
and W/T engines remain authoritative; no placeholder prices or fake grades.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gem_membership_history import read_history, enrich_stage_rows, departed_stage_rows
from gem_potential_list import build_potential_list
from gem_verified_snapshot import source_cleared_gems
from gem_stage_dossier import exact_event, timeline_events, scan_health
from gem_trading_advisory import (
    load_market_rows, assess_gem_trade, _score_gem_trade, render_base_formation_chart,
)
from ticker_toggle_panel import _init_browser_selection, _toggle, clean_ticker
from gem_trade_navigation import open_trade_workspace


def _show(value, default="NOT AVAILABLE"):
    if value is None:
        return default
    value = str(value).strip()
    if not value or value.lower() in ("none", "nan", "nat", "<na>"):
        return default
    return value


def _short(value, limit=46):
    value = _show(value)
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _css():
    """Compact reference-matched dashboard styles, isolated to GEM JR/GEM.

    This page inherits a site-wide large-font/black-metric theme. Override it
    only while a GEM visual hero is mounted; other PDUFA pages stay untouched.
    """
    st.markdown("""
    <style>
    .stApp:has(.gem-visual-hero){
      --gem-ink:#17364c;--gem-muted:#5f7788;--gem-rule:#d9e4eb;
      --gem-band:#eaf4f0;--gem-accent:#126e52;
      background:linear-gradient(120deg,#eff7f5 0%,#edf4fb 76%,#eef6f8 100%)!important;
      color:var(--gem-ink)!important;font-size:12px!important;
    }
    .stApp:has(.gem-stage-gem){
      --gem-band:#e9f2fd;--gem-accent:#2367a5;
    }
    .stApp:has(.gem-visual-hero) .block-container{
      max-width:1850px!important;padding:.4rem 1rem 1.2rem!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stVerticalBlock"]{
      gap:.34rem!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stHorizontalBlock"]{
      gap:.45rem!important;
    }
    .stApp:has(.gem-visual-hero) h1{
      font-size:1.0rem!important;line-height:1.15!important;
      letter-spacing:.015em;margin:0!important;color:#15354a!important;
    }
    .stApp:has(.gem-visual-hero) h2{
      font-size:1.08rem!important;line-height:1.18!important;
      margin:.15rem 0!important;color:#15354a!important;
    }
    .stApp:has(.gem-visual-hero) h3{
      font-size:.91rem!important;line-height:1.17!important;
      margin:.2rem 0!important;color:#163950!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stCaptionContainer"],
    .stApp:has(.gem-visual-hero) [data-testid="stCaptionContainer"] p{
      color:#657d8e!important;font-size:10.5px!important;
      line-height:1.3!important;margin:0!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMarkdownContainer"] p,
    .stApp:has(.gem-visual-hero) [data-testid="stMarkdownContainer"] li{
      font-size:11px!important;line-height:1.3!important;
      margin:0!important;color:#304f62!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-pdufa_brand_header{
      background:#fff!important;border:1px solid var(--gem-rule)!important;
      border-radius:9px!important;padding:7px 12px!important;
      box-shadow:0 2px 8px #a4bdc522;margin:0 0 3px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-pdufa_brand_header [data-testid="stCaptionContainer"]{
      display:none!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stRadio"]{
      margin:0!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p{
      font-size:10px!important;color:#4f7184!important;
    }
    .stApp:has(.gem-visual-hero) [data-baseweb="tab-list"]{
      background:#fff!important;padding:3px 5px!important;border:1px solid var(--gem-rule);
      border-radius:8px;gap:4px!important;min-height:30px!important;
      box-shadow:0 1px 6px #9bb2ba16;
    }
    .stApp:has(.gem-visual-hero) [data-baseweb="tab"]{
      font-size:10.5px!important;font-weight:700!important;min-height:26px!important;
      padding:4px 13px!important;border-radius:5px!important;
      border-bottom:0!important;color:#2c4f66!important;
    }
    .stApp:has(.gem-visual-hero) [data-baseweb="tab"][aria-selected="true"]{
      background:var(--gem-accent)!important;color:#fff!important;
    }
    .stApp:has(.gem-visual-hero) [data-baseweb="tab-highlight"],
    .stApp:has(.gem-visual-hero) [data-baseweb="tab-border"]{
      background:transparent!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stTabs"] [data-testid="stTabPanel"]{
      padding-top:0!important;
    }
    .stApp:has(.gem-visual-hero) .gem-visual-hero{
      padding:4px 0 5px!important;margin:0!important;
    }
    .gem-visual-kicker{font-size:9px!important;letter-spacing:.12em;
      font-weight:800;color:var(--gem-accent);margin:0 0 1px!important;}
    .stApp:has(.gem-visual-hero) .gem-visual-hero h2{
      font-size:23px!important;line-height:1.15!important;letter-spacing:-.025em;
      font-weight:850!important;color:var(--gem-ink)!important;margin:0!important;
    }
    .stApp:has(.gem-stage-jr) .gem-visual-hero h2{color:#09503e!important}
    .stApp:has(.gem-stage-gem) .gem-visual-hero h2{color:#1c5891!important}
    .gem-visual-hero p{font-size:10px!important;line-height:1.25!important;
      color:#5e7688!important;margin:2px 0!important}
    .gem-section-head{
      background:var(--gem-band)!important;border-bottom:1px solid #d8e6e9;
      font-size:12px!important;line-height:1.2!important;font-weight:800!important;
      color:#244e60!important;margin:-9px -11px 7px!important;
      padding:6px 10px!important;
    }
    .stApp:has(.gem-visual-hero) div[class*="st-key-visual_"]
    [data-testid="stVerticalBlockBorderWrapper"]{
      background:#fff!important;border:1px solid var(--gem-rule)!important;
      border-radius:8px!important;
      box-shadow:0 1px 3px #b4c7d018!important;padding:9px 11px!important;
    }
    .stApp:has(.gem-visual-hero) div[class*="st-key-visual_"]
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stMetric"]){
      padding:5px 8px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMetric"]{
      background:#fff!important;border:none!important;border-radius:0!important;
      min-height:44px!important;padding:0!important;box-shadow:none!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMetric"] *{
      color:var(--gem-ink)!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMetricLabel"]{
      font-size:9px!important;line-height:1.2!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMetricValue"]{
      font-size:17px!important;line-height:1.22!important;
      font-weight:800!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stMetricDelta"]{
      font-size:9px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stButton"] button,
    .stApp:has(.gem-visual-hero) [data-testid="stLinkButton"] a,
    .stApp:has(.gem-visual-hero) .stDownloadButton button{
      min-height:24px!important;max-height:29px!important;
      border-radius:5px!important;padding:3px 7px!important;
      font-size:10.5px!important;line-height:1.2!important;font-weight:700!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stTextInput"] input{
      font-size:10px!important;min-height:28px!important;padding:4px 8px!important;
      border:1px solid #cddce4!important;border-radius:4px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stTextInput"] label{
      font-size:10px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stDataFrame"]{
      border:1px solid #e3ebf0!important;border-radius:4px!important;
      font-size:10px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stDataFrame"] *{
      font-size:10px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stAlert"]{
      padding:6px 8px!important;border-radius:5px!important;
      font-size:10px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stExpander"]{
      border:1px solid #dbe5ea!important;border-radius:5px!important;
      margin:2px 0!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stExpander"] summary{
      font-size:11px!important;padding:5px 8px!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stProgress"]{
      height:5px!important;margin:0!important;
    }
    .stApp:has(.gem-visual-hero) [data-testid="stProgress"]>div{
      height:5px!important;border-radius:5px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-visual_jr_summary [data-testid="stHorizontalBlock"],
    .stApp:has(.gem-visual-hero) .st-key-visual_gem_summary [data-testid="stHorizontalBlock"]{
      gap:7px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-visual_jr_ranked [data-testid="stHorizontalBlock"],
    .stApp:has(.gem-visual-hero) .st-key-visual_gem_ranked [data-testid="stHorizontalBlock"]{
      gap:6px!important;padding:3px 0!important;border-bottom:1px solid #e8eef1;
      min-height:27px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-visual_jr_ranked [data-testid="stCaptionContainer"],
    .stApp:has(.gem-visual-hero) .st-key-visual_gem_ranked [data-testid="stCaptionContainer"]{
      font-size:9.5px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-visual_jr_ranked [data-testid="stButton"] button,
    .stApp:has(.gem-visual-hero) .st-key-visual_gem_ranked [data-testid="stButton"] button{
      padding:2px 4px!important;min-height:22px!important;
      max-height:25px!important;font-size:10px!important;
    }
    .stApp:has(.gem-visual-hero) .st-key-visual_jr_ranked [data-testid="stButton"] button[kind="primary"]{
      background:#127650!important;border-color:#127650!important;
    }
    .stApp:has(.gem-stage-gem) .st-key-visual_gem_ranked [data-testid="stButton"] button[kind="primary"]{
      background:#2474be!important;border-color:#2474be!important;
    }
    .stApp:has(.gem-visual-hero) [class*="st-key-visual_"][class*="_w_"] button,
    .stApp:has(.gem-visual-hero) [class*="st-key-visual_"][class*="_selected_w"] button{
      background:#2b80c5!important;color:#fff!important;border:1px solid #226fb0!important;
    }
    .stApp:has(.gem-visual-hero) [class*="st-key-visual_"][class*="_t_"] button,
    .stApp:has(.gem-visual-hero) [class*="st-key-visual_"][class*="_selected_t"] button{
      background:#157a55!important;color:#fff!important;border:1px solid #116a49!important;
    }
    .gem-visual-chip{display:inline-block!important;border-radius:3px!important;
      padding:2px 5px!important;font-weight:800!important;font-size:9px!important;
      background:#fff1cc!important;color:#895f05!important;}
    .gem-visual-chip--qualified{background:#dcf5e7!important;color:#176649!important}
    .gem-visual-footnote{text-align:center;padding:5px!important;
      font-size:9px!important;color:#6b8090!important}
    @media(max-width:760px){
      .stApp:has(.gem-visual-hero) .block-container{padding:5px 8px!important}
      .stApp:has(.gem-visual-hero) [data-baseweb="tab"]{padding:4px 6px!important;
        font-size:10px!important}
      .stApp:has(.gem-visual-hero) .gem-visual-hero h2{font-size:19px!important}
      .stApp:has(.gem-visual-hero) [data-testid="stVerticalBlock"]{gap:5px!important}
      .stApp:has(.gem-visual-hero) .st-key-visual_jr_summary [data-testid="stHorizontalBlock"],
      .stApp:has(.gem-visual-hero) .st-key-visual_gem_summary [data-testid="stHorizontalBlock"]{
        flex-wrap:wrap!important;
      }
    }
    </style>
    """, unsafe_allow_html=True)


def _head(text):
    st.markdown('<div class="gem-section-head">' + escape(text) + '</div>',
                unsafe_allow_html=True)


def _frame(rows, height=None):
    if not rows:
        st.caption("No source-linked observations available.")
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 **({"height": height} if height else {}))


def _priority_fields(record, event, score):
    return {
        "phase": _short(record.get("Phase 3 status") or record.get("Evidence type"), 32),
        "finance": (_short(record.get("Two-benchmark status") or
                           record.get("SEC documents rechecked") or record.get("Financing SEC source"),
                           32)),
        "cash": _show(event.get("cash"), "—"),
        "entry": score.get("entry") if score else None,
        "exit": score.get("exit_risk") if score else None,
        "quality": score.get("quality") if score else None,
    }


def _rankings(stage, active, root, today):
    """Build exact-program lookup once, without inventing unknown entry scores."""
    market = load_market_rows(root)
    mapped = {}
    source_status = {}
    if stage == "GEM":
        try:
            from gem_master_list import build_gem_master_list
            from gem_scans_ui import _saved_gem_scans, FILES
            path = Path(root)
            signature = tuple((name, (path / name).stat().st_mtime_ns
                      if (path / name).exists() else 0) for name in FILES)
            items, source_status = _saved_gem_scans(str(path), signature, today)
            for row in build_gem_master_list(items):
                key = (clean_ticker(row.get("Ticker")), str(row.get("Exact Program / Event") or ""))
                if key in mapped:
                    mapped[key] = None  # ambiguous exact identity: fail closed
                else:
                    mapped[key] = row
        except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
            mapped = {}
            source_status = {}
    results = []
    for i, record in enumerate(active):
        event = exact_event(root, record.get("Exact program"))
        ticker = clean_ticker(record.get("Ticker"))
        master = mapped.get((ticker, str(record.get("Exact program") or "")))
        profile = assess_gem_trade(master or {"Ticker": ticker, "_eligible": False},
                                   market, source_status, today)
        score = (_score_gem_trade(master, profile, source_status) if master
                 else {"entry": None, "exit_risk": None,
                       "entry_status": "NOT VERIFIED", "exit_status": "NOT VERIFIED",
                       "entry_factors": [], "exit_factors": [],
                       "entry_coverage": 0, "exit_coverage": 0})
        score["quality"] = master.get("GEM Score /100") if master and master.get("_eligible") else None
        results.append((record, event, master, profile, score))
    return results


def _candles(symbol):
    """Third-party TradingView candles; never represent them as verified scanner data."""
    if not symbol:
        st.info("Choose a valid ticker to load an external candlestick chart.")
        return
    import json
    settings = {
        "autosize": True, "symbol": symbol, "interval": "D", "timezone": "America/Los_Angeles",
        "theme": "light", "style": "1", "locale": "en", "enable_publishing": False,
        "hide_top_toolbar": False, "allow_symbol_change": False, "save_image": False,
        "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies", "MACD@tv-basicstudies"],
        "support_host": "https://www.tradingview.com",
    }
    html = """<div class="tradingview-widget-container" style="width:100%;height:100%">
    <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
    <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>""" + json.dumps(settings) + """</script>
    </div>"""
    components.html(html, height=390, scrolling=False)
    st.caption("Candlesticks/RSI/MACD supplied by external TradingView (possibly delayed). "
               "Not a verified trading feed or executable quote.")


def _factor_box(label, color, factors, value, coverage, status, *, stage):
    _head(label)
    st.metric(label.split("—")[0].strip(),
              f"{value}/100" if value is not None else "N/A")
    st.caption(f"Observable weighting coverage: {coverage}/100 · {status}")
    if factors:
        for factor, maximum, earned, why in factors:
            a, b = st.columns([3, 1])
            a.caption(factor)
            b.caption(f"{earned if earned is not None else '—'}/{maximum}")
            if earned is None:
                st.progress(0)
            else:
                st.progress(max(0.0, min(1.0, float(earned) / max(1, maximum))))
    else:
        st.info("No auditable factor breakdown: source feed is partial or stale. "
                "No scores are manufactured.")
    if stage == "GEM JR":
        st.caption("GEM JR remains a research queue; GEM trading scores require qualification.")


def _row_button(stage, symbol, selection, i):
    """One row gets independent real W and T actions, not decorative mockup badges."""
    w, t = st.columns(2, gap="small")
    with w:
        st.button("W", key=f"visual_{stage}_w_{i}",
                  type="primary" if symbol in st.session_state.get("watchlist", []) else "secondary",
                  help=f"Toggle {symbol} Watchlist", on_click=_toggle, args=(symbol, "watch"),
                  use_container_width=True)
    with t:
        st.button("T", key=f"visual_{stage}_t_{i}",
                  type="primary" if symbol in st.session_state.get("trading_tickers", []) else "secondary",
                  help=f"Open {symbol} in WT research (no broker order)",
                  on_click=open_trade_workspace, args=(symbol,),
                  use_container_width=True)


def render_visual_stage(stage, root="data"):
    """Render reference-image sections above the existing deep-research tools."""
    if stage not in ("GEM JR", "GEM"):
        raise ValueError("Unknown stage")
    _css()
    junior = stage == "GEM JR"
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    _init_browser_selection("visual_" + ("jr" if junior else "gem"))
    if junior:
        active, held = build_potential_list(root)
        qualified, qualified_history, _ = source_cleared_gems(root)
        excluded = {str(x.get("Pipeline ID") or "") for x in qualified + qualified_history}
        active = [r for r in active if str(r.get("Pipeline ID") or "") not in excluded]
        active = enrich_stage_rows(active, "GEM_JR", read_history(root))
    else:
        active, held, _ = source_cleared_gems(root)
        active = enrich_stage_rows(active, "GEM", read_history(root))
    stageid = "jr" if junior else "gem"
    rows = _rankings(stage, active, root, today)
    st.markdown(
        '<div class="gem-visual-hero gem-stage-' + stageid + '"><div class="gem-visual-kicker">'
        f'GEM JR + GEM · PAGE {1 if junior else 2} OF 2</div>'
        f'<h2>{escape(stage)} — Full Research &amp; Trading View</h2>'
        '<p>' + ('Earlier-entry research · post-Phase-3 monitoring · evidence pending verification'
                 if junior else
                 'High-conviction qualification · exact-program Phase 3 and two independent financing checks')
        + ' · Real source observations only; missing fields stay unavailable.</p></div>',
        unsafe_allow_html=True)
    with st.container(key="visual_" + stageid + "_summary"):
        kpis = st.columns(6, gap="small")
        facts = [
            ("Candidate universe", str(len(active))),
            ("Entry readiness", "0–100 / N/A"),
            ("Exit risk", "0–100 / N/A"),
            ("Clinical hierarchy", "3 levels"),
            ("Financing rule", "Track / verify" if junior else "2 SEC closes"),
            ("Scheduled scans", "10 PM PT"),
        ]
        for container, (label, value) in zip(kpis, facts):
            with container:
                with st.container(border=True):
                    st.metric(label, value)

    with st.container(border=True, key="visual_" + stageid + "_ranked"):
        headline, search = st.columns([3.6, 1.2], gap="small",
                                      vertical_alignment="center")
        with headline:
            _head(f"▦ {stage} Candidate Priority Table")
        with search:
            query = st.text_input(
                "Search candidate", placeholder="Search ticker / drug / indication",
                key="visual_" + stageid + "_search", label_visibility="collapsed")
        matched = [(i, x) for i, x in enumerate(rows)
                   if query.strip().lower() in (
                      _show(x[0].get("Ticker"), "") + " " +
                      _show(x[1].get("company"), "") + " " +
                      _show(x[0].get("Drug"), "") + " " +
                      _show(x[0].get("Indication"), "")).lower()]
        if not matched:
            st.info("No active source-qualified candidates match this view. "
                    "Held and historical programs remain in the detailed workbench below.")
        else:
            widths = [.83, 1.8, 1.45, .78, 1.58, 1.55, .75, .53, .62, 1.05, .9]
            labels = ["Ticker", "Company / Drug", "Indication", "Stage", "Phase 3",
                      "Financing", "Runway", "Entry", "Exit", "Status", "W / T"]
            header = st.columns(widths, vertical_alignment="center", gap="small")
            for h, title in zip(header, labels):
                h.markdown("**" + title + "**")
            for rank, (i, (rec, evt, master, p, score)) in enumerate(matched[:12], 1):
                symbol = clean_ticker(rec.get("Ticker"))
                c = st.columns(widths, vertical_alignment="center", gap="small")
                with c[0]:
                    st.button(symbol or "—", key=f"visual_{stageid}_pick_{i}",
                              help="Open this candidate profile",
                              on_click=_select, args=(stageid, i),
                              use_container_width=True)
                c[1].caption(_short(evt.get("company") or rec.get("Drug"), 32))
                c[2].caption(_short(rec.get("Indication"), 24))
                c[3].caption("Phase 3")
                c[4].caption(_short(rec.get("Phase 3 status") or rec.get("Evidence type"), 30))
                c[5].caption("2 SEC closes ✓" if not junior else
                             _short(rec.get("SEC documents rechecked"), 26))
                c[6].caption("N/A")  # Runway months not present in the qualified feed.
                c[7].caption(str(score["entry"]) if score["entry"] is not None else "N/A")
                c[8].caption(str(score["exit_risk"]) if score["exit_risk"] is not None else "N/A")
                c[9].markdown(
                    '<span class="gem-visual-chip' +
                    ('' if junior else ' gem-visual-chip--qualified') +
                    '">' + ('Review' if junior else 'Qualified · review') +
                    '</span>', unsafe_allow_html=True)
                with c[10]:
                    _row_button(stageid, symbol, rec, i)
            if len(matched) > 12:
                st.caption(f"Showing 12 of {len(matched)}; use search to narrow the source list.")

    if not rows:
        _empty_reference_sections(stageid, stage)
        _monitoring(stage, root, today)
        return

    indexkey = "visual_" + stageid + "_current"
    idx = st.session_state.get(indexkey, 0)
    if not isinstance(idx, int) or idx < 0 or idx >= len(rows):
        idx = 0
    record, event, master, profile, score = rows[idx]
    ticker = clean_ticker(record.get("Ticker"))
    st.caption(f"Selected program: {ticker} · {_show(record.get('Drug'))} · "
               f"{_show(record.get('Indication'))} · {_show(record.get('NCT ID'))}")

    left, right = st.columns([1.65, 1], gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_profile"):
            _head("▦ Selected Candidate · Full Profile")
            # Paired label/value fields reproduce the reference's compact two-up
            # profile without deriving approval odds or missing financial inputs.
            values = [
                ("Ticker", ticker, "Company / drug",
                 _show(event.get("company")) + " / " + _show(record.get("Drug"))),
                ("Indication", _show(record.get("Indication")), "Phase 3",
                 _show(record.get("Phase 3 status") or record.get("Evidence type"))),
                ("PDUFA date", _show(record.get("PDUFA saved") or event.get("pdufa_date")),
                 "Clinical readout", _show(record.get("Phase 3 date") or event.get("phase3_date"))),
                ("Cash / runway", _show(event.get("cash")) + " / runway NOT VERIFIED",
                 "Market cap / float", _show(event.get("market_cap")) + " / " +
                 _show(event.get("shares_float"))),
                ("Short interest", _show(event.get("short_interest")),
                 "Warrants / convertibles", "NOT VERIFIED"),
                ("Approval probability", _show(event.get("approval_probability"), "NOT SCORED"),
                 "Entry readiness", _show(score["entry"]) + " /100"),
                ("Exit risk", _show(score["exit_risk"]) + " /100",
                 "Trial NCT", _show(record.get("NCT ID"))),
            ]
            _frame([{"Field": left, "Source observation": lv,
                     "Other field": right, "Other observation": rv}
                    for left, lv, right, rv in values], height=270)
    with right:
        with st.container(border=True, key="visual_" + stageid + "_gates"):
            _head("★ " + stage + " Qualification Gates")
            items = (
              ["Phase 3 readout and results evidence","PDUFA timing tracked",
               "First financing source and closure","Second financing source and closure",
               "Cash, dilution, FDA risks","Program stays JR until GEM verifies"]
              if junior else
              ["Exact-program successful Phase 3 readout","SEC-backed financing #1 after readout",
               "Separate SEC-backed financing #2 after readout","Distinct financing dates and source records",
               "Cash/runway, warrants and dilution review","PDUFA / liquidity / risk checked before entry"]
            )
            for n, val in enumerate(items, 1):
                st.caption(f"{n:02d} • {val}")
            st.warning("Qualification is not trade authorization. Missing, "
                       "stale or contested source observations remain on hold.")

    left, right = st.columns(2, gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_clinical"):
            _head("▦ Three-Level Nested Clinical Trials")
            company = _show(event.get("company"), ticker)
            # Streamlit forbids nested expanders. Use nested toggles and
            # containers for genuine Company > Drug/Indication > Trial levels.
            if st.toggle("▸ LEVEL 1 · COMPANY / TICKER — " + company,
                         value=True, key="visual_" + stageid + "_level1"):
                with st.container(border=True):
                    st.caption("Company: " + company + " · Ticker: " + ticker +
                               " · Exact Pipeline ID: " + _show(record.get("Pipeline ID")))
                    if st.toggle("↳ LEVEL 2 · DRUG / INDICATION — " +
                                 _short(record.get("Drug")) + " / " +
                                 _short(record.get("Indication")),
                                 value=True, key="visual_" + stageid + "_level2"):
                        with st.container(border=True):
                            _frame([{
                                "Drug": _show(record.get("Drug")),
                                "Exact indication": _show(record.get("Indication")),
                                "Program key": _show(record.get("Exact program")),
                            }])
                            with st.expander("↳ ↳ LEVEL 3 · PHASE 3 TRIAL — " +
                                             _show(record.get("NCT ID")), expanded=True):
                                _frame([
                                    {"Trial field": "NCT ID", "Value": _show(record.get("NCT ID"))},
                                    {"Trial field": "Readout", "Value": _show(record.get("Phase 3 date") or event.get("phase3_date"))},
                                    {"Trial field": "Primary endpoint / p-values", "Value": _show(event.get("reported_p_values"))},
                                    {"Trial field": "Result source status", "Value": _show(record.get("Phase 3 status"))},
                                    {"Trial field": "Patients / study sites", "Value": "NOT AVAILABLE IN QUALIFIED FEED"},
                                ])
            st.caption("Other indications and trials remain independent Pipeline records; "
                       "no clinical evidence is inherited between programs.")
    with right:
        with st.container(border=True, key="visual_" + stageid + "_financing"):
            _head("▦ Financing, SEC Verification & Dilution")
            financials = [
                {"Verification": "Financing #1 close", "Saved date": _show(record.get("First close")),
                 "Source": _show(record.get("First SEC source"))},
                {"Verification": "Financing #2 close", "Saved date": _show(record.get("Second close")),
                 "Source": _show(record.get("Second SEC source") or record.get("Financing SEC source"))},
                {"Verification": "Program SEC review date", "Saved date": _show(record.get("Source review as of")),
                 "Source": "Requires current source check"},
                {"Verification": "Dilution, warrants / convertibles",
                 "Saved date": _show(event.get("new_dilution_flag")),
                 "Source": "Warrants / convertibles NOT VERIFIED"},
                {"Verification": "Runway", "Saved date": "NOT VERIFIED",
                 "Source": "Cash balance alone is not months of runway"},
            ]
            _frame(financials, height=225)
            for label, key in [("Clinical primary evidence", "Phase 3 source"),
                               ("SEC financing #1", "First SEC source"),
                               ("SEC financing #2", "Second SEC source")]:
                url = record.get(key)
                if isinstance(url, str) and url.startswith("https://"):
                    st.link_button(label + " ↗", url)
            st.caption("An offering announcement is not a verified closing. "
                       "Two distinct post-readout funded events are required for GEM.")

    left, right = st.columns([1.55, 1], gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_chart"):
            _head("↗ Trading Chart · Price, Base, Breakout & Volume")
            _candles(ticker)
            if st.toggle("SHOW SOURCE-SAVED EOD · Base, SMA20/SMA50, support and volume",
                         value=False, key="visual_" + stageid + "_saved_eod"):
                render_base_formation_chart(profile, compact=True)
    with right:
        with st.container(border=True, key="visual_" + stageid + "_signals"):
            _head("▦ Technical Entry / Exit Signals")
            base = profile["base"]
            _frame([
                {"Indicator": "Base status", "Observation": _show(base.get("status"))},
                {"Indicator": "Base support / resistance", "Observation":
                 f"{_show(base.get('support'))} / {_show(base.get('resistance'))}"},
                {"Indicator": "Latest close / SMA20 / SMA50", "Observation":
                 " / ".join(_show(profile.get(k)) for k in ("close", "sma20", "sma50"))},
                {"Indicator": "RSI (14) / relative volume", "Observation":
                 _show(profile.get("rsi")) + " / " + _show(profile.get("rvol"))},
                {"Indicator": "MACD", "Observation":
                 _show("Bullish" if profile["macd"]["bullish"] else "Bearish")
                 if profile.get("macd") is not None else "NOT AVAILABLE"},
                {"Indicator": "ATR / VWAP / spread", "Observation": "NOT VERIFIED — required OHLC / intraday / quotes"},
                {"Indicator": "Breakout / volume", "Observation": _show(base.get("breakout_rvol"))},
                {"Indicator": "Setup recommendation", "Observation": _show(profile.get("recommendation"))},
            ], height=318)
            st.caption("Not a confirmed entry signal. Validated stops and targets require "
                       "real order/risk parameters.")

    left, right = st.columns(2, gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_entry"):
            _factor_box("✓ ENTRY READINESS — Weighted 0–100", "green",
                        score["entry_factors"], score["entry"], score["entry_coverage"],
                        score["entry_status"], stage=stage)
    with right:
        with st.container(border=True, key="visual_" + stageid + "_exit"):
            _factor_box("⚑ EXIT RISK — Weighted 0–100", "red",
                        score["exit_factors"], score["exit_risk"], score["exit_coverage"],
                        score["exit_status"], stage=stage)

    left, right = st.columns(2, gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_timeline"):
            _head("◷ Timeline · PDUFA · Dead Zone")
            events, status = timeline_events(record, event, today)
            _frame(events, height=200)
            st.caption(status)
            st.caption("A dead-zone boundary requires a dated, exact-program catalyst; "
                       "missing endpoints cannot be inferred.")
    with right:
        with st.container(border=True, key="visual_" + stageid + "_riskpolicy"):
            _head("⚠ Hard Stops · PDUFA Decision · W/T Controls")
            st.warning("UNRESOLVED POLICY: choose pre-PDUFA exit, partial hold, or "
                       "hold-through. No automated exit is authorized.")
            st.caption("Clinical failure and verified dilution require review; "
                       "a price-base warning cannot replace position-specific stops.")
            c1, c2, c3 = st.columns([1, 1, 3])
            with c1:
                st.button("W", key="visual_" + stageid + "_selected_w",
                          on_click=_toggle, args=(ticker, "watch"))
            with c2:
                st.button("T", key="visual_" + stageid + "_selected_t",
                          on_click=open_trade_workspace, args=(ticker,))
            c3.caption("W = Watchlist · T = WT research (not an order)")

    _monitoring(stage, root, today)
    st.markdown('<div class="gem-visual-footnote">Source-backed research view. '
                'The reference artwork used hypothetical figures; this dashboard '
                'never substitutes mockup examples for real verification.</div>',
                unsafe_allow_html=True)



def _empty_reference_sections(stageid, stage):
    """Keep every reference-image panel visible even when eligibility yields zero.

    Empty is a valid research result, not permission to insert demo tickers.
    """
    groups = [
        ([1.65, 1], [
            ("▦ Selected Candidate · Full Profile",
             "No active exact-program candidate is selectable in this stage."),
            ("★ " + stage + " Qualification Gates",
             "Source results must meet this stage's independent clinical/SEC gates."),
        ]),
        ([1, 1], [
            ("▦ Three-Level Nested Clinical Trials",
             "COMPANY → DRUG / INDICATION → TRIAL: no active candidate data."),
            ("▦ Financing, SEC Verification & Dilution",
             "Financing dates, SEC sources, cash and dilution require a selected program."),
        ]),
        ([1.55, 1], [
            ("↗ Trading Chart · Price, Base, Breakout & Volume",
             "No selected ticker. No illustrative candlesticks or inferred signals."),
            ("▦ Technical Entry / Exit Signals",
             "RSI, MACD, RVOL, SMA, ATR, VWAP, support and resistance unavailable."),
        ]),
        ([1, 1], [
            ("✓ ENTRY READINESS — Weighted 0–100",
             "N/A — candidate not qualified or source coverage unavailable."),
            ("⚑ EXIT RISK — Weighted 0–100",
             "N/A — no source-grounded active program."),
        ]),
        ([1, 1], [
            ("◷ Timeline · PDUFA · Dead Zone",
             "No exact-program Phase 3 / financing / PDUFA dates are available."),
            ("⚠ Hard Stops · PDUFA Decision · W/T Controls",
             "PDUFA exit policy remains unresolved. W/T actions require a selected ticker."),
        ]),
    ]
    for n, (widths, panels) in enumerate(groups):
        left, right = st.columns(widths, gap="small")
        for slot, (title, description), suffix in zip(
            (left, right), panels, ("left", "right")
        ):
            with slot:
                with st.container(border=True, key=f"visual_{stageid}_empty_{n}_{suffix}"):
                    _head(title)
                    st.info(description)

def _select(stageid, index):
    st.session_state["visual_" + stageid + "_current"] = index


def _monitoring(stage, root, today):
    stageid = "jr" if stage == "GEM JR" else "gem"
    left, middle, right = st.columns(3, gap="small")
    with left:
        with st.container(border=True, key="visual_" + stageid + "_news"):
            _head("♧ News · Alerts · Watchlist Activity")
            st.caption("Clinical readouts · FDA decisions · SEC 8-K, S-3 / 424B "
                       "· dilution · short interest · breakout signals")
            st.info("Candidate-specific live alerts are not independently verified. "
                    "Review primary sources and SCANS before acting.")
            st.caption("W/T selections are research labels; no trades executed.")
    with middle:
        with st.container(border=True, key="visual_" + stageid + "_scans"):
            _head("↻ Scan Scheduler · Diagnostics · Recovery")
            st.caption("10 PM PT planned sequential schedule; verify actual runs in SCANS.")
            _frame(scan_health(root), height=215)
            st.caption("A completed collector does not establish fresh SEC or market coverage.")
    with right:
        with st.container(border=True, key="visual_" + stageid + "_history"):
            _head("↗ Promotion · Exit History · Backtests")
            histories = departed_stage_rows(read_history(root), "GEM_JR" if stageid == "jr" else "GEM")
            st.metric("Observed stage departures", len(histories))
            if histories:
                _frame(histories[:8], height=160)
            else:
                st.caption("No verified stage departures recorded in the saved ledger.")
            st.warning("Historical trading edge and benchmark win rates are not "
                       "independently backtested. No trade returns inferred.")
