"""Manual one-button all-registered-biotech market scanner for Step 5 page."""
from __future__ import annotations

import io
import sqlite3

import pandas as pd
import streamlit as st

from market_bulk_scan import (
    BULK_COLUMNS, csv_output, parse_phase_manifest, read_bulk_results,
    run_bulk, summarize,
)
from market_step5 import DEFAULT_DB

MANIFEST_TEMPLATE = (
    "ticker,phase,phase_url,phase_date,readout_date,pdufa_date,pdufa_url,pdufa_source_date\n"
    ""
)


def render_batch_scanner(registry, analysis_date):
    valid = {ticker: value for ticker, value in registry.items()
             if value.get("cik") and not value.get("conflict")}
    st.markdown("### Scan the entire biotech stock universe")
    st.caption(
        f"{len(valid):,} registered ticker–CIK identities. "
        "A single click queues all companies (three paced concurrent workers), "
        "saves each result, and resumes unfinished attempts on another run. "
        "Expect minutes or longer; EOD providers can rate-limit or refuse requests."
    )
    st.warning(
        "Ticker/CIK matching is not proof Stooq's quote symbol represents the issuer. "
        "Without separately sourced Phase 3 status, companies receive only a "
        "**phase-neutral price/volume screening rank**, never a fabricated "
        "PRE RESULTS or POST RESULTS clinical-period score."
    )

    with st.expander("Full-universe scan controls", expanded=True):
        with st.form("all_biotech_market_scan"):
            st.write("**Every registered ticker will be included. No market-cap/date/phase filters.**")
            bulk_as_of = st.date_input(
                "Full-universe analysis date", value=analysis_date,
                max_value=analysis_date, key="bulk_step5_asof")
            workers = st.slider("Parallel market requests", min_value=1,
                                max_value=4, value=3, key="bulk_step5_workers")
            spacing = st.slider("Global minimum seconds between provider requests",
                                min_value=0.5, max_value=2.0, value=1.0, step=0.1,
                                key="bulk_step5_spacing")
            evidence_file = st.file_uploader(
                "Optional Phase 3 stage manifest (.csv). Missing rows stay UNVERIFIED.",
                type=["csv"], key="bulk_step5_stage_manifest")
            launch = st.form_submit_button("SCAN ALL REGISTERED BIOTECH STOCKS")
        st.download_button("DOWNLOAD PHASE MANIFEST EXAMPLE",
                           MANIFEST_TEMPLATE, "step5_phase_manifest_example.csv",
                           mime="text/csv")
        st.caption("Full scans may outlast a Streamlit browser session. "
                   "Already completed tickers are checkpointed in SQLite; "
                   "press SCAN ALL again after interruption to resume and retry failed tickers. "
                   "Cloud-local SQLite can be erased on restart/redeploy.")

    if launch:
        progress = st.progress(0, text="Preparing all-company scan")
        message = st.empty()
        try:
            raw_manifest = (evidence_file.getvalue().decode("utf-8-sig")
                            if evidence_file is not None else None)
            manifest = parse_phase_manifest(raw_manifest, valid)

            def on_progress(update):
                done = update["attempted"]
                total = update["total"]
                progress.progress(min(1.0, done / max(1, total)),
                                  text=f"{done:,}/{total:,} tickers checkpointed")
                message.caption(f"Most recent: {update['ticker']} — {update['status']}")

            result = run_bulk(
                bulk_as_of, identities=valid, phase_manifest=manifest,
                db_path=DEFAULT_DB, max_workers=workers,
                min_interval=spacing, on_progress=on_progress)
            progress.progress(1.0, text="All ticker attempts completed")
            failed = result["status_counts"].get("FAILED", 0)
            st.success(
                f"Scanned {result['completed_attempts']:,}/{result['roster']:,} "
                f"registered companies. Failed provider requests: {failed:,}. "
                "Use the ranked research lists and failures table below."
            )
        except (ValueError, OSError, sqlite3.Error, RuntimeError, UnicodeError) as exc:
            st.error(f"Full-universe scan interrupted: {exc}. "
                     "Previously checkpointed results remain available if local storage survives.")

    try:
        existing = read_bulk_results()
    except (OSError, sqlite3.Error) as exc:
        st.error(f"Could not read bulk market scan checkpoints: {exc}")
        return
    if not existing:
        st.info("No full-universe market scan has been saved in this runtime yet.")
        return

    current = summarize(existing, len(valid))
    counts = current["status_counts"]
    st.markdown("#### Full-universe scan coverage and results")
    a, b, c, d = st.columns(4)
    a.metric("Ticker attempts saved", f"{current['completed_attempts']:,} / {current['roster']:,}")
    b.metric("Unscanned remaining", f"{current['remaining']:,}")
    c.metric("Provider failures", f"{counts.get('FAILED', 0):,}")
    d.metric("Phase-specific scored", f"{counts.get('SCORED — PHASE REVIEWER ASSERTED', 0):,}")

    st.caption(
        "These are technical stock-screening measures, NOT biotech trial or FDA "
        "success probabilities. Missing market data or unverified phase remains labeled."
    )
    options = ["Neutral ranking — all companies with valid price bars",
               "Verified-by-review PRE RESULTS ranking",
               "Verified-by-review POST RESULTS ranking",
               "All company statuses and failures"]
    label = st.radio("Choose ranking / results", options, horizontal=False,
                     key="bulk_step5_ranking_select")
    if label.startswith("Neutral"):
        shown = current["neutral_ranking"]
    elif "PRE RESULTS" in label:
        shown = current["pre_results_ranking"]
    elif "POST RESULTS" in label:
        shown = current["post_results_ranking"]
    else:
        shown = existing
    if shown:
        preferred = ["rank", "ticker", "company", "status", "phase",
                     "neutral_price_volume_score_0_100", "phase_specific_score_0_100",
                     "close", "momentum_30_pct", "relative_volume",
                     "avg_dollar_volume_20", "volatility_20_pct",
                     "last_session", "error"]
        table = pd.DataFrame(shown)
        table = table[[col for col in preferred if col in table.columns]]
        st.dataframe(table, hide_index=True, use_container_width=True)
    else:
        st.info("No companies qualified for this view. Inspect failures and review statuses.")

    failed_rows = [r for r in existing if r["status"] == "FAILED"]
    if failed_rows:
        with st.expander(f"Provider errors / ticker mapping review ({len(failed_rows):,})"):
            st.dataframe(pd.DataFrame(failed_rows)[["ticker", "company", "error"]],
                         hide_index=True, use_container_width=True)
    st.download_button(
        "DOWNLOAD COMPLETE ALL-STOCK SCAN CSV", csv_output(existing),
        file_name="all_biotech_step5_market_scan.csv", mime="text/csv",
        key="bulk_step5_csv_download")
    st.caption("The CSV includes every ticker attempted, including failures "
               "and unscored/unverified phase rows; missing tickers remain in the "
               "coverage counter until rescanned.")
