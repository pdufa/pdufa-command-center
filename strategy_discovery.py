"""Optional, read-only Strategy research discovery lenses.

All company/trial results are sourced from the already-filtered Pipeline pool.
Questions are research prompts, NOT verified care gaps or efficacy claims.
Biological targets and ingredient drug classes are distinct evidence levels.
"""
import pandas as pd


RESEARCH_LENSES = (
    "Unmet medical need",
    "Disease progression / reversal",
    "Shared biological mechanisms",
    "Treatment resistance",
    "Regenerative / next-generation approaches",
    "Biomarkers / trial endpoints",
)

# Questions only. No disease-treatment assertion, incidence extrapolation,
# investment score, or drug target is invented from disease labels.
DEFAULT_QUESTIONS = {
    "Unmet medical need": (
        "What does current approved standard-of-care treatment fail to achieve for this exact indication?",
        "Which patient subgroups remain inadequately treated, and what clinical evidence documents that gap?",
        "Does the investigational treatment address the identified gap with a meaningful endpoint?",
    ),
    "Disease progression / reversal": (
        "Do existing options slow progression, prevent complications, or restore lost function?",
        "Do registered studies measure clinical disease modification rather than symptom relief alone?",
        "What follow-up duration is needed to demonstrate durable benefit?",
    ),
    "Shared biological mechanisms": (
        "Which molecular targets have source-backed evidence in the selected trials?",
        "Is the same target studied in multiple indications, and is each indication supported independently?",
        "Is a named compound's drug class being mistaken for the program's actual target?",
    ),
    "Treatment resistance": (
        "Which trials explicitly enroll prior-treatment failures, intolerant patients, or refractory disease?",
        "Is benefit shown in the resistant subgroup rather than only the full trial population?",
        "How large is the documented eligible resistant population?",
    ),
    "Regenerative / next-generation approaches": (
        "Is the program gene therapy, RNA therapy, cell therapy, protein replacement, or tissue repair?",
        "Does the human evidence demonstrate restored function, or only an early biomarker change?",
        "What durability, safety, delivery, and manufacturing challenges remain?",
    ),
    "Biomarkers / trial endpoints": (
        "Which primary endpoints are measured, and are they clinically meaningful?",
        "Is any surrogate endpoint accepted for the specific indication and regulatory setting?",
        "Are biomarkers predictive of response, and has the correlation been independently established?",
    ),
}

INDICATION_QUESTIONS = {
    "Type 2 diabetes": (
        "Which trials investigate prevention of kidney, nerve, eye, or cardiovascular complications?",
        "Is benefit independent of glucose lowering, and how was that established?",
    ),
    "Heart failure": (
        "Do studies measure heart-failure hospitalization or mortality, rather than only exercise or biomarker changes?",
        "Which ejection-fraction and clinical subgroups are eligible?",
    ),
    "Chronic kidney disease": (
        "Is reduction in kidney failure or sustained eGFR decline demonstrated?",
        "Does treatment address progression in a specific cause or stage of CKD?",
    ),
    "Obesity": (
        "Which outcomes extend beyond weight loss, such as sleep apnea or cardiovascular events?",
        "Does durability remain after therapy withdrawal?",
    ),
    "Alzheimer's disease": (
        "Do cognitive, functional, and safety outcomes support meaningful clinical benefit?",
        "Is benefit limited to a documented biomarker-defined subgroup?",
    ),
    "MASH / fatty liver disease": (
        "Which studies measure fibrosis improvement, cirrhosis progression, or clinical outcomes?",
        "Are changes in histology supported by durable clinical benefit?",
    ),
    "Osteoarthritis": (
        "Does the intervention improve joint structure or merely reduce pain?",
        "Has slower structural deterioration been linked to better patient outcomes?",
    ),
}


def research_questions(disease, lens):
    """Return question prompts, never automated diagnoses or gap assertions."""
    if lens not in RESEARCH_LENSES:
        raise ValueError("Unknown discovery lens")
    questions = list(DEFAULT_QUESTIONS[lens])
    if lens in {"Unmet medical need", "Disease progression / reversal", "Biomarkers / trial endpoints"}:
        questions.extend(INDICATION_QUESTIONS.get(disease, ()))
    return tuple(questions)


def scoped_records(associations, disease):
    """One row per original source record for a selected disease."""
    if associations is None or associations.empty:
        return pd.DataFrame()
    match = associations.loc[associations["issue"].eq(disease)]
    return match.drop_duplicates(subset=["record_id"]).copy()


def mechanism_evidence(record):
    """Return source evidence category; never infer a biological target from class."""
    def clean(key):
        value = record.get(key, "")
        if pd.isna(value):
            return ""
        value = str(value).strip()
        return "" if value.lower() in {"nan", "none", "<na>"} else value

    target = clean("mechanism_target")
    if target:
        source = clean("classification_source_url")
        return (
            "Annotated biological target / mechanism" if source
            else "Target / mechanism noted — source missing",
            target, source,
        )
    drug_class = clean("drug_class")
    if drug_class:
        source = clean("classification_source_url")
        return (
            "Annotated drug class (target not established)" if source
            else "Drug class noted — source missing",
            drug_class, source,
        )
    named = clean("named_mechanism")
    if named:
        source = clean("named_mechanism_source")
        return (
            "Named ingredient drug class (not necessarily trial lead)" if source
            else "Named ingredient class — source missing",
            named, source,
        )
    return "Unclassified — source research needed", "Not classified", ""


def target_summary(records):
    """Summarize evidence types; identifiers are unique within each group."""
    columns = [
        "Evidence type", "Target / drug class", "Pipeline records",
        "Unique NCT IDs", "Companies", "Drug assets", "Source",
    ]
    if records is None or records.empty:
        return pd.DataFrame(columns=columns)
    data = records.copy().drop_duplicates(subset=["record_id"])
    triples = [mechanism_evidence(record) for record in data.to_dict("records")]
    data["_evidence_type"] = [t[0] for t in triples]
    data["_class"] = [t[1] for t in triples]
    data["_source"] = [t[2] for t in triples]
    for col in ["nct_id", "ticker", "drug"]:
        if col not in data:
            data[col] = ""
        data[col] = data[col].fillna("").astype(str)
    summary = data.groupby(
        ["_evidence_type", "_class", "_source"], dropna=False,
    ).agg(
        count=("record_id", "nunique"),
        nct=("nct_id", lambda x: x.loc[x.ne("")].nunique()),
        companies=("ticker", lambda x: x.loc[x.ne("")].nunique()),
        drugs=("drug", lambda x: x.loc[x.ne("")].nunique()),
    ).reset_index()
    summary = summary.rename(columns={
        "_evidence_type": "Evidence type",
        "_class": "Target / drug class",
        "_source": "Source",
        "count": "Pipeline records",
        "nct": "Unique NCT IDs",
        "companies": "Companies",
        "drugs": "Drug assets",
    })
    return summary[columns].sort_values(
        ["Unique NCT IDs", "Pipeline records"], ascending=False,
        kind="stable",
    ).reset_index(drop=True)


def render_optional_discovery(associations):
    """Off by default; no mutation of existing Streamlit state or Pipeline rows."""
    import streamlit as st

    st.markdown("### OPTIONAL RESEARCH DISCOVERY")
    enabled = st.checkbox(
        "Enable Unmet Medical Needs & Biological Targets explorer",
        value=False,
        key="strategy_enable_discovery",
        help="Optional read-only exploratory screen. Existing Strategy and Pipeline views do not change.",
    )
    if not enabled:
        st.caption("Optional discovery is off. Enable it to investigate medical gaps, targets and treatments.")
        return

    st.caption(
        "Exploratory questions are NOT verified unmet needs, clinical outcomes, "
        "drug approval probabilities or trading recommendations. A large "
        "disease population does not imply a large treatment-eligible population."
    )
    if associations is None or associations.empty:
        st.info("No Pipeline records match the current filters.")
        return

    counts = associations.groupby("issue", dropna=False)["record_id"].nunique()
    choices = sorted(counts.index.tolist(), key=lambda issue: (-counts[issue], issue))
    disease = st.selectbox(
        "Disease / issue to investigate",
        options=choices,
        key="strategy_discovery_disease",
    )
    lens = st.selectbox(
        "Optional research direction",
        options=list(RESEARCH_LENSES),
        key="strategy_discovery_lens",
    )
    selected = scoped_records(associations, disease)
    if selected.empty:
        st.info("No studies for that disease under the selected filters.")
        return

    st.markdown("**Questions requiring evidence review**")
    for question in research_questions(disease, lens):
        st.markdown("- " + question)

    nct = selected["nct_id"].loc[selected["nct_id"].ne("")].nunique()
    companies = selected["ticker"].loc[selected["ticker"].ne("")].nunique()
    a, b, c = st.columns(3)
    a.metric("Pipeline records for this issue", f"{len(selected):,}")
    b.metric("Unique NCT IDs", f"{nct:,}")
    c.metric("Distinct tickers", f"{companies:,}")

    st.markdown("**Recorded targets and intervention classes — check evidence links**")
    st.caption(
        "An annotated molecular target is distinct from an ingredient's "
        "pharmacologic class. Entries without a source link are explicitly marked "
        "as missing evidence; nothing here demonstrates treatment success."
    )
    summary = target_summary(selected)
    st.dataframe(
        summary, use_container_width=True, hide_index=True,
        height=min(385, 40 + 36 * len(summary)),
        column_config={"Source": st.column_config.LinkColumn("Evidence source")},
    )

    st.markdown("**Underlying PIPELINE evidence — companies, drugs and trials**")
    fields = {
        "ticker": "Ticker", "company": "Company",
        "drug": "Drug / intervention", "current_stage": "Stage",
        "status": "Trial status", "nct_id": "NCT ID",
        "indication": "Exact registry indication",
        "source_url": "Original study / regulatory source",
    }
    detail = selected.reindex(columns=list(fields), fill_value="").rename(columns=fields)
    st.dataframe(
        detail, use_container_width=True, hide_index=True, height=420,
        column_config={
            "Original study / regulatory source": st.column_config.LinkColumn("Study source"),
        },
    )
    st.caption(
        "The source records and 14 Pipeline stages are unchanged. "
        "Approved-treatment comparisons, unmet-need severity, endpoints and "
        "commercial opportunity must be verified independently before scoring."
    )
