"""Research-only Streamlit PREDICTIONS page.

Run as: streamlit run research/predictions_page.py
Requires PREDICTIONS_TRIAL_SNAPSHOT pointing to a real JSON trial snapshot.
Requires PREDICTIONS_JOB_DIRECTORY for persistent job records.
"""
from __future__ import annotations

import os
from pathlib import Path

from research.predictions_source_loader import load_trial_snapshot
from research.predictions_tab import render_predictions_tab


def page_configuration() -> tuple[str | None, str | None]:
    return os.getenv("PREDICTIONS_TRIAL_SNAPSHOT"), os.getenv("PREDICTIONS_JOB_DIRECTORY")


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="PREDICTIONS", layout="wide")
    snapshot, directory = page_configuration()
    if not snapshot:
        st.title("PREDICTIONS")
        st.warning("Trial source snapshot not configured. No live trial data available.")
        return
    try:
        trials = load_trial_snapshot(Path(snapshot))
    except (OSError, ValueError) as exc:
        st.title("PREDICTIONS")
        st.error(f"Trial source unavailable: {type(exc).__name__}")
        return
    render_predictions_tab(trials, job_directory=directory)


if __name__ == "__main__":
    main()
