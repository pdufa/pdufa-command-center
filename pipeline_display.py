"""Pure, testable filters for the Streamlit Pipeline page.

Only a CURRENT stage plus a selected date band can produce trial rows.
The page decides whether the user has pressed the explicit Show button.
"""
import pandas as pd

DATE_BANDS = (
    "0–30 DAYS",
    "31–60 DAYS",
    "61–90 DAYS",
    "+90 DAYS",
    "NO PDUFA YET",
    "PAST / RECHECK",
)

DISPLAY_FIELDS = {
    "DATES": "DATES",
    "Days to PDUFA": "Days to PDUFA",
    "ticker": "Ticker",
    "company": "Company",
    "current_stage": "Current Stage",
    "record_type": "Record Type",
    "drug": "Drug",
    "indication": "Indication",
    "nct_id": "NCT ID",
    "registered_phase": "Registered Phase",
    "status": "Trial Status",
    "results_posted": "Results Posted",
    "nda_submission_date": "NDA/BLA Submission Date",
    "fda_acceptance_date": "FDA Acceptance Date",
    "pdufa_date": "PDUFA Target",
    "decision_date": "FDA Decision Date",
    "outcome": "Recorded Outcome",
    "evidence_status": "Evidence Status",
    "checked_at": "Last Checked",
    "source_url": "Source",
    "evidence_note": "Evidence Note",
}


def prepare_pipeline(frame, as_of):
    """Assign exactly one countdown band to every source record."""
    result = frame.copy()
    if "pdufa_date" not in result.columns:
        result["pdufa_date"] = ""
    target = pd.to_datetime(
        result["pdufa_date"].fillna("").astype(str).str[:10],
        format="%Y-%m-%d", errors="coerce",
    )
    days = (target - pd.Timestamp(as_of)).dt.days
    result["Days to PDUFA"] = days

    def band(value):
        if pd.isna(value):
            return "NO PDUFA YET"
        if value < 0:
            return "PAST / RECHECK"
        if value <= 30:
            return "0–30 DAYS"
        if value <= 60:
            return "31–60 DAYS"
        if value <= 90:
            return "61–90 DAYS"
        return "+90 DAYS"

    result["DATES"] = days.map(band)
    return result


def filter_pipeline(frame, stages, date_bands, query=""):
    """Filter both dimensions; never interpret no selection as all."""
    if frame.empty or not stages or not date_bands:
        return frame.iloc[:0].copy()
    if "current_stage" not in frame or "DATES" not in frame:
        return frame.iloc[:0].copy()
    selected = frame.loc[
        frame["current_stage"].fillna("").isin(list(stages))
        & frame["DATES"].isin(list(date_bands))
    ].copy()
    if "record_id" in selected:
        selected = selected.drop_duplicates(subset=["record_id"])
    query = str(query or "").strip()
    if query and not selected.empty:
        cols = [c for c in ("ticker", "company", "drug", "indication", "nct_id")
                if c in selected]
        if not cols:
            return selected.iloc[:0].copy()
        text = selected[cols].fillna("").astype(str).agg(" ".join, axis=1)
        selected = selected.loc[text.str.contains(query, case=False, regex=False)]
    return selected


def chart_rows(frame, sort_mode="Closest PDUFA first"):
    """The count must be len(this very same dataframe)."""
    if frame.empty:
        return pd.DataFrame(columns=list(DISPLAY_FIELDS.values()))
    selected = frame.copy()
    if sort_mode == "Ticker A–Z":
        selected = selected.sort_values(
            ["ticker", "Days to PDUFA"], na_position="last",
            kind="stable",
        )
    else:
        selected["_date_rank"] = pd.Categorical(
            selected["DATES"], categories=DATE_BANDS, ordered=True
        )
        selected = selected.sort_values(
            ["_date_rank", "Days to PDUFA", "ticker"],
            na_position="last", kind="stable",
        ).drop(columns=["_date_rank"])
    for col in DISPLAY_FIELDS:
        if col not in selected:
            selected[col] = ""
    return selected[list(DISPLAY_FIELDS)].rename(columns=DISPLAY_FIELDS)
