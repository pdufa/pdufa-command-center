"""Pipeline-first nested disease / therapy / company / trial Strategy view.

All records come from the exact selected Pipeline pool. The small curated issue
catalog only supplies extra disease labels and source notes for exact NCT IDs.
"""
import html
import math
import re

import pandas as pd
from pipeline_universe import STAGES, select_records, stage_counts
from disease_taxonomy import (
    group_indication, burden_for, population_label, RARE_CATEGORIES,
)


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
    # Do not let 9,000+ precise registry phrasings splinter disease counts.
    # Match a conservative disease taxonomy, while preserving the complete
    # indication on every underlying trial for auditing.
    rows["issue"] = [
        group_indication(indication, curated_issue)
        for indication, curated_issue in
        zip(rows["indication"], rows["curated_issue"])
    ]
    rows["approach"] = rows.apply(_approach, axis=1)
    rows["trial_name"] = rows["curated_trial_name"]
    rows["target_population_note"] = rows["curated_population_note"]
    # Never filter on curated membership, and never match by ticker alone.
    assert len(rows) == len(pipeline_pool)
    return rows


# Registry participation states, not evidence of trial success.
ACTIVE_TRIAL_STATES = {
    "RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION",
}


def select_trial_activity(rows, choice):
    """Filter display rows only; PIPELINE and its 14 stage counts stay intact."""
    if rows.empty or choice == "All clinical / regulatory records":
        return rows
    states = rows["status"].fillna("").astype(str).str.upper().str.replace(
        " ", "_", regex=False
    )
    active = states.isin(ACTIVE_TRIAL_STATES)
    if choice == "Active / recruiting trials":
        return rows.loc[active].copy()
    if choice == "Completed trials":
        return rows.loc[states.eq("COMPLETED")].copy()
    if choice == "Stopped / withdrawn studies":
        return rows.loc[states.isin({"TERMINATED", "WITHDRAWN", "SUSPENDED"})].copy()
    if choice == "Regulatory / no registry status":
        return rows.loc[
            rows["record_type"].fillna("").astype(str).str.contains(
                "Regulatory", case=False, regex=False
            ) | states.eq("")
        ].copy()
    return rows


def issue_summary(rows, sort_by="Patient population (global)"):
    """One row per disease; prevalence is context, never addressable market."""
    columns = [
        "Disease / issue", "Worldwide affected", "US affected",
        "Pool records", "Unique NCT IDs", "Companies", "Patient-data year",
        "Population definition", "Rare-disease group", "Burden source", "US data source",
    ]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    grouped = rows.groupby("issue", dropna=False).agg(
        records=("record_id", "size"),
        nct_ids=("nct_id", lambda s: s.loc[s.ne("")].nunique()),
        companies=("ticker", lambda s: s.loc[s.ne("")].nunique()),
    ).reset_index()
    grouped["_world_sort"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("world_people", 0)
    )
    grouped["_us_sort"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("us_people", 0)
    )
    grouped["Worldwide affected"] = grouped["issue"].map(
        lambda issue: population_label(burden_for(issue).get("world_people"))
    )
    grouped["US affected"] = grouped["issue"].map(
        lambda issue: (
            population_label(burden_for(issue).get("us_people"))
            if burden_for(issue).get("us_people")
            else burden_for(issue).get("us_percent", "Not verified")
        )
    )
    grouped["Patient-data year"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("year", "Not verified")
    )
    grouped["Population definition"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("definition", "")
    )
    grouped["Burden source"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("source", "")
    )
    grouped["US data source"] = grouped["issue"].map(
        lambda issue: burden_for(issue).get("us_source", "")
    )
    grouped["Rare-disease group"] = grouped["issue"].map(
        lambda issue: "Potentially rare — verify" if issue in RARE_CATEGORIES else ""
    )
    if sort_by == "Patient population (US)":
        order = ["_us_sort", "records", "issue"]
        descending = [False, False, True]
    elif sort_by == "Most Pipeline trials / programs":
        order = ["records", "_world_sort", "issue"]
        descending = [False, False, True]
    else:
        order = ["_world_sort", "records", "issue"]
        descending = [False, False, True]
    grouped = grouped.sort_values(
        order, ascending=descending, kind="stable"
    )
    return grouped.rename(columns={
        "issue": "Disease / issue", "records": "Pool records",
        "nct_ids": "Unique NCT IDs", "companies": "Companies",
    })[columns].reset_index(drop=True)


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
        "Full PIPELINE pool → grouped disease → drug pathway → company / asset "
        "→ registered trial. Disease groups combine common registry synonyms; "
        "curated annotations match only exact NCT IDs. All source trials remain "
        "in the pool, including records awaiting classification."
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
    all_rows = prepare_strategy_rows(pool, issue_catalog)
    activity_mode = st.selectbox(
        "Trial activity",
        [
            "All clinical / regulatory records",
            "Active / recruiting trials",
            "Completed trials",
            "Stopped / withdrawn studies",
            "Regulatory / no registry status",
        ],
        key="strategy_trial_activity",
        help="Filter STRATEGY results without changing the PIPELINE universe or individual stage counts.",
    )
    rows = select_trial_activity(all_rows, activity_mode)

    total_nct = rows["nct_id"].loc[rows["nct_id"].ne("")].nunique() if not rows.empty else 0
    curated_count = int(rows["curated_issue"].ne("").sum()) if not rows.empty else 0
    unclassified = int(
        rows["issue"].eq("Indication not recorded").sum()
    ) if not rows.empty else 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pipeline records displayed", f"{len(rows):,}")
    m2.metric("Unique registered NCT IDs", f"{total_nct:,}")
    m3.metric("Exact NCT issue matches", f"{curated_count:,}")
    m4.metric("Missing trial indication", f"{unclassified:,}")
    if len(all_rows) != len(rows):
        st.caption(
            f"Showing {len(rows):,} of {len(all_rows):,} records matching "
            "the selected Pipeline stages and activity filter."
        )
    st.caption(
        "Source completeness: classification is available only when "
        "registry / company evidence supports it. Mechanisms not present "
        "in the source are explicitly labeled unclassified."
    )

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
        # Include the precise registry indication in disease search.
        matches = rows["issue"].str.contains(
            issue_search, case=False, regex=False, na=False
        ) | rows["indication"].str.contains(
            issue_search, case=False, regex=False, na=False
        )
        rows = rows.loc[matches].copy()
    st.markdown("### DISEASE BURDEN — LARGEST AFFECTED POPULATIONS")
    sort_by = st.selectbox(
        "Rank conditions by", [
            "Patient population (global)", "Patient population (US)",
            "Most Pipeline trials / programs",
        ], key="strategy_burden_sort"
    )
    verified_only = st.checkbox(
        "Show only diseases with verified population data",
        value=False, key="strategy_verified_burden_only",
    )
    summary = issue_summary(rows, sort_by=sort_by)
    if verified_only:
        summary = summary.loc[
            summary["Burden source"].ne("") | summary["US data source"].ne("")
        ].reset_index(drop=True)
    st.caption(
        f"{len(summary):,} conditions shown · {len(rows):,} Pipeline records "
        "in the selected stages. Population figures are source-dated "
        "disease-wide estimates (often different years and definitions), "
        "NOT trial-eligible patients or commercial forecasts. "
        "Unverified figures remain blank."
    )
    if summary.empty:
        st.info("No diseases match these filters or have verified population data.")
        return
    st.dataframe(
        summary, use_container_width=True, hide_index=True, height=450,
        column_config={
            "Burden source": st.column_config.LinkColumn("Burden source"),
            "US data source": st.column_config.LinkColumn("US data source"),
        },
    )

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
        f"of {len(summary):,}. Open a disease to see its treatment pathways, "
        "companies and clinical trials."
    )

    for item in subset.to_dict("records"):
        issue_name = item["Disease / issue"]
        issue_records = rows.loc[rows["issue"].eq(issue_name)]
        title = (
            f"{issue_name} — {item['Pool records']:,} record(s), "
            f"{item['Unique NCT IDs']:,} NCT ID(s)"
        )
        with st.expander(title, expanded=False):
            context = burden_for(issue_name)
            world = population_label(context.get("world_people"))
            usa = (
                population_label(context.get("us_people"))
                if context.get("us_people")
                else context.get("us_percent", "Not verified")
            )
            st.markdown(
                "**Worldwide affected:** " + world
                + " · **US affected:** " + usa
                + " · **Evidence year:** "
                + context.get("year", "Not verified")
            )
            st.caption(
                context.get("definition", "Patient population not yet verified")
                + ". Clinical eligibility and unmet medical need require "
                "indication-specific research."
            )
            if context.get("source"):
                st.link_button("WORLD / POPULATION SOURCE", context["source"])
            if context.get("us_source"):
                st.link_button("US POPULATION SOURCE", context["us_source"])
            if issue_name in RARE_CATEGORIES:
                st.caption(
                    "Potential rare-disease category — specific FDA orphan "
                    "designation must be verified for each drug and indication."
                )
            # Even a single unclassified disease group may include thousands
            # of records. Page within it rather than freezing the browser.
            if len(issue_records) > 100:
                issue_pages = math.ceil(len(issue_records) / 100)
                issue_key = "strategy_issue_records_" + re.sub(
                    r"[^a-z0-9]+", "_", issue_name.lower()
                )[:70]
                record_page = int(st.number_input(
                    "Record page for " + issue_name,
                    min_value=1, max_value=issue_pages, value=1, step=1,
                    key=issue_key,
                ))
                st.caption(
                    f"Records {(record_page-1)*100+1:,}–"
                    f"{min(record_page*100, len(issue_records)):,} "
                    f"of {len(issue_records):,} for this disease group"
                )
                issue_records = issue_records.sort_values(
                    ["company", "ticker", "drug", "nct_id"], kind="stable"
                ).iloc[(record_page-1)*100:record_page*100]
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
