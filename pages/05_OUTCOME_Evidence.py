"""Read-only OUTCOME evidence page; no prediction execution or training."""
import streamlit as st
from outcome_fda_readiness_streamlit import render_outcome_readiness

st.set_page_config(page_title="OUTCOME · FDA Evidence", page_icon="📊", layout="wide")
render_outcome_readiness(st)
st.info(
    "Research-only status. The 20 selected FDA actions are not a verified "
    "unbiased application cohort. No prediction accuracy or approval "
    "probability is certified."
)
