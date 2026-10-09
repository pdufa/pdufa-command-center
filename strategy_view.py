"""Pipeline-first nested disease / therapy / company / trial Strategy view.

All records come from the exact selected Pipeline pool. The small curated issue
catalog only supplies extra disease labels and source notes for exact NCT IDs.
"""
import html
import math
import re

import pandas as pd
from pipeline_universe import STAGES, select_records, stage_counts


NCT_PATTERN = re.compile(r"^NCT\d{8}$")
STRATEGY_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1lBfjuXloQnoUTOJZYnu6v6PAHrZSqJoWn_-6L6wt-fY/edit#gid=202610019"
)


def _text(value, fallback=""):
    """Return safe, visible scalar text without turning missing values into 'nan'."""
    if value is None:
        return fallback
    value = str(value).strip()
    if not value or value.lower() in {"nan", "nat", "<na>", "none"}:
        return fallback
    return value


def _nct(value):
    value = _text(value).upper()
    return value if NCT_PATTERN.fullmatch(value) else ""


def _approach(row):
    # Prefer the source-classified target or pharmacologic class; never guess.
    for key in ("drug_class", "mechanism_target"):
        value = _text(row.get(key))
        if value:
            return value
    modality = _text(row.get("drug_modality"))
    if modality and not modality.startswith("Drug (registry;"):
        return modality + " — mechanism not classified"
    return "Mechanism / drug approach not yet classified"


def prepare_strategy_rows(pipeline_pool, catalog=None):
    """Preserve every selected Pipeline record; enrich ONLY via exact NCT match."""
    if pipeline_pool is None or pipeline_pool.empty:
        return pd.DataFrame(columns=[
            "record_id", "issue", "approach", "nct_id", "company", "ticker",
            "drug", "curated_issue", "trial_name", "target_population_note",
        ])

    rows = pipeline_pool.copy().reset_index(drop=True)
    required = (
        "record_id", "record_type", "ticker", "company", "drug", "indication",
        "nct_id", "drug_class", "mechanism_target", "drug_modality",
        "registered_phase", "current_stage", "status", "results_posted",
        "source_updated", "checked_at", "source_url", "evidence_status",
        "evidence_note", "classification_status", "classification_source_url",
        "nda_submission_date", "fda_acceptance_date", "pdufa_date",
        "decision_date",
    )
    for name in required:
        if name not in rows:
            rows[name] = ""
    for name in required:
        rows[name] = rows[name].map(_text)
    rows["nct_id"] = rows["nct_id"].map(_nct)

    catalog_columns = ("nct_id", "issue", "trial_name",
                       "target_population_note", "evidence_url")
    if catalog is None or catalog.empty or "nct_id" not in catalog:
        lookup = pd.DataFrame(columns=catalog_columns)
    else:
        lookup = catalog.copy()
        for name in catalog_columns:
            if name not in lookup:
                lookup[name] = ""
        lookup = lookup[list(catalog_columns)].fillna("")
        lookup["nct_id"] = lookup["nct_id"].map(_nct)
        lookup = lookup[lookup["nct_id"].ne("")].drop_duplicates(
            "nct_id", keep="first"
        )
    lookup = lookup.rename(columns={
        "issue": "curated_issue",
        "trial_name": "curated_trial_name",
        "target_population_note": "curated_population_note",
        "evidence_url": "curated_evidence_url",
    })
    rows = rows.merge(lookup, on="nct_id", how="left", validate="many_to_one")
    for name in ("curated_issue", "curated_trial_name",
                 "curated_population_note", "curated_evidence_url"):
        rows[name] = rows[name].fillna("").map(_text)
    rows["issue"] = rows.apply(
        lambda r: _text(r["curated_issue"]) or
                  _text(r["indication"]) or
                  "Indication / disease not yet classified",
        axis=1,
    )
    rows["approach"] = rows.apply(_approach, axis=1)
    rows["trial_name"] = rows["curated_trial_name"]
    rows["target_population_note"] = rows["curated_population_note"]
    # Never filter on curated membership, and never match by ticker alone.
    assert len(rows) == len(pipeline_pool)
    return rows


def issue_summary(rows):
    if rows.empty:
        return pd.DataFrame(columns=["Disease / issue", "Pool records",
                                     "Unique NCT IDs", "Companies"])
    grouped = rows.groupby("issue", dropna=False).agg(
        records=("record_id", "size"),
        nct_ids=("nct_id", lambda s: s.loc[s.ne("")].nunique()),
        companies=("ticker", lambda s: s.loc[s.ne("")].nunique()),
    ).reset_index()
    grouped = grouped.sort_values(
        ["records", "issue"], ascending=[False, True], kind="stable"
    )
    return grouped.rename(columns={
        "issue": "Disease / issue", "records": "Pool records",
        "nct_ids": "Unique NCT IDs", "companies": "Companies",
    }).reset_index(drop=True)


def _escape(value, fallback="Not recorded"):
    return html.escape(_text(value, fallback), quote=True)


def _link(label, value):
    url = _text(value)
    if not url.startswith(("https://", "http://")):
        return ""
    return (
        '<a style="color:#0b57d0 !important;text-decoration:underline !important" '
        'target="_blank" rel="noopener noreferrer" href="'
        + html.escape(url, quote=True) + '">'
        + html.escape(label) + "</a>"
    )


def _trial_html(record):
    nct = _nct(record.get("nct_id"))
    title = _text(record.get("trial_name")) or (
        "Registered clinical trial" if nct else
        "Pipeline program / regulatory event (trial ID not recorded)"
    )
    links = [
        _link("ClinicalTrials.gov", "https://clinicaltrials.gov/study/" + nct) if nct else "",
        _link("Registry / regulatory source", record.get("source_url")),
        _link("Curated clinical evidence", record.get("curated_evidence_url")),
        _link("Mechanism evidence", record.get("classification_source_url")),
    ]
    links = [link for link in links if link]
    details = [
        "Stage: " + _escape(record.get("current_stage")),
        "Registered phase: " + _escape(record.get("registered_phase"))
        + " · Trial status: " + _escape(record.get("status")),
        "Registry/source updated: " + _escape(record.get("source_updated"))
        + " · Last checked: " + _escape(record.get("checked_at")),
        "Evidence: " + _escape(record.get("evidence_status"))
        + " · Classification: " + _escape(record.get("classification_status")),
    ]
    for key, label in (
        ("results_posted", "Results posted"),
        ("nda_submission_date", "NDA/BLA submitted"),
        ("fda_acceptance_date", "FDA accepted"),
        ("pdufa_date", "PDUFA target"),
        ("decision_date", "Decision date"),
    ):
        if _text(record.get(key)):
            details.append(label + ": " + _escape(record.get(key)))
    if _text(record.get("target_population_note")):
        details.append("Target population: " + _escape(
            record.get("target_population_note")
        ))
    if _text(record.get("indication")):
        details.append("Specific indication: " + _escape(record.get("indication")))
    if links:
        details.append(" · ".join(links))
    return (
        "<li><strong>" + _escape(title) + "</strong> "
        + ("<code>" + _escape(nct) + "</code>" if nct
           else "<em>No NCT ID</em>")
        + "<ul>" + "".join("<li>" + entry + "</li>" for entry in details)
        + "</ul></li>"
    )


def render_strategy_page(universe, issue_catalog):
    """Render the live full-Pipeline Strategy page in the existing Streamlit app."""
    import streamlit as st

    st.markdown("## STRATEGY — NESTED DISEASE / DRUG / TRIAL MAP")
    st.caption(
        "Source: the same complete Pipeline universe and 14 stages as PIPELINE. "
        "Disease → drug approach / mechanism → company and asset → clinical "
        "trial or program. Curated issue labels enrich only exact NCT matches; "
        "unmapped Pipeline records are always retained."
    )
    st.link_button("OPEN STRATEGY RESEARCH SHEET", STRATEGY_SHEET_URL)

    st.markdown("### PIPELINE STAGES AND COUNTS")
    stages = st.multiselect(
        "Pipeline stages feeding STRATEGY",
        options=list(STAGES),
        default=list(STAGES),
        key="pipeline_universe_stages",
        placeholder="Choose one or more stages",
    )
    # Counts shown for each of the 14 stages before the populated list.
    st.dataframe(stage_counts(universe), use_container_width=True,
                 hide_index=True, height=530)
    st.caption(
        "Each stage count covers the whole saved Pipeline universe. A record "
        "can carry multiple stage tags; totals across stages must not be added."
    )

    search = st.text_input(
        "Find ticker, drug, indication, or NCT ID",
        key="pipeline_universe_search",
    ).strip()
    pool = select_records(universe, stages, search)
    rows = prepare_strategy_rows(pool, issue_catalog)

    total_nct = rows["nct_id"].loc[rows["nct_id"].ne("")].nunique() if not rows.empty else 0
    curated_count = int(rows["curated_issue"].ne("").sum()) if not rows.empty else 0
    unclassified = int(
        rows["issue"].eq("Indication / disease not yet classified").sum()
    ) if not rows.empty else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pipeline records displayed", f"{len(rows):,}")
    m2.metric("Unique registered NCT IDs", f"{total_nct:,}")
    m3.metric("Exact NCT issue matches", f"{curated_count:,}")
    m4.metric("Issue not classified", f"{unclassified:,}")

    if not stages:
        st.info("Select at least one stage to populate STRATEGY.")
        return
    if rows.empty:
        st.info("No Pipeline records match the selected stages or search.")
        return

    issue_search = st.text_input(
        "Search disease / issue names", key="strategy_disease_search"
    ).strip()
    if issue_search:
        rows = rows[rows["issue"].str.contains(
            issue_search, case=False, regex=False, na=False
        )].copy()
    summary = issue_summary(rows)
    st.markdown("### DISEASE / MEDICAL ISSUE LIST")
    st.caption(
        f"{len(summary):,} matching conditions · {len(rows):,} unique Pipeline records. "
        "U.S. and worldwide patient populations and unmet need stay "
        "UNVERIFIED until evidence and as-of dates are collected."
    )
    if summary.empty:
        st.info("No disease / issue names match this search.")
        return
    st.dataframe(summary, use_container_width=True,
                 hide_index=True, height=280)

    page_size = st.selectbox(
        "Disease groups per page", [10, 25, 50, 100],
        index=1, key="strategy_page_size"
    )
    pages = max(1, math.ceil(len(summary) / page_size))
    current_page = int(st.number_input(
        "Issue page", min_value=1, max_value=pages, value=1, step=1
    ))
    start = (current_page - 1) * page_size
    subset = summary.iloc[start:start + page_size]
    st.caption(
        f"Displaying disease groups {start+1:,}–{start+len(subset):,} "
        f"of {len(summary):,}; use the page control to reach all groups."
    )

    for item in subset.to_dict("records"):
        issue_name = item["Disease / issue"]
        issue_records = rows.loc[rows["issue"].eq(issue_name)]
        title = (
            f"{issue_name} — {item['Pool records']:,} record(s), "
            f"{item['Unique NCT IDs']:,} NCT ID(s)"
        )
        with st.expander(title, expanded=False):
            st.caption(
                "Patient population (U.S./worldwide): not verified · "
                "Unmet medical need: pending evidence review"
            )
            for approach, approach_rows in issue_records.groupby(
                "approach", sort=True, dropna=False
            ):
                st.markdown("#### " + _escape(approach))
                groups = approach_rows.sort_values(
                    ["company", "ticker", "drug", "nct_id"],
                    kind="stable",
                ).groupby(["company", "ticker", "drug"],
                          sort=True, dropna=False)
                for (company, ticker, drug), company_rows in groups:
                    st.markdown(
                        '<div class="card"><strong>'
                        + _escape(company, "Company not recorded")
                        + " (" + _escape(ticker, "No ticker") + ")"
                        + " — " + _escape(drug, "Asset not recorded")
                        + "</strong><ul>"
                        + "".join(
                            _trial_html(row) for row in company_rows.to_dict("records")
                        )
                        + "</ul></div>",
                        unsafe_allow_html=True,
                    )
    if st.button("REFRESH STRATEGY FROM PIPELINE", key="strategy_refresh"):
        st.cache_data.clear()
        st.rerun()
