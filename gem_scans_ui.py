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
    "finance_ir_sec_recheck_targets.csv",
    "finance_ir_sec_recheck.csv",
    "gem_runway_evidence.json",
    "sec_step4_snapshots.sqlite3",
)
STAGE_COLUMNS = {
    "Phase 3": (
        "Phase 3 evidence", "Clinical evidence /30", "Trading setup /20",
        "Market activity /10", "Cash runway (months)", "Cash runway gate",
        "NCT ID", "Phase 3 source",
        "Days to PDUFA",
    ),
    "Post-Financing": (
        "2nd Financing Completed", "Financing #2", "Financing evidence /20",
        "Trading setup /20", "Market activity /10", "Cash runway (months)",
        "Cash runway gate", "Cash runway reason", "Cash runway source",
        "Financing source",
        "Days to PDUFA",
    ),
    "PDUFA": (
        "PDUFA verification", "Days to PDUFA", "PDUFA date",
        "PDUFA evidence /15", "Clinical evidence /30",
        "Financing evidence /20", "Cash runway (months)",
        "Cash runway gate", "Cash runway reason", "Cash runway source",
        "Cash runway as of", "Cash runway trend", "Cash runway previous (months)",
        "GEM 3 financial alert", "GEM 3 dilution status",
        "PDUFA source",
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
        '<th rowspan="2">Priority rank</th><th rowspan="2">Priority /100</th>'
        '<th rowspan="2">Runway (mo)</th><th rowspan="2">Runway status</th>'
        '<th rowspan="2">Two-benchmark status</th>'
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
        runway = item.get("Cash runway (months)")
        runway_label = html.escape(str(runway)) if runway is not None else "—"
        runway_status = html.escape(str(item.get("Cash runway gate") or "REVIEW"))
        gate = html.escape(str(item.get("Two-benchmark entry status") or "WATCH"))
        rank = item.get("Two-benchmark rank")
        rank_label = html.escape(str(rank)) if rank is not None else "—"
        score = item.get("Two-benchmark priority /100")
        score_label = html.escape(str(score)) if score is not None else "—"
        rows.append("<tr>" + "".join(cells) +
                    f'<td class="ticker">{ticker}</td><td>{drug}</td>'
                    f'<td>{rank_label}</td><td>{score_label}</td>'
                    f'<td>{runway_label}</td><td>{runway_status}</td><td>{gate}</td></tr>')
    return style + header + "".join(rows) + "</tbody></table></div>"


def render_gem_scans(root="data"):
    st.markdown("## GEM CANDIDATES — TWO BENCHMARKS, THEN RANK")
    st.caption(
        "The only two positive entry benchmarks are (1) dated, source-verified "
        "released Phase 3 results for the exact program, and (2) verified close "
        "of a second separate financing after that readout. Once both pass, "
        "financial runway, dilution, clinical strength, price/volume activity "
        "and PDUFA timing PRIORITIZE or WARN; they do not silently become "
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
    # Primary trading-candidate shortlist uses ONLY the two benchmark passes.
    qualified = sorted(
        (row for row in items if row.get("Two-benchmark eligible") is True),
        key=lambda r: r.get("Two-benchmark rank") or 1000000,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Phase 3 readout verified", status.get("two_benchmark_phase3_count", 0))
    m2.metric("Second financing closed", status.get("two_benchmark_financing_count", 0))
    m3.metric("Both benchmarks met", status.get("two_benchmark_candidate_count", 0))
    st.markdown("### PRIORITIZED TRADING CANDIDATES")
    st.caption(
        "Only stocks passing BOTH event benchmarks are ranked. The /100 score "
        "uses Phase 3 quality (30), runway (25), dilution risk (15), "
        "price/volume activity (20) and PDUFA timing (10). Missing evidence "
        "earns zero points within that factor, NOT automatic exclusion. "
        "Risks may still make a candidate unsuitable; this is manual review only."
    )
    ordered = [
        "Two-benchmark rank", "Ticker", "Drug", "Indication",
        "Benchmark 1 — Phase 3 released", "Benchmark 2 — Financing #2 closed",
        "Two-benchmark priority /100",
        "Phase 3 quality /30", "Financial runway /25",
        "Dilution overhang /15", "Trading activity /20", "PDUFA timing /10",
        "Cash runway (months)", "Cash runway trend", "Days to PDUFA",
        "Verified 2nd financing close date", "Two-benchmark risk flags",
        "Exact event", "Phase 3 source", "Financing source",
    ]
    if qualified:
        qtable = pd.DataFrame(qualified).reindex(columns=ordered)
        st.dataframe(qtable.head(100), use_container_width=True, hide_index=True)
        st.download_button(
            "EXPORT RANKED TWO-BENCHMARK CANDIDATES",
            qtable.to_csv(index=False).encode("utf-8"),
            file_name=f"gem_two_benchmark_ranked_{day:%Y%m%d}.csv",
            mime="text/csv", key="gem_two_benchmark_export",
        )
    else:
        st.info(
            "No program is currently source-verified as having BOTH a released "
            "Phase 3 readout and a separate second post-readout financing close. "
            "This is not a conclusion about unreviewed companies."
        )
    with st.expander("WATCHLIST — WORKING TOWARD THE TWO BENCHMARKS", expanded=False):
        remaining = [row for row in items if not row.get("Two-benchmark eligible")]
        waiting_columns = [
            "Ticker", "Drug", "Indication", "Benchmark 1 — Phase 3 released",
            "Benchmark 2 — Financing #2 closed", "Two-benchmark risk flags",
            "Exact event",
        ]
        st.dataframe(
            pd.DataFrame(remaining).reindex(columns=waiting_columns).head(250),
            use_container_width=True, hide_index=True,
        )
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
                "GEM trade entry gate", "Phase 3 GEM", "Days to PDUFA", "Phase 3 source",
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
    st.warning(
        "MANDATORY ENTRY RULE: Phase 3 and financing candidates are WATCH ONLY "
        "until the second distinct post-readout financing has actually CLOSED "
        "and its evidence has been verified for the exact program. An offering "
        "announcement, pricing, active financing or Phase 3 GEM rank is NEVER an entry signal. "
        "The 12-month cash runway gate is separately mandatory for GEM 2/3."
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

    strict = [
        item for item in items if item.get("GEM strict shortlist rank") is not None
    ]
    st.markdown("### 💎 THE FEW GEMS — ALL MANDATORY ENTRY GATES")
    st.metric("All mandatory entry gates met", len(strict))
    st.caption(
        "STRICT INTERSECTION: verified successful Phase 3 and clinical/safety "
        "requirements, confirmed price base and normalized volume, both separate "
        "post-readout financing closings independently attested with SEC sources, "
        "no unresolved dilution, >=12 months SEC cash-only runway, fresh SEC and market data, "
        "confirmed future PDUFA "
        "and at least 4 days before decision. All three GEM stages must qualify "
        "and Stage 1 must be GREEN. PASS means manual research/entry review ONLY: "
        "not an order, return prediction or guarantee of approval."
    )
    if not strict:
        st.warning(
            "NO STOCK currently passes every mandatory GEM entry gate. "
            "Watchlist remains research only; financing announcements, a "
            "single-stage rank or inaccessible SEC evidence never qualify."
        )
    else:
        shortlisted = sorted(strict, key=lambda row: row["GEM strict shortlist rank"])
        shortlist_columns = [
            "GEM strict shortlist rank", "Ticker", "Drug", "Indication",
            "Phase 3 GEM", "Post-Financing GEM", "PDUFA GEM",
            "Verified 2nd financing close date", "Cash runway (months)",
            "Cash runway gate", "Cash runway source", "Cash runway as of",
            "Cash runway trend", "GEM 3 financial alert", "Days to PDUFA",
            "PDUFA date", "Planned exit (-3 days)",
            "GEM ALL ENTRY GATES", "GEM trade entry gate", "Exact event",
            "Phase 3 source", "Financing source", "PDUFA source",
        ]
        strict_table = pd.DataFrame(shortlisted).reindex(columns=shortlist_columns)
        st.dataframe(strict_table.head(25), use_container_width=True, hide_index=True)
        st.download_button(
            "EXPORT STRICT ALL-GATE GEMS",
            strict_table.to_csv(index=False).encode("utf-8"),
            file_name=f"gem_strict_all_gates_{day:%Y%m%d}.csv",
            mime="text/csv", key="gem_strict_shortlist_export",
        )
    mode = st.radio(
        "GEMS research view",
        ("All mandatory entry gates passed", "Qualified in any research stage",
         "All candidates, including watch/review"),
        horizontal=True, key="gem_scan_row_mode",
    )
    eligible = [
        item for item in items
        if any(item[stage + " rank"] is not None for stage in STAGES)
    ]
    shown = (strict if mode.startswith("All mandatory") else
             eligible if mode.startswith("Qualified in any") else items)
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
            "No candidates currently qualify in any single research ranking. "
            "Unqualified watchlist rows remain available for evidence review."
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
                 "GEM ALL ENTRY GATES", "GEM strict shortlist rank",
                 "Phase 3 tracking", "Financing watch", "GEM trade entry gate",
                 "Verified 2nd financing close date",
                 "Cash runway (months)", "Cash runway gate",
                 "Cash runway reason", "Cash runway source",
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
        "Do not place trades from these scores alone: cash-only runway is a historical "
        "SEC estimate, not guaranteed liquidity. Valuation, dilution and "
        "independently backtested return expectations "
        "still require individual review. GEM 3 trend warnings compare only "
        "saved, dated SEC cash quarters; they do not constitute live filing alerts."
    )
