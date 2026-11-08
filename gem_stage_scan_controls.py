"""Retired GEM JR and GEM scan controls. Historical ledgers are preserved."""
import streamlit as st


def render_stage_scan(stage):
    """Never dispatch retired GEM JR/GEM scans."""
    if stage not in ("GEM JR", "GEM"):
        raise ValueError("Unknown historical GEM stage")
    st.info(stage + " scans were retired. Use POOL, FOCUS and independent Deep Medical Intelligence. Historical scans remain retired.")
