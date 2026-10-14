"""Always-visible #1 GEM potential list with specific, source-grounded reasons."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gem_potential_list import build_potential_list
from gem_secondary_research import (
    OPTIONAL_CHECK_TOPICS, optional_check_search_links,
    research_search_links, source_research_policy,
)

VISIBLE = ("Ticker", "Drug", "Why potential", "Still needed", "Timing / resolution")
FULL = (
    "Ticker", "Drug", "Indication", "Why potential", "Still needed",
    "Evidence type", "GEM status", "SEC documents rechecked", "NCT ID",
    "PDUFA date (saved)", "Timing / resolution", "Exact program",
    "Clinical source", "Financing SEC source", "Source review date",
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


def render_gem_potential(root="data", *, compact=False, namespace="gem_potential"):
    """Keep pending research stocks separate from proven GEM eligibility.

    This view updates from saved review files, never launches a scan or
    reinterprets a historical funding claim as an entry authorization.
    """
    potential, timing_hold = build_potential_list(root)
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
    if potential:
        with st.expander("INVESTOR RELATIONS + SOCIAL RESEARCH — SELECT POTENTIAL GEM",
                         expanded=False):
            st.caption(
                "Investigate non-benchmark checks here: cash/runway, insider "
                "activity, dilution, trading attention, discussion and catalysts. "
                "Source links open a search or the company's known official "
                "Investor Relations/news page; this panel DOES NOT collect, "
                "verify or automatically score social posts."
            )
            identifiers = list(range(len(potential)))
            choice = st.selectbox(
                "Research exact stock / drug program",
                identifiers,
                format_func=lambda n: (
                    str(potential[n].get("Ticker") or "?") + " · " +
                    str(potential[n].get("Drug") or "?") + " · " +
                    str(potential[n].get("NCT ID") or potential[n].get("Exact program") or "")
                ),
                key=namespace + "_source_research_pick",
            )
            lead = potential[choice]
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
                    "issuer readout and two source-verifiable post-readout "
                    "financing closings. Only those independently checked "
                    "events can clear the first two GEM benchmarks."
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
    return potential
