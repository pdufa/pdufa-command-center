"""Optional Streamlit display for the read-only OUTCOME readiness grades.

Call render_outcome_readiness() from an existing Streamlit page. Importing
this module does not run Streamlit, write to storage, or activate a model.
"""
from __future__ import annotations
from outcome_fda_readiness_panel import build_outcome_readiness_panel

def render_outcome_readiness(st=None) -> dict:
    if st is None:
        import streamlit as st
    payload = build_outcome_readiness_panel()
    primary = payload["primary"]
    secondary = payload["secondary"]
    st.subheader("OUTCOME · Historical evidence readiness")
    a, b, c = st.columns(3)
    a.metric("Evidence documented", f'{primary["documented_timeline_coverage_percent"]:.1f}%')
    b.metric("FDA timelines", f'{primary["documented_timeline_numerator"]}/{primary["selected_action_denominator"]}')
    c.metric("Prediction", primary["prediction_grade"])
    st.caption(payload["disclaimer"])
    with st.expander(f'{secondary["title"]} ({secondary["blocking_condition_count"]})',
                     expanded=False):
        for item in secondary["blocking_conditions"]:
            if item["blocking"]:
                suffix = (f' — {item["affected_count"]} records'
                          if item["affected_count"] is not None else "")
                st.write(f'• {item["label"]}{suffix}')
        st.warning("Prediction probability and measured accuracy are unavailable. "
                   "Research-only evidence does not authorize model training.")
    return payload
