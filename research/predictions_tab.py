"""Research-only PREDICTIONS Streamlit component.

Mount via render_predictions_tab(trial_rows, assessment_rows, job_directory=...).
Jobs are QUEUED until a real external scientific worker runs them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

ELIGIBLE_GROUPS = ("PHASE3_DATA_RELEASED", "GEM_JR", "GEM", "WT")
VALID_STATUSES = {"NOT_STARTED", "RUNNING", "COMPLETED", "BLOCKED", "FAILED", "MISSING_EVIDENCE"}


def eligible_trials(rows: Iterable[Mapping]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        trial_id = str(row.get("trial_id") or "").strip()
        groups = set(row.get("groups") or ())
        if row.get("phase3_data_released") is True:
            groups.add("PHASE3_DATA_RELEASED")
        groups &= set(ELIGIBLE_GROUPS)
        if not trial_id or not groups:
            continue
        if trial_id not in grouped:
            grouped[trial_id] = {"trial_id": trial_id, "label": str(row.get("label") or trial_id), "groups": set()}
        grouped[trial_id]["groups"].update(groups)
    return [
        {**entry, "groups": sorted(entry["groups"])}
        for entry in sorted(grouped.values(), key=lambda item: item["label"].casefold())
    ]


def assessment_progress(rows: Iterable[Mapping]) -> tuple[int, int]:
    checks = list(rows)
    return sum(row.get("status") == "COMPLETED" for row in checks), len(checks)


def render_predictions_tab(
    trial_rows: Iterable[Mapping],
    assessment_rows: Iterable[Mapping] = (),
    *,
    on_start=None,
    job_directory: str | Path | None = None,
) -> None:
    """Render persisted checklist. Explicit on_start overrides local queue."""
    import streamlit as st

    from research.predictions_job_adapter import (
        checklist_for_trial, latest_trial_job, start_prediction_job,
    )

    st.title("PREDICTIONS")
    st.caption("Research-only predictions. Not a validated trading signal.")
    trials = eligible_trials(trial_rows)
    if not trials:
        st.info("No verified eligible trials available. Connect Phase 3/GEM JR/GEM/WT data.")
        return
    selected = st.selectbox(
        "Select a trial", trials,
        format_func=lambda item: f"{item['label']} — {', '.join(item['groups'])}",
        key="predictions_trial_selection",
    )
    if st.button("START PREDICTION", type="primary", disabled=on_start is None and job_directory is None):
        if on_start is not None:
            on_start(selected["trial_id"])
        elif job_directory is not None:
            start_prediction_job(job_directory, selected["trial_id"])
        st.success("Prediction job queued. Scientific analysis requires a connected worker.")
    if on_start is None and job_directory is None:
        st.warning("Prediction runner and job store not connected. START PREDICTION is disabled.")
    st.subheader("Assessment checklist")
    if job_directory is not None:
        job = latest_trial_job(job_directory, selected["trial_id"])
        if job:
            st.write(f"Job: {job['job_id']} · State: {job['status']}")
        checks = checklist_for_trial(job_directory, selected["trial_id"])
    else:
        checks = [row for row in assessment_rows if row.get("trial_id") == selected["trial_id"]]
    done, total = assessment_progress(checks)
    st.progress(done / total if total else 0)
    st.write(f"{done} of {total} assessments completed")
    if not checks:
        st.info("No assessment job results available for this trial.")
    for idx, row in enumerate(checks):
        title = str(row.get("title") or f"Assessment {idx + 1}")
        status = str(row.get("status") or "NOT_STARTED")
        if status not in VALID_STATUSES:
            status = "BLOCKED"
        with st.expander(f"{title} — {status}"):
            st.write(str(row.get("details") or "No assessment details recorded."))
            st.write("Evidence:", row.get("evidence") or "Not available")
            st.write("Uncertainty:", row.get("uncertainty") or "Not assessed")
    st.subheader("Decision")
    st.info("PASS / CRL / EXTENSION / ABSTAIN — not calculated until a validated analysis runner returns a result.")
