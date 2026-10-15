"""Read-only Streamlit GEM scanner surface inside the existing SCANS sub-tab."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_scans import SCAN_QUALIFIERS, STAGES, WEIGHTS, build_gem_scans
from pipeline_universe import SOURCE_FILES as PIPELINE_SOURCE_FILES
from gem_master_list import MASTER_COLUMNS, build_gem_master_list
from gem_membership_history import read_history, enrich_gem_master_rows, departed_stage_rows
from gem_trading_advisory import (TRADE_COLUMNS, attach_trade_fields,
                                  load_market_rows, render_gem_trade_panel)
from gem_eligibility_diagnostics import GROUPS, group_counts, load_saved_rechecks, report_rows
from gem_checklist_ui import checklist_filters, render_checkbox_table, render_research_candidates
from gem_benchmark_checklist import program_key
from gem_phase3_discovery import DISCOVERY_COLUMNS, discover_phase3_results, gem_discrimination_audit
from gem_readiness_audit import build_readiness_report
from gem_calibration_ui import render_gem_calibration
from gem_survey_catalog import survey_rows

FILES = (*PIPELINE_SOURCE_FILES,
    "pdufa_candidates.csv",
    "step7_live_status.json",
    "step7_financing_review.csv",
    "second_financing_status.csv",
    "step7_market_status.csv",
    "step7_pre_phase3_feed.csv",
    "post_phase3_discoveries.csv",
    "phase3_announcements.csv",
    "finance_ir_sec_recheck_targets.csv",
    "finance_ir_sec_recheck.csv",
    "gem_runway_evidence.json",
    "gem_hedge_fund_13f.json",
    "gem_bpw_comparable.json",
    "gem_insider_form4.json",
    "gem_hedge_fund_managers.csv",
    "sec_step4_snapshots.sqlite3",
)

@st.cache_data(ttl=120, show_spinner=False)
def _saved_gem_scans(root, signature, pacific_day):
    # Source file signature, plus local calendar day, prevents a cached
    # "current" rating from surviving an updated feed or Pacific midnight.
    return build_gem_scans(root, as_of=pacific_day)


@st.cache_data(ttl=120, show_spinner=False)
def _discovery(root, signature, pacific_day):
    return discover_phase3_results(root, as_of=pacific_day)


def render_gem_scans(root="data"):
    st.markdown("## GEM — MASTER STOCK LIST")
    st.caption(
        "The only two positive entry benchmarks are (1) dated, source-verified "
        "released Phase 3 results for the exact program, and (2) verified close "
        "of a second separate financing after that readout. Once both pass, "
        "financial runway, dilution, clinical strength, price/volume activity, "
        "PDUFA timing and quarterly SEC hedge-fund holdings PRIORITIZE or WARN; "
        "they do not silently become "
        "additional entry benchmarks. Scores are research heuristics, not "
        "approval probabilities, stock-return forecasts or trade orders."
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

    excluded = status.get("excluded_outside_pipeline", 0)
    st.caption(
        f"PIPELINE ORIGIN CONTROL · {len(items):,} tracked GEM leads · "
        f"{excluded:,} outside-Pipeline source leads withheld. "
        "GEM JR and GEM may enrich or qualify existing Pipeline IDs only."
    )
    if excluded:
        st.warning("New source leads were excluded because no exact Pipeline "
                   "application or trial identity exists yet. Add and reconcile "
                   "them in Pipeline first; they are not new GEM records.")
    if not status.get("feed_current"):
        st.warning(
            "SOURCE SNAPSHOT STALE: refresh saved clinical and market data. "
            "Previously verified results remain labeled, but their evidence "
            "may no longer reflect current trading circumstances."
        )
    if not status.get("sec_financing_source_current"):
        st.warning(
            "SEC FINANCING RECHECK PARTIAL/STALE: an already attested closing "
            "must be reconfirmed before relying on it. This is a source-quality "
            "warning, not a third fundamental entry benchmark."
        )
    st.caption(
        f"Saved data as of (Pacific): {status.get('as_of', 'unknown')} · "
        "Scan output derives from existing clinical, SEC, FDA and market "
        "evidence. This button-free read-only view does not dispatch a new scan."
    )
    qualified = sorted(
        (row for row in items if row.get("Two-benchmark eligible") is True),
        key=lambda r: r.get("Two-benchmark rank") or 1000000,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Phase 3 readout verified", status.get("two_benchmark_phase3_count", 0))
    m2.metric("Second financing closed", status.get("two_benchmark_financing_count", 0))
    m3.metric("Both benchmarks met", status.get("two_benchmark_candidate_count", 0))
    st.markdown("### GEM — UNIFIED MASTER LIST")
    st.caption(
        "ONE stock-program list for Phase 3 → Post-Financing → PDUFA. "
        "Only the two verified event benchmarks unlock GEM eligibility and "
        "the 100-point priority rank. The GEM Stage is a descriptive research "
        "milestone, NOT an extra eligibility condition. The PDUFA stage means "
        "a verified date within 90 calendar days; the trading exit warning "
        "begins at PDUFA −3. Other risk factors only rank or warn."
    )
    membership = read_history(path)
    master_rows = enrich_gem_master_rows(build_gem_master_list(items), membership)
    # Disclose precisely why a program is unscored. The standalone source
    # rechecks below are research observations, never automatic promotions.
    details = report_rows(
        master_rows,
        sec_current=bool(status.get("sec_financing_source_current")),
        feed_current=bool(status.get("feed_current")),
        rechecks=load_saved_rechecks(path, "gem_two_close_recheck.csv"),
        clinical_rechecks=load_saved_rechecks(path, "gem_phase3_exact_recheck.csv"),
    )
    counts_by_group = group_counts(details)
    st.markdown("### GEM ELIGIBILITY — WHY STOCKS ARE ON HOLD")
    a, b, c, d = st.columns(4)
    for panel, title in zip((a, b, c, d), GROUPS):
        panel.metric(title, counts_by_group[title])
    if not status.get("sec_financing_source_current"):
        st.warning(
            "Historical financing records are NOT current SEC confirmations. "
            "A blocked/stale SEC collector does not prove a transaction failed. "
            "New source rechecks do not automatically refresh the original "
            "two-close attestation or upgrade GEM eligibility."
        )
    st.caption(
        "These groups use exactly the two required events, not cash runway, "
        "market momentum or PDUFA timing. Registry postings are discovery "
        "only; a dated successful issuer Phase 3 readout still needs verification."
    )
    with st.expander("EACH PROGRAM — MISSING VERIFICATION & LATEST SOURCE AUDITS",
                     expanded=True):
        audit_columns = [
            "Ticker", "Drug", "Verification group", "Missing / recheck needed",
            "Phase 3 Verified", "Second Financing Closed",
            "Latest Phase 3 registry audit", "Registry audit needed",
            "Latest SEC transaction audit", "Current SEC source",
            "Phase 3 Result Date", "Second Financing Close Date",
            "Phase 3 Source", "Financing Source", "Exact Program / Event",
        ]
        table = pd.DataFrame(details).reindex(columns=audit_columns)
        st.dataframe(table, use_container_width=True, hide_index=True, height=420,
                     column_config={
                         "Phase 3 Source": st.column_config.LinkColumn("Phase 3 Source"),
                         "Financing Source": st.column_config.LinkColumn("Financing Source"),
                     })
        st.download_button(
            "EXPORT GEM VERIFICATION GAPS — ALL STOCKS",
            table.to_csv(index=False).encode("utf-8"),
            file_name=f"gem_verification_gaps_{day:%Y%m%d}.csv",
            mime="text/csv", key="gem_verification_gaps_download",
        )
    if not load_saved_rechecks(path, "gem_two_close_recheck.csv"):
        st.caption("Fresh SEC two-close document recheck not yet published; "
                   "saved historical attestations remain research only.")
    if not load_saved_rechecks(path, "gem_phase3_exact_recheck.csv"):
        st.caption("Exact-NCT Phase 3 source recheck not yet published; "
                   "registry discovery is not a verified issuer readout.")

    umbrella_rows, checkbox_states = checklist_filters(
        master_rows, items,
        financing_rechecks=load_saved_rechecks(path, "gem_two_close_recheck.csv"),
        clinical_rechecks=load_saved_rechecks(path, "gem_phase3_exact_recheck.csv"),
        status=status, namespace="gem_scan",
    )
    source_leads = render_research_candidates(
        master_rows, checkbox_states,
        financing_rechecks=load_saved_rechecks(path, "gem_two_close_recheck.csv"),
        clinical_rechecks=load_saved_rechecks(path, "gem_phase3_exact_recheck.csv"),
        namespace="gem_scan_research",
    )
    research_keys = {item["_event_id"] for item in source_leads}
    with st.expander("GEM BENCHMARK & RISK CHECKBOXES — ALL MATCHING STOCKS",
                     expanded=True):
        checkbox_grid = render_checkbox_table(
            umbrella_rows, checkbox_states, height=400,
        )
        st.download_button(
            "EXPORT ALL GEM CHECKBOXES",
            checkbox_grid.to_csv(index=False).encode("utf-8"),
            mime="text/csv", file_name=f"gem_checklist_{day:%Y%m%d}.csv",
            key="gem_master_checkbox_export",
        )

    gem_view = st.radio(
        "GEM list filter",
        ("Research candidates (source leads)", "All GEM programs", "Entry-eligible only", "Watch / review"),
        horizontal=True, key="gem_master_filter",
    )
    f1, f2 = st.columns([2, 1])
    with f1:
        gem_search = st.text_input(
            "Find GEM ticker, drug, indication or event",
            value="", key="gem_master_search",
        ).strip().casefold()
    with f2:
        stage_filter = st.selectbox(
            "GEM stage", ("All stages", "Phase 3", "Post-Financing",
                         "PDUFA", "Research / Unverified"),
            key="gem_master_stage",
        )
    display_rows = [
        row for row in umbrella_rows
        if ((gem_view == "All GEM programs")
            or (gem_view == "Research candidates (source leads)" and program_key(row) in research_keys)
            or (gem_view == "Entry-eligible only" and row["_eligible"])
            or (gem_view == "Watch / review" and not row["_eligible"]))
        and (stage_filter == "All stages" or row["GEM Stage"] == stage_filter)
        and (not gem_search or any(gem_search in str(row.get(field) or "").casefold()
             for field in ("Ticker", "Drug", "Indication", "Exact Program / Event")))
    ]
    market_rows = load_market_rows(path)
    displayed_trades = attach_trade_fields(display_rows, market_rows, status, day)
    master_table = pd.DataFrame(displayed_trades).reindex(columns=MASTER_COLUMNS + TRADE_COLUMNS)
    st.caption(
        f"Showing all {len(master_table):,} matching GEM programs "
        f"({len(master_rows):,} total before filters). "
        "Eligible records sort by GEM rank first; watch and unverified "
        "programs remain visible below. A blank rank is NOT a zero score. "
        "Use the export for ALL matching rows."
    )
    st.dataframe(master_table, use_container_width=True, height=650,
                 hide_index=True)
    st.download_button(
        "EXPORT GEM MASTER LIST",
        master_table.to_csv(index=False).encode("utf-8"),
        file_name=f"gem_master_{day:%Y%m%d}.csv",
        mime="text/csv", key="gem_master_export",
    )
    st.markdown("### EACH GEM — PRICE CHART + ENTRY / EXIT RECOMMENDATION")
    st.caption("Select any matching exact program to inspect its saved EOD price history, "
               "indicator checks, source freshness and risk reason. Every row above "
               "also includes its trade assessment for sorting/export; incomplete "
               "verification stays WAIT, not a buy call.")
    if display_rows:
        selected_idx = st.selectbox(
            "Select GEM stock / exact program",
            range(len(display_rows)),
            format_func=lambda n: (
                str(display_rows[n].get("Ticker") or "?") + " · " +
                str(display_rows[n].get("Drug") or "?") + " · " +
                str(display_rows[n].get("Exact Program / Event") or "?")
            ),
            key="gem_master_trade_detail",
        )
        render_gem_trade_panel(display_rows[selected_idx], market_rows, status, day)
    else:
        st.caption("No matching program selected. Change the GEM list filter.")
    if not qualified and gem_view == "Entry-eligible only" and research_keys:
        st.info("Verified GEM count is zero, but research candidates are "
                "available above. Choose Research candidates (source leads) "
                "to display them in the master list.")
    if not qualified:
        st.info(
            "No saved program currently has BOTH required independently verified "
            "events. The complete GEM watch/review universe remains visible "
            "above; missing evidence is never treated as a failed trial."
        )
    comparable_file = path / "gem_bpw_comparable.json"
    try:
        comparison = json.loads(comparable_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        comparison = {}
    comparison_current = (
        comparison.get("schema_version") == 1
        and comparison.get("as_of_pacific") == day.isoformat()
        and isinstance(comparison.get("capability_matrix"), list)
    )
    with st.expander("GEM SURVEY DIRECTORY — 7 PRIMARY SURVEYS", expanded=False):
        st.caption(
            "Seven GEM survey categories covering Pipeline-origin programs. "
            "Only 1 (Phase 3) and 2 (second financing) determine GEM research "
            "qualification. 13F and Form 4 evidence share one advisory category "
            "but retain distinct sources. Market cap stays in Pipeline; "
            "unvalidated historical returns and BPW comparison are RESEARCH "
            "DIAGNOSTICS, not daily surveys."
        )
        st.caption(
            f"Saved-source observations: {len(items):,} exact Pipeline-linked "
            "GEM research programs. Survey coverage uses the GEM data directly "
            "(not BPW). Missing/late evidence is not an automatic PASS; "
            "one company may have multiple exact programs."
        )
        if not status.get("feed_current"):
            st.warning("GEM source feed stale/partial — survey observations "
                       "require a current source recheck before trading review.")
        st.dataframe(
            pd.DataFrame(survey_rows({}, scans=items,
                                     feed_current=status.get("feed_current"))),
            use_container_width=True, hide_index=True,
        )

    with st.container(border=True, key="gem_ownership_insider_card"):
        st.markdown("### OWNERSHIP & INSIDER ACTIVITY — ADVISORY")
        st.caption("A single survey category, with SEC 13F holdings and Form 4 "
                   "insider reports checked and displayed independently.")
        st.markdown("#### HEDGE-FUND OWNERSHIP — SEC 13F")
        h1, h2 = st.columns(2)
        h1.metric("Candidates with specialist 13F matches",
                  status.get("hedge_fund_13f_matched_candidates", 0))
        h2.metric("Companies with at least one manager increasing",
                  status.get("hedge_fund_accumulating_candidates", 0))
        st.caption(
            "Initial monitored managers: Baker Bros., RA Capital, OrbiMed and "
            "Perceptive Advisors. 13F shows reported long positions as of quarter "
            "end; filings can arrive up to 45 days later. Reported changes are "
            "NOT proof of purchases made today, and absence is not proof of "
            "zero hedge-fund ownership. These signals never change the two "
            "entry benchmarks."
        )
        with st.expander("ALL WATCHLIST 13F MANAGER DETAILS AND SOURCES", expanded=False):
            hcols = ["Ticker", "Drug", "Hedge-fund signal",
                     "Hedge-fund accumulation /10", "Hedge-fund managers holding",
                     "Hedge-fund managers adding", "Hedge-fund managers reducing",
                     "Hedge-fund managers new", "Hedge-fund managers no longer reported",
                     "Hedge-fund quarter end", "Hedge-fund filed as of",
                     "Hedge-fund position details", "Hedge-fund source links",
                     "Hedge-fund limitation"]
            st.dataframe(pd.DataFrame(items).reindex(columns=hcols).head(250),
                         use_container_width=True, hide_index=True)
        st.markdown("#### INSIDER TRADING — SEC FORM 4 SOURCE REVIEW")
        st.caption(
            "Reported, priced open-market common-share purchase (P) and sale (S) "
            "transactions from company-matched Form 4 XML. Grants, exercises "
            "and unverified filings do not create a buy signal. This is an "
            "advisory research factor, not a new entry requirement or part of "
            "the currently unvalidated 100-point weights."
        )
        st.metric("Watchlist rows with verified insider source review",
                  status.get("insider_form4_covered_rows", 0))
        insider_fields = ["Ticker", "Drug", "Insider Form 4 signal",
                          "Insider open-market purchases", "Insider open-market sales",
                          "Insider purchase amount USD", "Insider sale amount USD",
                          "Insider net reported amount USD", "Insider buyers",
                          "Insider last filing date", "Insider filings reviewed",
                          "Insider source links", "Insider risk note"]
        with st.expander("FORM 4 PURCHASES, SALES, SOURCE LINKS AND GAPS", expanded=False):
            st.dataframe(pd.DataFrame(items).reindex(columns=insider_fields).head(250),
                         use_container_width=True, hide_index=True)
    st.divider()
    # Research confirmations remain visible while the nightly SEC collector
    # independently rechecks each dated transaction. Neither the research
    # ledger nor a one-transaction SEC match can unlock the GEM entry gate.
    st.markdown("### PUBLIC / INVESTOR SOURCE CONFIRMATIONS → FRESH SEC RECHECK")
    st.caption(
        "Public and company-site findings stay recorded even when SEC has not "
        "confirmed a closing. Only exact-company and exact-date SEC evidence "
        "can upgrade the independent transaction check. The second distinct "
        "post-Phase-3 financing confirmation is still required. Dilution "
        "is now an advisory risk/ranking factor, not a third entry benchmark."
    )
    with st.expander("RESEARCH STATUS — ALL 45 REVIEWED CLAIMS", expanded=False):
        research_file = (
            Path(__file__).resolve().parent / "reports" / "missing_sources" /
            "public_web_cross_check_2026-10-13.csv"
        )
        if research_file.is_file():
            try:
                reviewed = pd.read_csv(research_file, dtype=str).fillna("")
                fields = [
                    "event_key", "category", "claim",
                    "ir_full_45_review_status", "ir_full_45_evidence",
                    "ir_full_45_source_links",
                ]
                st.dataframe(reviewed.reindex(columns=fields),
                             use_container_width=True, hide_index=True)
                st.caption(
                    f"{len(reviewed):,} public research rows. A REVIEWED row "
                    "is not proof a financing closed; some contain only pricing, "
                    "older financing or unrelated acquisition evidence."
                )
            except (OSError, ValueError, pd.errors.ParserError):
                st.warning("Public research ledger could not be displayed.")
        else:
            st.info("No saved public/Investor Relations research ledger available.")
    with st.expander("FINANCING CLOSE DATE LEADS — SEC RECHECK QUEUE",
                     expanded=False):
        leads_file = path / "finance_ir_sec_recheck_targets.csv"
        if leads_file.is_file():
            try:
                leads = pd.read_csv(leads_file, dtype=str).fillna("")
                st.dataframe(leads, use_container_width=True, hide_index=True)
                st.caption(
                    "Each row is a dated public-source transaction lead, not an "
                    "independently qualified second post-Phase-3 financing."
                )
            except (OSError, ValueError, pd.errors.ParserError):
                st.warning("SEC recheck lead queue could not be displayed.")
        else:
            st.info("No dated IR/SEC recheck leads published in this build.")
    with st.expander("LATEST SAVED FRESH SEC TRANSACTION RECHECKS",
                     expanded=False):
        fresh_file = path / "finance_ir_sec_recheck.csv"
        if fresh_file.is_file():
            try:
                recent_checks = pd.read_csv(fresh_file, dtype=str).fillna("")
                st.dataframe(recent_checks, use_container_width=True,
                             hide_index=True)
                st.caption(
                    "SEC_TRANSACTION_VERIFIED confirms only the named closing. "
                    "Even two matching company transactions do not bypass the "
                    "separate exact-event Phase 3 timing check. Dilution is a "
                    "ranking/risk factor rather than an entry benchmark."
                )
            except (OSError, ValueError, pd.errors.ParserError):
                st.warning("Published SEC recheck results could not be read.")
        else:
            # The source publisher stores SEC rechecks inside the existing
            # signed-off source-report JSON, avoiding extra workflows.
            source_report_file = path / "pdufa_source_report.json"
            try:
                published = (json.loads(source_report_file.read_text(encoding="utf-8"))
                             if source_report_file.is_file() else {})
                findings = published.get("public_ir_sec_recheck") or {}
                if (findings.get("status") == "COMPLETE_RESEARCH_ONLY"
                        and findings.get("results")):
                    st.dataframe(
                        pd.DataFrame(findings["results"]),
                        use_container_width=True, hide_index=True
                    )
                    st.caption(
                        f"{findings.get('leads_checked', 0)} dated IR leads SEC-rechecked; "
                        f"{findings.get('sec_transactions_verified', 0)} individual SEC "
                        "transactions confirmed. This is NOT confirmation of two "
                        "post-Phase-3 financings or approval to trade."
                    )
                else:
                    st.info(
                        "SEC recheck publication: " +
                        str(findings.get("status", "NOT YET AVAILABLE")) +
                        ". Public findings remain recorded; no new trade entry "
                        "is permitted from provisional research."
                    )
            except (OSError, ValueError, TypeError, pd.errors.ParserError):
                st.warning("SEC recheck source-report snapshot is unavailable.")
    counts = status["scan_counts"]
    st.caption(
        "Cash runway is a ranking factor, NOT a minimum trading-entry benchmark. "
        f"{status.get('cash_runway_passing_count', 0)} passes and "
        f"{status.get('cash_runway_unverified_count', 0)} missing/stale sources; "
        f"{status.get('cash_runway_deteriorating_count', 0)} declining runway trends; "
        f"{status.get('gem3_dilution_alert_count', 0)} dilution alerts. "
        "Pre-close cash statements, restricted cash and missing SEC facts receive "
        "no qualifying financial-runway ranking points."
    )
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
    st.caption(
        "Phase 3 watch programs stay in the ONE GEM master table; they are "
        "never promoted to entry-ready by a Phase 3 readout alone. The "
        "second separate financing must be verified closed."
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
    with st.expander("OPTIONAL STAGE-SPECIFIC RESEARCH CHECKS — AUDIT ONLY",
                     expanded=False):
        st.caption(
            "Legacy Phase 3, Post-Financing and PDUFA scorecards remain "
            "available in the underlying source audit. They do NOT create "
            "three trading lists or add requirements to GEM eligibility. "
            "The sole GEM /100 trading priority is shown in the master list."
        )
        for stage in STAGES:
            st.write(
                f"{stage}: {counts[stage]['qualified']:,} with complete optional "
                f"research-stage gates; {counts[stage]['review']:,} requiring review."
            )
            st.caption(
                "Optional historical rubric: " +
                "; ".join(f"{column}: {points} points"
                          for column, points in WEIGHTS[stage].items())
            )
            with st.expander(stage + " — optional qualifier definitions",
                             expanded=False):
                for index, qualifier in enumerate(SCAN_QUALIFIERS[stage], 1):
                    st.write(f"{index}. {qualifier}")
        st.write(
            "Programs meeting every old, stricter research filter:",
            status.get("strict_entry_gate_shortlist_count", 0),
        )
        st.caption(
            "These are diagnostic gates, not the two-entry-benchmark GEM policy. "
            "No separate qualified-stock list is generated here."
        )
    st.caption(
        "Your planned exit remains three days before PDUFA. A decision date "
        "at or inside that boundary is a serious timing warning, rather than "
        "a third qualification benchmark. The separate legacy Stage 1 "
        "workspace still has an older -7 entry filter; it is not the "
        "two-benchmark GEM eligibility policy."
    )
    discrimination = gem_discrimination_audit(items, STAGES)
    with st.expander("GEM RANKING QUALITY — TIES & EVIDENCE LIMITS", expanded=False):
        st.dataframe(pd.DataFrame([
            {
                "Research stage": stage,
                "Optional qualified": discrimination[stage]["qualified"],
                "Distinct scores": discrimination[stage]["unique_scores"],
                "Stocks tied on score": discrimination[stage]["tied_candidates"],
                "Largest tie": discrimination[stage]["largest_tied_group"],
                "Status": discrimination[stage]["status"].replace("_", " "),
            } for stage in STAGES
        ]), use_container_width=True, hide_index=True)
        st.caption(
            "This is the diagnostic quality of legacy stage-specific evidence "
            "rubrics, NOT three separate GEM stock rankings. Historical GEM "
            "calibration must be validated before changing master-score weights."
        )
    st.divider()
    st.markdown("### RESEARCH DIAGNOSTICS — NOT NIGHTLY SURVEYS")
    st.caption(
        "Optional source-coverage comparison and historical score calibration "
        "are available for manual review. They do not create Pipeline records, "
        "GEM eligibility, trading returns, or nightly scan pass requirements."
    )
    if st.toggle("SHOW BIOPHARMAWATCH FEATURE-COVERAGE DIAGNOSTIC",
                 value=False, key="gem_show_bpw_diagnostic"):
        if not comparison_current:
            st.info("A same-day BPW-style source coverage comparison is not yet published.")
        else:
            st.caption(
                "Comparison is of GEM's source-data COVERAGE against BPW's advertised "
                "capabilities, not a head-to-head performance test or proprietary "
                "PoA score comparison. Missing data is reported, never fabricated."
            )
            st.dataframe(
                pd.DataFrame(comparison["capability_matrix"])[
                    ["capability", "state", "observed_gem_rows",
                     "total_gem_rows", "data_coverage_pct", "caveat"]
                ], use_container_width=True, hide_index=True
            )
            st.download_button(
                "DOWNLOAD GEM vs BPW COMPARISON",
                json.dumps(comparison, indent=2).encode("utf-8"),
                file_name=f"gem_bpw_comparable_{day:%Y%m%d}.json",
                mime="application/json", key="gem_bpw_comparable_json_export",
            )

        st.link_button("RUN OPTIONAL BPW RESEARCH DIAGNOSTIC",
                       "https://github.com/pdufa/pdufa-command-center/actions/workflows/gem-research-diagnostics.yml")
    if st.toggle("SHOW HISTORICAL GEM BACKTEST / CALIBRATION",
                 value=False, key="gem_show_historical_diagnostic"):
        render_gem_calibration(root)
    st.caption(
        "Qualification here means a source-supported research ranking only. "
        "Do not place trades from these scores alone: cash-only runway is a historical "
        "SEC estimate, not guaranteed liquidity. Valuation, dilution and "
        "independently backtested return expectations "
        "still require individual review. GEM 3 trend warnings compare only "
        "saved, dated SEC cash quarters; they do not constitute live filing alerts."
    )
    st.markdown("### GEM — PREVIOUS CANDIDATES")
    st.caption("Each prior GEM program keeps its exact Pipeline ID, first-found "
               "date, date left, PDUFA date, and actual departure reason. "
               "A PDUFA −3 trading warning does not end stage membership.")
    with st.expander("OPEN PREVIOUS GEM CANDIDATES", expanded=False):
        departed = departed_stage_rows(membership, "GEM")
        if departed:
            st.dataframe(pd.DataFrame(departed), hide_index=True,
                         use_container_width=True)
        else:
            st.caption("No previous GEM candidates recorded by a complete scan yet.")
