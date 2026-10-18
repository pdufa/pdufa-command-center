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
    build_checklist_map, filter_programs, program_key, research_candidate_rows,
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
        checks = checklists.get(program_key(r), {})
        entry = {
            "Ticker": r.get("Ticker"), "Drug": r.get("Drug"),
            "Stage": r.get("GEM Stage"), "GEM Status": r.get("GEM Status"),
            "GEM Score /100": r.get("GEM Score /100"),
            "Exact Program / Event": event,
            "NCT ID": r.get("NCT ID"),
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


def render_research_candidates(master_rows, checklists, *,
                               clinical_rechecks=(), financing_rechecks=(),
                               namespace="gem_research", compact=False):
    """Always-visible exact-program leads, irrespective of eligible-only filters."""
    leads = research_candidate_rows(
        master_rows, checklists, clinical_rechecks=clinical_rechecks,
        financing_rechecks=financing_rechecks,
    )
    st.markdown("### GEM RESEARCH CANDIDATES — SOURCE LEADS")
    st.caption(
        "Includes Phase 3 data observations OR a historically attested "
        "financing lead. The TWO verified benchmarks still control eligibility. "
        "A lead is NOT a qualified GEM or a buy recommendation."
    )
    verified = sum(r.get("Status") == "PHASE 3 VERIFIED — FINANCING OPTIONAL" for r in leads)
    if compact:
        st.caption(f"{len(leads)} research leads · {verified} fully verified GEM candidates")
    else:
        p, q = st.columns(2)
        p.metric("Research candidates (unverified leads included)", len(leads))
        q.metric("Both GEM benchmarks verified", verified)
    if not leads:
        st.info(
            "No source-observed GEM research leads in the current saved dataset. "
            "This is a source coverage result, not proof that no biotech opportunities exist."
        )
        return []
    for name, group in (
        ("Both data leads", "Both research leads"),
        ("Financing lead", "Financing lead — Phase 3 review"),
        ("Phase 3 lead", "Phase 3 lead — financing review"),
    ):
        tickers = list(dict.fromkeys(
            str(v.get("Ticker") or "") for v in leads
            if v.get("GEM research group") == group and v.get("Ticker")
        ))
        if tickers:
            st.caption(name + ": " + ", ".join(tickers))
    fields = (
        "Ticker", "Drug", "GEM research group", "Status",
        "Phase 3 data observed", "Financing lead observed",
        "Phase 3 benchmark verified", "Second financing benchmark verified",
        "Fresh SEC transactions verified", "Latest clinical review",
        "Latest SEC review", "NCT ID", "PDUFA Date",
        "Phase 3 Source", "Financing Source", "Exact Program / Event",
    )
    table = pd.DataFrame(leads).reindex(columns=fields)
    st.dataframe(
        table, use_container_width=True, hide_index=True,
        height=255 if compact else 420,
        column_config={
            "Phase 3 data observed": st.column_config.CheckboxColumn(
                "Phase 3 data observed", disabled=True),
            "Financing lead observed": st.column_config.CheckboxColumn(
                "Financing lead observed", disabled=True),
            "Phase 3 benchmark verified": st.column_config.CheckboxColumn(
                "Phase 3 benchmark verified", disabled=True),
            "Second financing benchmark verified": st.column_config.CheckboxColumn(
                "Second financing benchmark verified", disabled=True),
            "Phase 3 Source": st.column_config.LinkColumn("Phase 3 Source"),
            "Financing Source": st.column_config.LinkColumn("Financing Source"),
        },
    )
    st.download_button(
        "EXPORT GEM RESEARCH CANDIDATES",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="gem_research_candidates.csv",
        mime="text/csv", key=namespace + "_export",
    )
    return leads
