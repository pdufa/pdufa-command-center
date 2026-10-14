"""Always-visible #1 GEM potential list with specific, source-grounded reasons."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gem_potential_list import build_potential_list

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
