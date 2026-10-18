"""Always-visible #1 GEM potential list with specific, source-grounded reasons."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from gem_trading_advisory import load_market_rows, render_base_chart_for_ticker

import pandas as pd
import streamlit as st

from gem_potential_list import build_potential_list
from gem_trial_hierarchy_ui import render_trial_hierarchy
from gem_membership_history import read_history, enrich_stage_rows, departed_stage_rows
from gem_financing_batch_review import build_financing_review
from gem_verified_snapshot import source_cleared_gems
from stage_wt_tables import render_stage_wt_tables
from gem_secondary_research import (
    OPTIONAL_CHECK_TOPICS, optional_check_search_links,
    research_search_links, source_research_policy,
)

VISIBLE = ("Ticker", "Drug", "Pipeline ID", "Date Found", "Date Left",
           "Why potential", "Still needed", "Timing / resolution")
FULL = (
    "Ticker", "Drug", "Indication", "Why potential", "Still needed",
    "Evidence type", "GEM status", "SEC documents rechecked", "NCT ID",
    "PDUFA date (saved)", "Timing / resolution", "Exact program",
    "Clinical source", "Financing SEC source", "Source review date",
    "Pipeline ID", "Date Found", "Date Left", "Date Re-entered",
    "Leave Reason", "Listing status",
)


def research_program_label(lead):
    """Display exact-program identity for either source-cleared or research GEMs.

    Source-cleared records use 'NCT ID' / 'Exact program' just like pending
    research records; never index a different list from a selector callback.
    """
    return (
        str(lead.get("Ticker") or "?") + " · " +
        str(lead.get("Drug") or "?") + " · " +
        str(lead.get("NCT ID") or lead.get("Exact program") or "")
    )


def numbered_potential_markdown(potential):
    """One compact ordered list, with a source-based reason and remaining work."""
    lines = []
    for number, lead in enumerate(potential, 1):
        ticker = str(lead.get("Ticker") or "UNKNOWN").replace("*", r"\*")
        drug = str(lead.get("Drug") or "").replace("*", r"\*")
        reason = str(lead.get("Why potential") or "No documented reason yet")
        pending = str(lead.get("Still needed") or "Further source verification")
        lines.extend((
            f"{number}. **{ticker} · {drug}**",
            f"   - **Why potential:** {reason}",
            f"   - **Pending:** {pending}",
            "",
        ))
    return "\n".join(lines)


def render_gem_potential(root="data", *, compact=False, namespace="gem_potential",
                         show_previous=True):
    """Keep pending research stocks separate from proven GEM eligibility.

    This view updates from saved review files, never launches a scan or
    reinterprets a historical funding claim as an entry authorization.
    """
    potential, timing_hold = build_potential_list(root)
    source_cleared, historical_cleared, sec_global_current = source_cleared_gems(root)
    cleared_programs = {x["Exact program"] for x in source_cleared + historical_cleared}
    potential = [x for x in potential if x["Exact program"] not in cleared_programs]
    timing_hold = [x for x in timing_hold if x["Exact program"] not in cleared_programs]
    membership = read_history(root)
    source_cleared = enrich_stage_rows(source_cleared, "GEM", membership)
    historical_cleared = enrich_stage_rows(historical_cleared, "GEM", membership)
    potential = enrich_stage_rows(potential, "GEM_JR", membership)
    timing_hold = enrich_stage_rows(timing_hold, "GEM_JR", membership)

    # GEM active cards require source-verified successful Phase 3. JR research,
    # expired/resolved items and historical holds do not appear in active GEM.
    render_trial_hierarchy(source_cleared, namespace=namespace, title="GEM")
    st.markdown("### GEM — VERIFIED SUCCESSFUL PHASE 3")
    st.caption(
        f"{len(source_cleared)} ACTIVE PROGRAMS VERIFIED · "
        f"{len(historical_cleared)} HISTORICAL / RESOLVED. "
        "These are exact-event source-audited research qualifications, "
        "NOT authorized trade entries."
    )
    if source_cleared:
        for count, lead in enumerate(source_cleared, 1):
            st.markdown(
                f"{count}. **{lead['Ticker']} · {lead['Drug']}** "
                "— Successful Phase 3 verified; financing #2 optional"
            )
            st.caption(
                "Phase 3 " + lead["Phase 3 date"] + " · " + lead["NCT ID"] +
                " · 1st closing " + lead["First close"] +
                " · 2nd closing " + lead["Second close"]
            )
            st.caption(
                "PDUFA " + str(lead["PDUFA saved"] or "NOT CONFIRMED") +
                " · " + (str(lead["PDUFA days left"]) + " DAYS LEFT" if
                         lead["PDUFA days left"] is not None else "DATE UNKNOWN") +
                " · " + lead["PDUFA timing window"] +
                " · " + ("SOURCE VERIFIED" if lead["PDUFA verified"]
                         else "PDUFA SOURCE NOT VERIFIED") +
                " · EXIT: " + (lead["Planned exit (PDUFA −3)"] or "UNVERIFIED")
            )
            st.caption("GEM first found: " + lead["Date Found"] +
                       " · Left: " + (lead["Date Left"] or "CURRENTLY LISTED") +
                       " · Re-entered: " + (lead["Date Re-entered"] or "—"))
            st.caption(lead["Still needed"])
        with st.expander("VERIFIED GEM PRIMARY SOURCES — EXACT PROGRAM", expanded=False):
            st.dataframe(
                pd.DataFrame(source_cleared), hide_index=True,
                use_container_width=True, height=265,
                column_config={
                    "Phase 3 source": st.column_config.LinkColumn("Phase 3 source"),
                    "First SEC source": st.column_config.LinkColumn("First SEC source"),
                    "Second SEC source": st.column_config.LinkColumn("Second SEC source"),
                },
            )
    else:
        st.caption("No source-cleared successful Phase 3 GEMs in current saved evidence.")
    if historical_cleared:
        with st.expander(
            f"VERIFIED HISTORICAL GEM EVIDENCE — NOT TRADABLE ({len(historical_cleared)})",
            expanded=False,
        ):
            for lead in historical_cleared:
                st.markdown("**" + lead["Ticker"] + " · " + lead["Drug"] + "**")
                st.caption(lead["Still needed"])
    if not sec_global_current:
        st.warning(
            "GLOBAL SEC SOURCE CHECK PARTIAL/STALE — verified program-level "
            "evidence does not clear fresh all-source trading-entry gates."
        )
    # GEM WT only shows active, exact-program, successful Phase 3 leads.
    # Research leads remain in GEM JR and do not inherit GEM eligibility.
    render_stage_wt_tables(
        "GEM", source_cleared, namespace="gem", controls=True)
    # The full financing-stage scope is broader than historical two-close
    # attestations; EVERY distinct exact program stays visible for follow-up.
    financing_worklist, financing_audit = build_financing_review(root)
    st.caption(
        f"FINANCING-STAGE REVIEW · {financing_audit['financing_programs_reviewed']} "
        f"exact programs / {financing_audit['unique_tickers']} tickers · "
        f"{financing_audit['active_benchmark_cleared']} active 2/2 "
        f"source-cleared · {financing_audit['pending_or_excluded']} "
        "pending/excluded · "
        f"{financing_audit['financing_programs_with_matched_phase3_source_leads']} "
        "with registry/issuer discovery leads"
    )
    with st.expander(
        "ALL FINANCING-STAGE COMPANIES — EVIDENCE, GAPS & SOURCE SEARCH",
        expanded=False,
    ):
        st.caption(
            "Full financing-block coverage, including 1-close, no-close and "
            "program-mapping cases. Source-search links do NOT verify findings "
            "or turn a historical claim into a GEM clearance. "
            "NO trades authorized from this worklist."
        )
        visible_fields = (
            "Ticker", "Drug", "Exact program", "Review status",
            "Phase 3 source-clear", "Phase 3 readout date",
            "Matched Phase 3 source leads", "Phase 3 discovery examples",
            "Phase 3 discovery source",
            "Financing ledger claim", "Financing close #1",
            "Financing close #2", "PDUFA (saved)", "PDUFA days left",
            "PDUFA window", "PDUFA date verified",
            "Missing evidence / next actions", "PDUFA primary source",
            "Primary clinical source", "Financing source #1",
            "Financing source #2", "Investor news / source search",
            "SEC program search", "ClinicalTrials.gov search",
            "Reddit leads (not evidence)",
        )
        detail = pd.DataFrame(financing_worklist).reindex(columns=visible_fields)
        st.dataframe(
            detail, use_container_width=True, hide_index=True, height=410,
            column_config={
                name: st.column_config.LinkColumn(name)
                for name in (
                    "Primary clinical source", "PDUFA primary source",
                    "Phase 3 discovery source",
                    "Financing source #1",
                    "Financing source #2", "Investor news / source search",
                    "SEC program search", "ClinicalTrials.gov search",
                    "Reddit leads (not evidence)",
                )
            },
        )
        st.download_button(
            "EXPORT COMPLETE FINANCING-STAGE GEM REVIEW",
            data=detail.to_csv(index=False).encode("utf-8"),
            file_name="gem_full_financing_stage_review.csv",
            mime="text/csv", key=namespace + "_financing_stage_export",
        )

    st.markdown("### POTENTIAL GEMs — PENDING RESEARCH")
    st.caption(
        "Research leads under #1, NOT the verified GEM entry list. "
        "Each reason comes from saved Phase 3/SEC observations and shows "
        "what still needs verification. No automatic trading or inferred approvals."
    )
    st.caption(f"{len(potential)} active research leads · {len(timing_hold)} "
               "at/past exit or resolved · 0 additional entries authorized by this list")
    if not potential:
        st.info("No currently active potential GEMs supported by the saved source reviews.")
    elif compact:
        # A single readable, numbered list beats narrow multi-column tables
        # and disconnected ticker cards inside the one-quarter-width #1 panel.
        with st.container(height=355, border=False):
            st.markdown(numbered_potential_markdown(potential))
    else:
        st.dataframe(
            pd.DataFrame(potential).reindex(columns=VISIBLE),
            use_container_width=True, hide_index=True, height=410,
            column_config={
                "Why potential": st.column_config.TextColumn("Why potential", width="large"),
                "Still needed": st.column_config.TextColumn("Still needed", width="large"),
            },
        )
    research_universe = source_cleared + potential
    if compact and research_universe:
        with st.expander("GEM — OPEN STOCK BASE / SUPPORT CHART", expanded=False):
            tickers = sorted({str(x.get("Ticker") or "").upper().strip()
                              for x in research_universe if x.get("Ticker")})
            chosen = st.selectbox("GEM stock to chart", tickers,
                                  key=namespace + "_base_stock")
            render_base_chart_for_ticker(
                chosen, load_market_rows(root),
                datetime.now(ZoneInfo("America/Los_Angeles")).date(),
            )
            st.caption("Both research-only leads and Phase 3-verified GEM programs "
                       "are shown here; a technical base cannot establish GEM eligibility.")
    if research_universe:
        with st.expander("INVESTOR RELATIONS + SOCIAL RESEARCH — SELECT GEM PROGRAM",
                         expanded=False):
            st.caption(
                "Investigate non-benchmark checks here: cash/runway, insider "
                "activity, dilution, trading attention, discussion and catalysts. "
                "Source links open a search or the company's known official "
                "Investor Relations/news page; this panel DOES NOT collect, "
                "verify or automatically score social posts."
            )
            identifiers = list(range(len(research_universe)))
            choice = st.selectbox(
                "Research exact stock / drug program",
                identifiers,
                # All options index the combined universe, not just potential.
                # Source-cleared GEMs can outnumber pending leads (including 0).
                format_func=lambda n: research_program_label(research_universe[n]),
                key=namespace + "_source_research_pick",
            )
            lead = research_universe[choice]
            links = research_search_links(lead)
            if links:
                st.markdown("**COMPANY SOURCES — FIRST**")
                if links["confirmed_issuer_news"]:
                    st.link_button("OPEN OFFICIAL COMPANY IR / NEWS",
                                   links["confirmed_issuer_news"],
                                   key=namespace + "_open_ir")
                else:
                    st.link_button("FIND OFFICIAL COMPANY INVESTOR RELATIONS",
                                   links["find_issuer_news"],
                                   key=namespace + "_find_ir")
                st.markdown(
                    "[Search this drug on issuer's site](" +
                    links["issuer_program_search"] + ") · " +
                    "[Search SEC filings](" + links["sec_program_search"] + ") · " +
                    "[Find funded FINANCING CLOSES](" + links["sec_funding_close_search"] + ") · " +
                    "[Search ClinicalTrials.gov](" + links["clinical_trials"] + ")"
                )
                st.markdown("**SOCIAL DISCUSSION — LEADS ONLY**")
                st.markdown(
                    "[Reddit program discussions](" + links["reddit_program"] +
                    ") · [Stocktwits ticker](" + links["stocktwits_ticker"] +
                    ") · [X discussions](" + links["x_program"] +
                    ") · [Recent news](" + links["news_program"] + ")"
                )
                issues = {key: label for key, label, _ in OPTIONAL_CHECK_TOPICS}
                check = st.selectbox(
                    "Optional check requiring investigation",
                    list(issues),
                    format_func=lambda k: issues[k],
                    key=namespace + "_optional_check_search",
                )
                targeted = optional_check_search_links(lead, check)
                st.markdown(
                    "**SEARCH THIS OPEN CHECK — " + targeted["label"] + "**"
                )
                st.markdown(
                    "[Company Investor Relations](" + targeted["issuer_ir"] +
                    ") · [Primary public records](" + targeted["primary_records"] +
                    ") · [Reddit discussion](" + targeted["reddit"] +
                    ") · [Recent news](" + targeted["news"] + ")"
                )
                st.caption(source_research_policy())
                st.markdown(
                    "**#2 PIPELINE → #1 GEM:** Use these leads to locate an "
                    "issuer Phase 3 readout with verified successful endpoints. "
                    "Two separately funded SEC closings remain optional "
                    "risk evidence, not GEM qualification requirements."
                )

    with st.expander("ALL POTENTIAL GEM EVIDENCE + SOURCE LINKS", expanded=False):
        table = pd.DataFrame(potential + timing_hold).reindex(columns=FULL)
        st.dataframe(
            table, use_container_width=True, hide_index=True, height=360,
            column_config={
                "Clinical source": st.column_config.LinkColumn("Clinical source"),
                "Financing SEC source": st.column_config.LinkColumn("Financing SEC source"),
            },
        )
    st.download_button(
        "EXPORT POTENTIAL GEMs + REASONS",
        pd.DataFrame(potential + timing_hold).reindex(columns=FULL).to_csv(index=False)
        .encode("utf-8"),
        file_name="potential_gems_with_reasons.csv", mime="text/csv",
        key=namespace + "_download",
    )
    if timing_hold:
        with st.expander(f"PAST / EXIT-WINDOW PROGRAMS ({len(timing_hold)}) — NOT NEW ENTRIES",
                         expanded=False):
            for row in timing_hold:
                st.markdown("**" + row["Ticker"] + " · " + row["Drug"] + "**")
                st.caption(row["Why potential"] + " — " + row["Timing / resolution"])
    if show_previous:
        # Previous candidates belong below the entire GEM stage listing.
        departed = departed_stage_rows(membership, "GEM")
        st.markdown("### GEM — PREVIOUS CANDIDATES")
        st.caption(
            "Individual exact-Pipeline-ID history: date GEM first found the trial, "
            "date it left, and recorded departure reason. PDUFA −3 is a trading "
            "warning, not an early removal from this research listing."
        )
        with st.expander(f"OPEN PREVIOUS GEM CANDIDATES ({len(departed)})",
                         expanded=False):
            if departed:
                st.dataframe(pd.DataFrame(departed), use_container_width=True,
                             hide_index=True)
            else:
                st.caption("No GEM departure has been recorded by a complete scan yet.")
    return potential
