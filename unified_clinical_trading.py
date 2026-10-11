"""Read-only combined clinical-to-trading overview, no ordinal rankings."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from pipeline_universe import load_universe
from post_phase3_unified import build_queue
from step7_cached_snapshot import load_current_snapshot
from pdufa_display_columns import (POST_SCORES, PRE_SCORES, PRE_PRIORITY_SCORES,
                                  POST_PRIORITY_SCORES, prepare_pdufa_grid, sort_pdufa_grid,
                                  DISPLAY_ORDER_OPTIONS, finance_style)
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

def render_combined_overview(root="data"):
    """Render linked clinical context and return the shared ticker focus."""
    st.markdown("### UNIFIED CLINICAL → TRADING DISPLAY")
    st.caption("Pipeline + pre-readout Phase 3 + post-readout trading evidence in one view. No ordinal ranks, Top 10, or automatic orders. Clinical and financing status are not inferred from trial stage.")
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
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
                      if str(value).strip()})
    focus_options = ["All tickers", *tickers]
    focus_key = "postphase3_shared_ticker"
    if st.session_state.get(focus_key, "All tickers") not in focus_options:
        st.session_state[focus_key] = "All tickers"
    focus = st.selectbox("Focus ticker", focus_options, key=focus_key)
    ticker = None if focus == "All tickers" else focus
    st.caption(
        "This ticker selection links the clinical/pipeline display, PDUFA dates, "
        "candidate qualification, reported positions, and historical research below."
    )
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
        st.dataframe(audit, use_container_width=True, hide_index=True)
        st.caption("Counts use the full Pipeline universe before the user filters. Scores are not approval probabilities. Missing trial links do not establish failed clinical or financing gates.")
    with st.expander("UNMATCHED TRIAL RECONCILIATION"):
        missing = df.loc[
            df["Pre Phase 3 evidence match"].ne("EXACT TICKER + NCT")
            | df["Post evidence match"].ne("EXACT TICKER + NCT")
        ].copy()
        st.caption("Missing source links are research gaps, not clinical failures.")
        st.dataframe(missing[["Ticker", "NCT ID", "Drug",
            "Pre Phase 3 evidence match", "Post evidence match"]].head(250),
            hide_index=True, use_container_width=True)
        st.download_button("EXPORT UNMATCHED RECORDS",
            missing.to_csv(index=False).encode("utf-8"),
            file_name="unmatched_trial_records.csv", mime="text/csv",
            key="unified_missing_export")
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        phase = st.selectbox("Research phase", ["All", "PRE PHASE 3", "POST PHASE 3 / REGULATORY", "OTHER / REVIEW"], key="unified_phase")
    with f2:
        stage = st.selectbox("Stage", ["All"] + sorted(df["Pipeline stage"].dropna().unique().tolist()), key="unified_stage")
    with f3:
        search = st.text_input("Ticker, drug, indication or NCT", key="unified_query").strip()
    if phase != "All":
        df = df.loc[df["Research phase"].eq(phase)]
    if stage != "All":
        df = df.loc[df["Pipeline stage"].eq(stage)]
    if search:
        hay = df[["Ticker", "Drug", "Indication", "NCT ID"]].fillna("").astype(str).agg(" ".join, axis=1)
        df = df.loc[hay.str.contains(search, case=False, regex=False)]
    display_order = st.selectbox(
        "Display order", DISPLAY_ORDER_OPTIONS, key="unified_pdufa_display_order",
    )
    df = sort_pdufa_grid(df, display_order)
    st.caption(
        "Top Score shows the highest available numerical score first; the adjacent "
        "Score type identifies its model. Pre- and post-readout scores are not "
        "interchangeable performance or approval probabilities."
    )
    st.dataframe(finance_style(df.head(350)), hide_index=True, use_container_width=True,
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
                       key="unified_export")
    st.caption("Missing pre-readout scores remain blank. An exact ticker/NCT match is an identity link only, not independent clinical or SEC verification. Multiple post evidence rows for the same pair are intentionally withheld from automatic matching. Unlinked fields remain blank, not zero.")
    return ticker
