"""Read-only combined clinical-to-trading overview, no ordinal rankings."""
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import pandas as pd
import streamlit as st
from pdufa_table_headers import pdufa_dataframe, attach_survey
from ticker_toggle_panel import render_ticker_toggle_panel, _init_browser_selection
from pdufa_circled_help_grid import render_dashboard_sheet
from pipeline_universe import load_universe
from post_phase3_unified import build_queue
from step7_cached_snapshot import load_current_snapshot
from pdufa_display_columns import (POST_SCORES, PRE_SCORES, PRE_PRIORITY_SCORES,
                                  POST_PRIORITY_SCORES, prepare_pdufa_grid, sort_pdufa_grid,
                                  DISPLAY_ORDER_OPTIONS, finance_style, FINANCE_PALETTE)
from pdufa_date_gradient import COUNTDOWN_BANDS
from datetime import timezone
from pathlib import Path

@st.cache_data(ttl=120, show_spinner=False)
def _load(day, root="data"):
    pipeline = load_universe(root, today=day)
    post, health = build_queue(root, as_of=day)
    snapshot = None
    try:
        snapshot = load_current_snapshot(Path(root), datetime.now(timezone.utc))
        pre = snapshot[0] if snapshot is not None else []
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
        pre = []
    return pipeline, post, health, pre, snapshot is not None

def _timing_legend_html():
    """Legend uses the same colors as the rendered PDUFA and financing cells."""
    countdown_key = (
        ("91+ days", COUNTDOWN_BANDS[0][2]),
        ("90–60 days", COUNTDOWN_BANDS[1][2]),
        ("59–30 days", COUNTDOWN_BANDS[2][2]),
        ("29–0 days", COUNTDOWN_BANDS[3][2]),
        ("Past / unknown", FINANCE_PALETTE["unknown"]),
    )
    financing_key = (
        ("Started", FINANCE_PALETTE["green"]),
        ("Running", FINANCE_PALETTE["yellow"]),
        ("Closed", FINANCE_PALETTE["red"]),
        ("Unverified", FINANCE_PALETTE["unknown"]),
    )

    def legend_row(heading, items):
        swatches = "".join(
            '<span class="timing-key-item">'
            f'<span class="timing-key-swatch" style="background:{html.escape(color, quote=True)}" aria-hidden="true"></span>'
            f'{html.escape(label)}</span>'
            for label, color in items
        )
        return (
            '<div class="timing-key-row">'
            f'<strong>{html.escape(heading)}</strong>'
            f'<div class="timing-key-items">{swatches}</div>'
            '</div>'
        )

    return (
        '<style>'
        '.timing-key{background:#fff;color:#111;border:1px solid #111;border-radius:8px;'
        'padding:8px 10px;margin:5px 0 10px;font-size:12px;line-height:1.4}'
        '.timing-key-row+.timing-key-row{border-top:1px solid #ddd;margin-top:6px;padding-top:6px}'
        '.timing-key-row>strong{display:block;font-size:12px;margin-bottom:3px}'
        '.timing-key-items{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}'
        '.timing-key-item{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}'
        '.timing-key-swatch{display:inline-block;flex:0 0 12px;width:12px;height:12px;'
        'border:1px solid #333;border-radius:2px;box-sizing:border-box}'
        '.timing-key-note{font-size:11px;color:#444;margin-top:5px}'
        '</style>'
        '<div class="timing-key" aria-label="PDUFA countdown and financing timeline color key">'
        + legend_row("DAYS TO PDUFA", countdown_key)
        + legend_row("FINANCING TIMELINE (F)", financing_key)
        + '<div class="timing-key-note">Colors indicate countdown windows and '
          'financing stage—not FDA approval probability or financing safety.</div>'
        + '</div>'
    )


def _render_command_center(df, pre, post, *, today, ticker, phase, stage, search, display_order, root="data"):
    """Named source panels share filters without changing evidence or scores."""
    def filtered_feed(records, view):
        grid = prepare_pdufa_grid(pd.DataFrame(records), view=view, as_of=today)
        if ticker:
            grid = grid.loc[grid["Ticker"].eq(ticker)]
        if phase != "All" or stage != "All":
            identities = set(zip(df["Ticker"], df["NCT ID"]))
            grid = grid.loc[
                [(row.get("Ticker"), row.get("NCT ID")) in identities
                 for row in grid.to_dict("records")]
            ]
        if search and not grid.empty:
            hay = grid.reindex(columns=["Ticker", "Drug", "Indication", "NCT ID"])
            hay = hay.fillna("").astype(str).agg(" ".join, axis=1)
            grid = grid.loc[hay.str.contains(search, case=False, regex=False)]
        return sort_pdufa_grid(grid, display_order)

    pre3 = filtered_feed(pre, "PRE PHASE 3")
    post3 = filtered_feed(post, "POST PHASE 3")
    # Shared W/T state was already hydrated by the GEM tab entrypoint.
    st.markdown("""
    <style>
    .st-key-overview_pipeline_panel, .st-key-overview_pre3_panel,
    .st-key-overview_post3_panel {
      background:#ffffff; border:2px solid #000000 !important;
      border-radius:14px; padding:14px; color:#111111;
      position:relative; isolation:isolate;
    }
    .st-key-overview_pipeline_panel::before,
    .st-key-overview_pre3_panel::before,
    .st-key-overview_post3_panel::before {
      position:absolute; top:2px; right:16px; z-index:-1;
      font-size:120px; font-weight:900; line-height:1;
      color:rgba(17,17,17,.10); pointer-events:none; user-select:none;
    }
    .st-key-overview_pipeline_panel::before {content:"2";}
    .st-key-overview_pre3_panel::before {content:"3";}
    .st-key-overview_post3_panel::before {content:"4";}
    /* Scope the responsive grid to the three overview cards. Nested metric
       columns inside the POST3 timeline retain their own layout. */
    /* #2, #3 and #4 occupy precisely one third of the same 100%-wide row.
       Internal column padding supplies gutters without stealing grid width. */
    .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) {
      display:grid !important;
      width:100% !important;
      max-width:100% !important;
      grid-template-columns:repeat(3,minmax(0,33.333333%));
      gap:0 !important;
      align-items:stretch !important;
    }
    /* Stretch each Streamlit column's vertical content to the tallest card
       in its grid row, without forcing a fixed height or hiding content. */
    .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) > [data-testid="stColumn"] {
      box-sizing:border-box !important;
      display:flex !important;
      flex-direction:column !important;
      align-self:stretch !important;
      flex:none !important;
      width:100% !important;
      min-width:0 !important;
      max-width:100% !important;
      padding-inline:0.375rem !important;
    }
    .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {
      display:flex !important;
      flex-direction:column !important;
      flex:1 1 auto !important;
      height:100% !important;
    }
    /* Streamlit's bordered st.container adds another wrapper inside each
       column. Stretch that wrapper too, or the visible black outlines may
       stop at different vertical positions despite equal grid-row heights. */
    .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) > [data-testid="stColumn"]
    [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-overview_pipeline_panel, .st-key-overview_pre3_panel, .st-key-overview_post3_panel) {
      display:flex !important;
      flex-direction:column !important;
      flex:1 1 auto !important;
      height:100% !important;
    }
    .st-key-overview_pipeline_panel, .st-key-overview_pre3_panel,
    .st-key-overview_post3_panel {
      box-sizing:border-box;
      flex:1 1 auto;
      height:100%;
      min-width:0;
      width:100%;
    }
    @media (max-width:1250px) {
      .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) {
        grid-template-columns:repeat(2,minmax(0,50%));
      }
    }
    @media (max-width:800px) {
      .st-key-overview_panels [data-testid="stHorizontalBlock"]:has(.st-key-overview_pipeline_panel) {
        grid-template-columns:minmax(0,100%);
      }
      .st-key-overview_pipeline_panel::before,
      .st-key-overview_pre3_panel::before,
      .st-key-overview_post3_panel::before {font-size:100px; right:12px;}
    }
    </style>
    """, unsafe_allow_html=True)
    # #1 is a new collapsible block INSIDE the former Unified Overview.
    # Keep all existing overview controls, score-coverage audits, #2/#3/#4 cards,
    # timeline, all-fields table and exports at their original positions.
    with st.expander("#1 GEM — THREE-LEVEL NESTED MASTER LIST (open to view)", expanded=False):
        from gem_nested_master_ui import render_gem_nested_master
        render_gem_nested_master(root=root, selections_ready=True)
    with st.container(key="overview_panels"):
        pipeline_col, pre3_col, post3_col = st.columns([1, 1, 1], gap="small")
        with pipeline_col, st.container(border=True, key="overview_pipeline_panel"):
            st.markdown("### #2-PIPELINE")
            st.caption("Clinical programs · stage, scores and financing cycle")
            st.metric("Matching programs", len(df))
            st.markdown(_timing_legend_html(), unsafe_allow_html=True)
            if df.empty:
                st.info("No pipeline programs match these filters.")
            render_dashboard_sheet(
                df.head(150),
                ["Ticker", "Score /100", "PDUFA Date", "Days to PDUFA",
                 "2nd Financing Completed", "Cash Runway (months)",
                 "Score type", "Pipeline stage", "F", "Drug", "NCT ID"],
                height=310,
                ticker_controls=True,
                watchlist=st.session_state.get("watchlist", []),
                trading_tickers=st.session_state.get("trading_tickers", []),
            )
            st.caption("Expand ALL FIELDS below for every clinical field, score component and source link.")
        with pre3_col, st.container(border=True, key="overview_pre3_panel"):
            st.markdown("### #3-PRE3")
            st.caption("Pre-readout Phase 3 programs · clinical evidence, scores and review priority")
            st.metric("Matching pre-readout programs", len(pre3))
            st.markdown(_timing_legend_html(), unsafe_allow_html=True)
            if pre3.empty:
                st.info("No current pre-readout programs match these filters.")
            render_dashboard_sheet(
                pre3.head(150),
                ["Ticker", "Score /100", "PDUFA Date", "Days to PDUFA",
                 "2nd Financing Completed", "Cash Runway (months)",
                 "Score type", "Score status", "F", "Drug", "NCT ID"],
                height=310,
                ticker_controls=True,
                watchlist=st.session_state.get("watchlist", []),
                trading_tickers=st.session_state.get("trading_tickers", []),
            )
            with st.expander("ALL PRE3 FIELDS & EVIDENCE"):
                pdufa_dataframe(finance_style(pre3.head(350)), hide_index=True,
                             use_container_width=True)
            st.download_button("EXPORT PRE3 PROGRAMS", pre3.to_csv(index=False).encode(),
                               file_name="unified_pre3_programs.csv", mime="text/csv",
                               key="overview_pre3_export")

        with post3_col, st.container(border=True, key="overview_post3_panel"):
            st.markdown("### #4-POST3")
            st.caption("Post-readout candidates · qualification, scores and financing evidence")
            st.metric("Matching candidates", len(post3))
            st.markdown(_timing_legend_html(), unsafe_allow_html=True)
            if post3.empty:
                st.info("No current trading candidates match these filters.")
            render_dashboard_sheet(
                post3.head(150),
                ["Ticker", "Score /100", "PDUFA Date", "Days to PDUFA",
                 "2nd Financing Completed", "Cash Runway (months)",
                 "Score type", "Entry qualification", "F", "Drug", "NCT ID"],
                height=310,
                ticker_controls=True,
                watchlist=st.session_state.get("watchlist", []),
                trading_tickers=st.session_state.get("trading_tickers", []),
            )
            with st.expander("ALL TRADING FIELDS & EVIDENCE"):
                pdufa_dataframe(finance_style(post3.head(350)), hide_index=True,
                             use_container_width=True)
            st.download_button("EXPORT TRADING CANDIDATES", post3.to_csv(index=False).encode(),
                               file_name="unified_trading_candidates.csv", mime="text/csv",
                               key="overview_trading_export")
    # Cross-panel timeline belongs below the equal-height cards, not inside #4.
    with st.expander("PDUFA TIMELINE", expanded=True):
        st.caption("Program-specific dates and countdowns · reported dates retain their evidence status")
        fields = ["Ticker", "Score /100", "Score type", "PDUFA Date", "Days to PDUFA", "2nd Financing Completed", "Cash Runway (months)", "Date Classification",
                  "Drug", "NCT ID", "Planned exit (-7 days)", "PDUFA source", "Pipeline source"]
        timeline = pd.concat([df.reindex(columns=fields), pre3.reindex(columns=fields),
                              post3.reindex(columns=fields)], ignore_index=True)
        timeline = timeline.loc[timeline["PDUFA Date"].fillna("").ne("")]
        timeline = timeline.drop_duplicates(subset=["Ticker", "NCT ID", "Drug", "PDUFA Date"])
        timeline = sort_pdufa_grid(timeline, display_order)
        attach_survey(timeline, df)
        a, b, c = st.columns(3)
        days = pd.to_numeric(timeline["Days to PDUFA"], errors="coerce")
        a.metric("Dated programs", len(timeline))
        b.metric("PDUFA within 30 days", int(days.between(0, 30).sum()))
        c.metric("Past dates to recheck", int(days.lt(0).sum()))
        if timeline.empty:
            st.info("No dated PDUFA programs match these filters. Undated programs remain in their source panels.")
        pdufa_dataframe(timeline.head(250), hide_index=True, use_container_width=True, height=310,
                     column_config={"PDUFA source": st.column_config.LinkColumn("PDUFA source"),
                                    "Pipeline source": st.column_config.LinkColumn("Pipeline source")})
        st.download_button("EXPORT PDUFA TIMELINE", timeline.to_csv(index=False).encode(),
                           file_name="unified_pdufa_timeline.csv", mime="text/csv",
                           key="overview_timeline_export")


def render_combined_overview(root="data", *, dashboard=False):
    """Render linked clinical context and return the shared ticker focus."""
    if dashboard:
        # Hydrate shared W/T once before either GEM or legacy source-table controls.
        _init_browser_selection("overview_inline")
    if not dashboard:
        st.markdown("### UNIFIED CLINICAL → TRADING DISPLAY")
        st.caption("Pipeline + pre-readout Phase 3 + post-readout trading evidence in one view. No ordinal ranks, Top 10, or automatic orders. Clinical and financing status are not inferred from trial stage.")
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        with st.spinner("Loading saved pipeline, clinical and PDUFA evidence…"):
            pipeline, post, health, pre, pre_current = _load(today, root)
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError):
        st.error("Saved source data could not be loaded. No eligibility has been verified.")
        return
    if not pre_current:
        st.warning("Pre–Phase 3 validated snapshot unavailable or expired. Pre-readout scores are left blank.")
    if not health.get("feed_current"):
        st.warning("Post–Phase 3 verification snapshot is stale. Post-readout scores, financing stages and entry-ready labels are withheld until refreshed.")
        post = []  # Fail closed: stale research records cannot populate current status cells.
    if not isinstance(pipeline, pd.DataFrame) or pipeline.empty:
        st.info("The saved Pipeline feed is empty.")
        return
    src = pipeline.copy()
    for c in ("ticker", "nct_id", "drug", "indication", "current_stage", "pdufa_date",
              "primary_completion", "source_url", "status", "record_id"):
        if c not in src:
            src[c] = ""
    src["Ticker"] = src["ticker"].fillna("").astype(str).str.strip().str.upper()
    src["NCT ID"] = src["nct_id"].fillna("").astype(str).str.strip().str.upper()
    src["Drug"] = src["drug"].fillna("").astype(str)
    src["Indication"] = src["indication"].fillna("").astype(str)
    src["Pipeline stage"] = src["current_stage"].fillna("").astype(str)
    src["Clinical status"] = src["status"].fillna("").astype(str)
    src["Primary completion"] = src["primary_completion"].fillna("").astype(str)
    src["PDUFA date (pipeline)"] = src["pdufa_date"].fillna("").astype(str)
    src["Pipeline source"] = src["source_url"].fillna("").astype(str)
    src["Research phase"] = src["Pipeline stage"].map(
        lambda x: "PRE PHASE 3" if x in ("Phase 3", "Phase 2/3", "Phase 2",
        "Phase 1", "Phase 1/2", "Early Phase 1") else
        "POST PHASE 3 / REGULATORY" if x in ("Phase 3 Results",
        "NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision")
        else "OTHER / REVIEW"
    )
    # A ticker-only match is prohibited: it can mix unrelated drugs and trials.
    post_by_id = {}
    ambiguous = set()
    for item in post:
        ticker = str(item.get("Ticker") or "").strip().upper()
        nct = str(item.get("NCT ID") or "").strip().upper()
        if not ticker or not nct:
            continue
        identity = (ticker, nct)
        if identity in post_by_id:
            ambiguous.add(identity)
        else:
            post_by_id[identity] = item
    for identity in ambiguous:
        post_by_id.pop(identity, None)
    cols = ("Entry qualification", "Phase 3 evidence", "Financing #2",
            "2nd Financing Completed", "Cash Runway (months)",
            "Financing cycle (separate)", "Evidence score /100",
            "Research priority /100", "Days to PDUFA", "Planned exit (-7 days)",
            "Blockers", "Next action", "Phase 3 source", "Financing source",
            "PDUFA source", "PDUFA date", *POST_SCORES,
            "Research priority status", *POST_PRIORITY_SCORES)
    # Exact ticker + NCT match only; ambiguous records are withheld.
    pre_by_id = {}
    ambiguous_pre = set()
    for item in pre:
        ticker = str(item.get("Ticker") or "").strip().upper()
        nct = str(item.get("NCT ID") or "").strip().upper()
        if not ticker or not nct:
            continue
        key = (ticker, nct)
        if key in pre_by_id:
            ambiguous_pre.add(key)
        else:
            pre_by_id[key] = item
    for key in ambiguous_pre:
        pre_by_id.pop(key, None)
    pre_fields = (
        "Pre-readout research score /100",
        "Preliminary clinical score /100", "Score status",
        "Clinical score as of", "Linked Phase 2 PRIMARY p",
        "Primary endpoint p values observed", *PRE_SCORES,
        "Review priority /100", "Review priority status",
        "Review priority rubric", *PRE_PRIORITY_SCORES,
    )
    records = []
    for r in src.to_dict("records"):
        key = (r["Ticker"], r["NCT ID"])
        matched = post_by_id.get(key)
        pre_match = pre_by_id.get(key)
        post_conflict = False
        pre_conflict = False
        if matched and r["Drug"] and matched.get("Drug"):
            if r["Drug"].strip().casefold() != str(matched["Drug"]).strip().casefold():
                matched = None
                post_conflict = True
        if pre_match and r["Drug"] and pre_match.get("Drug"):
            if r["Drug"].strip().casefold() != str(pre_match["Drug"]).strip().casefold():
                pre_match = None
                pre_conflict = True
        entry = {k: r[k] for k in ("Ticker", "NCT ID", "Drug", "Indication",
                                  "Research phase", "Pipeline stage", "Clinical status",
                                  "Primary completion", "PDUFA date (pipeline)", "Pipeline source")}
        entry["Pipeline Last Checked"] = r.get("checked_at", "")
        entry["Post evidence match"] = ("DRUG CONFLICT — REVIEW" if post_conflict else
                                        "AMBIGUOUS — REVIEW" if key in ambiguous
                                        else "EXACT TICKER + NCT" if matched else "NOT LINKED")
        entry["Pre Phase 3 evidence match"] = ("DRUG CONFLICT — REVIEW" if pre_conflict else
                                                "AMBIGUOUS — REVIEW" if key in ambiguous_pre
                                                else "EXACT TICKER + NCT" if pre_match else "NOT LINKED")
        for c in pre_fields:
            entry[c] = pre_match.get(c, "") if pre_match else ""
        for c in cols:
            entry[c] = matched.get(c, "") if matched else ""
        if key in ambiguous or post_conflict:
            entry["Entry qualification"] = ("REVIEW — DRUG IDENTITY CONFLICT" if post_conflict
                                              else "REVIEW — AMBIGUOUS TRIAL MATCH")
        records.append(entry)
    df = prepare_pdufa_grid(pd.DataFrame(records), view="UNIFIED", as_of=today)
    # Coverage audit is computed before filtering, without hiding missing evidence.
    total = len(df)
    pre_exact = int(df["Pre Phase 3 evidence match"].eq("EXACT TICKER + NCT").sum())
    post_exact = int(df["Post evidence match"].eq("EXACT TICKER + NCT").sum())
    both = int((df["Pre Phase 3 evidence match"].eq("EXACT TICKER + NCT")
               & df["Post evidence match"].eq("EXACT TICKER + NCT")).sum())
    pre_ambiguous = int(df["Pre Phase 3 evidence match"].eq("AMBIGUOUS — REVIEW").sum())
    pre_conflicts = int(df["Pre Phase 3 evidence match"].eq("DRUG CONFLICT — REVIEW").sum())
    post_ambiguous = int(df["Post evidence match"].eq("AMBIGUOUS — REVIEW").sum())
    post_conflicts = int(df["Post evidence match"].eq("DRUG CONFLICT — REVIEW").sum())
    pre_score_count = int(pd.to_numeric(df["Pre-readout research score /100"],
                                       errors="coerce").notna().sum())
    post_score_count = int(pd.to_numeric(df["Evidence score /100"],
                                        errors="coerce").notna().sum())
    tickers = sorted({str(value).strip().upper()
                      for value in df["Ticker"].tolist()
                      + [item.get("Ticker", "") for item in post]
                      + ([item.get("Ticker", "") for item in pre] if dashboard else [])
                      if str(value).strip()})
    if not dashboard:
        render_ticker_toggle_panel("post3_4", post, title="TICKER WATCH / TRADE")
    focus_options = ["All tickers", *tickers]
    prefix = "overview" if dashboard else "unified"
    focus_key = "overview_shared_ticker" if dashboard else "postphase3_shared_ticker"
    if st.session_state.get(focus_key, "All tickers") not in focus_options:
        st.session_state[focus_key] = "All tickers"
    focus = st.selectbox("Focus ticker", focus_options, key=focus_key)
    ticker = None if focus == "All tickers" else focus
    st.caption("One ticker selection updates #2-PIPELINE, #3-PRE3, #4-POST3 and the PDUFA Timeline." if dashboard else
               "This ticker selection links the clinical/pipeline display, PDUFA dates, "
               "candidate qualification, reported positions, and historical research below.")
    if ticker:
        df = df.loc[df["Ticker"].eq(ticker)]
    a, b, c, d = st.columns(4)
    a.metric("Pipeline records", len(df))
    b.metric("Exact post evidence matches", int(df["Post evidence match"].eq("EXACT TICKER + NCT").sum()))
    c.metric("Pre clinical matches", int(df["Pre Phase 3 evidence match"].eq("EXACT TICKER + NCT").sum()))
    d.metric("Post evidence REVIEW", health.get("review_count", 0))
    with st.expander("SOURCE MATCH & SCORE COVERAGE AUDIT", expanded=False):
        audit = pd.DataFrame([
            {"Check": "Pipeline records", "Count": total},
            {"Check": "Exact pre-readout matches", "Count": pre_exact},
            {"Check": "Exact post-readout matches", "Count": post_exact},
            {"Check": "Matched in both feeds", "Count": both},
            {"Check": "Pre drug-name conflicts", "Count": pre_conflicts},
            {"Check": "Post drug-name conflicts", "Count": post_conflicts},
            {"Check": "Pre-readout ambiguous trial IDs", "Count": pre_ambiguous},
            {"Check": "Post-readout ambiguous trial IDs", "Count": post_ambiguous},
            {"Check": "Missing pre-readout match", "Count": total - pre_exact - pre_ambiguous - pre_conflicts},
            {"Check": "Missing post-readout match", "Count": total - post_exact - post_ambiguous - post_conflicts},
            {"Check": "Numeric pre-readout scores", "Count": pre_score_count},
            {"Check": "Numeric post-readout evidence scores", "Count": post_score_count},
        ])
        pdufa_dataframe(audit, use_container_width=True, hide_index=True, survey_source=src)
        st.caption("Counts use the full Pipeline universe before the user filters. Scores are not approval probabilities. Missing trial links do not establish failed clinical or financing gates.")
    with st.expander("UNMATCHED TRIAL RECONCILIATION"):
        missing = df.loc[
            df["Pre Phase 3 evidence match"].ne("EXACT TICKER + NCT")
            | df["Post evidence match"].ne("EXACT TICKER + NCT")
        ].copy()
        st.caption("Missing source links are research gaps, not clinical failures.")
        pdufa_dataframe(missing[["Ticker", "NCT ID", "Drug",
            "Pre Phase 3 evidence match", "Post evidence match"]].head(250),
            hide_index=True, use_container_width=True, survey_source=missing)
        st.download_button("EXPORT UNMATCHED RECORDS",
            missing.to_csv(index=False).encode("utf-8"),
            file_name="unmatched_trial_records.csv", mime="text/csv",
            key=f"{prefix}_missing_export")
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        phase = st.selectbox("Research phase", ["All", "PRE PHASE 3", "POST PHASE 3 / REGULATORY", "OTHER / REVIEW"], key=f"{prefix}_phase")
    with f2:
        stage_options = ["All"] + sorted(df["Pipeline stage"].dropna().unique().tolist())
        if st.session_state.get(f"{prefix}_stage", "All") not in stage_options:
            st.session_state[f"{prefix}_stage"] = "All"
        stage = st.selectbox("Stage", stage_options, key=f"{prefix}_stage")
    with f3:
        search = st.text_input("Ticker, drug, indication or NCT", key=f"{prefix}_query").strip()
    if phase != "All":
        df = df.loc[df["Research phase"].eq(phase)]
    if stage != "All":
        df = df.loc[df["Pipeline stage"].eq(stage)]
    if search and not df.empty:
        hay = df[["Ticker", "Drug", "Indication", "NCT ID"]].fillna("").astype(str).agg(" ".join, axis=1)
        df = df.loc[hay.str.contains(search, case=False, regex=False)]
    display_order = st.selectbox(
        "Display order", DISPLAY_ORDER_OPTIONS, key=f"{prefix}_pdufa_display_order",
    )
    df = sort_pdufa_grid(df, display_order)
    st.caption(
        "Top Score sorts Score /100 highest to lowest, then Days to PDUFA highest "
        "to lowest for equal scores, with missing dates last. The adjacent "
        "Score type identifies its model. Pre- and post-readout scores are not "
        "interchangeable performance or approval probabilities."
    )
    if dashboard:
        _render_command_center(df, pre, post, today=today, ticker=ticker,
                               phase=phase, stage=stage, search=search,
                               display_order=display_order, root=root)
    full_view = st.expander("ALL FIELDS — CLINICAL, SCORES & SOURCE EVIDENCE") if dashboard else st.container()
    with full_view:
        pdufa_dataframe(finance_style(df.head(350)), hide_index=True, use_container_width=True,
                 column_config={
                     "Pipeline source": st.column_config.LinkColumn("Pipeline source"),
                     "Phase 3 source": st.column_config.LinkColumn("Phase 3 source"),
                     "Financing source": st.column_config.LinkColumn("Financing source"),
                     "PDUFA source": st.column_config.LinkColumn("PDUFA source"),
                     "F": st.column_config.TextColumn("F", width="small"),
                 })
        if len(df) > 350:
            st.caption("Showing 350 rows; export contains all matching records.")
    st.download_button("EXPORT COMBINED TRIAL VIEW", df.to_csv(index=False).encode(),
                       file_name="pdufa_unified_trial_view.csv", mime="text/csv",
                       key=f"{prefix}_export")
    st.caption("Missing pre-readout scores remain blank. An exact ticker/NCT match is an identity link only, not independent clinical or SEC verification. Multiple post evidence rows for the same pair are intentionally withheld from automatic matching. Unlinked fields remain blank, not zero.")
    return ticker
