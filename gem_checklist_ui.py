"""Shared, visible Streamlit checkboxes for the GEM research universe.

Controls filter displayed programs. Disabled per-program checks report saved
source observations, with NOT VERIFIED distinct from failed clinical studies.
"""
from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from gem_benchmark_checklist import (
    ADVISORIES, BENCHMARKS, CHECK_LABELS, FILTERABLE, UMBRELLA,
    build_checklist_map, filter_programs,
)


def _columns(compact, n=2):
    return (st,) * n if compact else st.columns(n)


def checklist_filters(master_rows, source_items, *, financing_rechecks=(),
                      clinical_rechecks=(), status=None, namespace="gem",
                      compact=False):
    status = status or {}
    checks = build_checklist_map(
        master_rows, source_items, financing_rechecks, clinical_rechecks,
        sec_current=bool(status.get("sec_financing_source_current")),
        feed_current=bool(status.get("feed_current")),
    )
    st.markdown("**GEM RESEARCH UMBRELLA — TWO ENTRY BENCHMARKS**")
    st.caption(
        "ALL programs stay visible by default. Select checkboxes to FILTER the "
        "research list; these selections NEVER alter actual eligibility, ranking "
        "or trading permission. A registry result or historical financing lead "
        "is not automatically a verified GEM benchmark."
    )
    selected = []
    one, two = _columns(compact)
    for col, (key, label) in zip((one, two), BENCHMARKS):
        if col.checkbox("Only: " + label, value=False,
                        key=namespace + "_filter_" + key):
            selected.append(key)
    with st.expander("MORE CHECKBOX FILTERS — RESEARCH LEADS & OPTIONAL CHECKS",
                     expanded=False):
        st.caption(
            "The first two lead filters include UNVERIFIED source observations. "
            "The other filters require an affirmative, source-grounded check. "
            "None is a new entry benchmark."
        )
        for idx, (key, label) in enumerate(UMBRELLA + ADVISORIES):
            if st.checkbox("Show only: " + label, value=False,
                           key=namespace + "_filter_" + key):
                selected.append(key)
    visible = filter_programs(master_rows, checks, selected)
    st.caption(
        f"Showing {len(visible):,} / {len(master_rows):,} programs after "
        f"{len(selected)} user-selected checkbox filter(s). "
        "Unchecked = no filter, not a negative finding."
    )
    return visible, checks


def stock_checkboxes(row, states, *, namespace="gem"):
    """Read-only visible statuses; checkmarks mean PASS, or observed lead only."""
    event = str(row.get("Exact Program / Event") or "")
    uid = hashlib.sha256(event.encode("utf-8")).hexdigest()[:16]
    st.markdown("**CHECKLIST · EXACT PROGRAM / SOURCE EVIDENCE**")
    st.caption(
        "Checks below are read-only evidence statuses, not manual overrides. "
        "The first TWO are the only GEM eligibility benchmarks. "
        "A blank box can mean missing/blocked data, not trial failure."
    )
    for key, label in BENCHMARKS:
        x = states.get(key, {})
        st.checkbox(label + " — " + x.get("status", "NOT VERIFIED"),
                    value=x.get("checked") is True, disabled=True,
                    key=f"{namespace}_stock_{uid}_{key}_{int(x.get('checked') is True)}")
        st.caption(x.get("detail", "Evidence not linked"))
    with st.expander("SOURCE-OBSERVED UMBRELLA + ALL OPTIONAL RESEARCH CHECKS",
                     expanded=False):
        st.caption(
            "Lead checkmarks show data observed, not proof that the GEM "
            "entry benchmark passed. Advisory checks are NOT eligibility gates."
        )
        for key, label in UMBRELLA + ADVISORIES:
            x = states.get(key, {})
            checked = x.get("checked") is True or (
                key in dict(UMBRELLA) and x.get("observed") is True
            )
            st.checkbox(label + " — " + x.get("status", "NOT VERIFIED"),
                        value=checked, disabled=True,
                        key=f"{namespace}_stock_{uid}_{key}_{int(checked)}")
            st.caption(x.get("detail", "Source not verified"))


def checkbox_table(rows, checklists):
    """Boolean checkbox columns plus per-program review count, no risk gating."""
    columns = [(key, label) for key, label in BENCHMARKS + UMBRELLA + ADVISORIES]
    out = []
    for r in rows:
        event = str(r.get("Exact Program / Event") or "")
        checks = checklists.get(event, {})
        entry = {
            "Ticker": r.get("Ticker"), "Drug": r.get("Drug"),
            "Stage": r.get("GEM Stage"), "GEM Status": r.get("GEM Status"),
            "GEM Score /100": r.get("GEM Score /100"),
            "Exact Program / Event": event,
        }
        for key, label in columns:
            state = checks.get(key, {})
            entry[label] = bool(
                state.get("checked") is True or (
                    key in dict(UMBRELLA) and state.get("observed") is True
                )
            )
        out.append(entry)
    return pd.DataFrame(out)


def render_checkbox_table(rows, checklists, *, height=360):
    table = checkbox_table(rows, checklists)
    st.caption(
        "Checked = verified source condition, except the two RESEARCH UMBRELLA "
        "lead columns, where checked means an observation exists and still "
        "requires adjudication. Blank may mean unavailable or unverified."
    )
    st.dataframe(
        table, use_container_width=True, hide_index=True, height=height,
        column_config={
            label: st.column_config.CheckboxColumn(label, disabled=True)
            for _, label in BENCHMARKS + UMBRELLA + ADVISORIES
        },
    )
    return table
