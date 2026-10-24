"""Read-only lineage, overlap and input-coverage audit for PDUFA score models.

This is an INPUT audit, not investment performance validation or a substitute
for independent source verification. Missing values never become zeros.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

SOURCES = {
    "PDUFA candidates": "data/pdufa_candidates.csv",
    "FDA V3 review": "data/fda_review_engine.csv",
    "Pre-readout evidence": "data/phase3_pre_readout_evidence.csv",
    "Post financing gates": "data/step7_financing_review.csv",
    "Post market status": "data/step7_market_status.csv",
}
PILOTS = "data/pre_phase3_pilot_clinical_reviews.json"
CLINICAL = (
    ("Phase 2 efficacy", "phase2_efficacy", 25),
    ("Phase 3 design", "phase3_design", 30),
    ("Safety", "safety", 15),
    ("Regulatory alignment", "regulatory_alignment", 15),
    ("Execution", "execution", 10),
    ("Evidence quality", "evidence_quality", 5),
)
MODELS = (
    ("PRE Clinical (pilot)", "Clinical evidence", "Phase 2 efficacy, Phase 3 design, safety, regulatory alignment, execution, evidence quality", PILOTS, "100", "Source-cited analyst review"),
    ("PRE Clinical (reviewed)", "Clinical evidence", "six *_points plus *_source and *_source_date", SOURCES["Pre-readout evidence"], "100", "Requires source/assessment date gates"),
    ("PRE Research Priority", "Clinical / registry", "Trial phase, Company/program identity, Registry check, Protocol check, Design inputs present /6, Phase 2 PRIMARY evidence count, Registry primary completion, Market cap USD", "data/step7_pre_phase3_feed.csv", "100", "Research-order only"),
    ("POST Evidence", "Clinical / financing / PDUFA / market", "phase3_status, phase3_date, trial_evidence_url, Audited gate details, Historical second closing, Second source, pdufa_date, pdufa_confirmation, trailing_momentum_pct, relative_volume", "PDUFA + post financing + market snapshots", "100", "Source-gated evidence, not entry authorization"),
    ("POST Research Priority", "Clinical / financing / PDUFA / market", "Days to PDUFA, Phase 3 evidence, Phase 3 source, financing record freshness, PDUFA verification, trailing_momentum_pct, relative_volume, NCT ID, Exact event", "Post Stage 7 combined records", "100", "Research-triage only"),
    ("Trading Score", "Clinical / regulatory (saved fallback)", "trade_score; fallback only if column ABSENT: mean(science_score, regulatory_score, safety_score, cmc_score)", SOURCES["PDUFA candidates"], "100", "Not necessarily a technical trade score"),
    ("Market Technical", "Market", "OHLCV -> momentum_30_session_pct, relative_volume_vs_prior20, close_vs_sma20_pct, avg_dollar_volume_20_usd, annualized_historical_volatility_20_pct", "Step 5 OHLCV records", "100", "Separate PRE and POST weight profiles"),
    ("FDA V3 Model", "FDA clinical / safety / regulatory", "fda_clinical_score, fda_statistics_score, fda_meaningfulness_score, fda_safety_score, fda_clinical_pharmacology_score, fda_nonclinical_score, fda_cmc_score, fda_regulatory_score, fda_labeling_score, fda_benefit_risk_score; critical gates", SOURCES["FDA V3 review"], "%", "Approval forecast only if hard gates PASS"),
    ("PoA Consensus", "FDA approval models", "approval_probability, public_approval_probability (equal weight, both required)", SOURCES["PDUFA candidates"], "%", "Model estimates may share evidence"),
)
OVERLAPS = (
    ("Preliminary clinical", "Reviewed PRE clinical", "6 identical scoring domains / 100-point weights", "HIGH", "Keep one clinical evidence assessment with version and audit status."),
    ("POST Evidence", "POST Research Priority", "Clinical readout, financing, PDUFA, momentum and relative volume", "HIGH", "Never add these totals or treat as independent signals."),
    ("FDA V3", "Science / Safety / Regulatory / CMC", "Four FDA component columns can be seeded from the same saved stock fields", "HIGH", "Display one source lineage; FDA model is not independent confirmation."),
    ("Trade Score fallback", "Science / Safety / Regulatory / CMC", "Mean of those four components if trade_score column is absent", "HIGH", "Do not label fallback as a verified market-technical trade score."),
    ("Market Technical", "POST Evidence / Research Priority", "Price trend/momentum and relative volume derived from price bars", "MEDIUM", "Reuse one dated observation; prevent multi-counting in composites."),
    ("Internal approval probability", "Public approval probability", "Consensus averages the two; underlying source independence untested", "POTENTIAL", "Audit evidence provenance before treating as independent models."),
)

def present(value):
    return value is not None and str(value).strip().lower() not in ("", "none", "nan", "nat", "<na>", "not scored", "unknown")

def csv_rows(path, root="."):
    try:
        with (Path(root) / path).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except (OSError, ValueError, UnicodeError, csv.Error):
        return []

def load_sources(root="."):
    records = {key: csv_rows(path, root) for key, path in SOURCES.items()}
    try:
        with (Path(root) / PILOTS).open(encoding="utf-8") as handle:
            content = json.load(handle)
        records["PRE pilots"] = content.get("records", []) if isinstance(content, dict) else []
    except (OSError, ValueError, TypeError):
        records["PRE pilots"] = []
    return records

def filled(rows, field):
    return sum(present(row.get(field)) for row in rows)

def clinical_agreement(data):
    pilots = data.get("PRE pilots", [])
    strict = data.get("Pre-readout evidence", [])
    matched, equal, disagreements = 0, 0, []
    for pilot in pilots:
        candidates = [r for r in strict
                      if r.get("nct_id") == pilot.get("nct_id")
                      and r.get("ticker") == pilot.get("ticker")]
        if not candidates:
            continue
        matched += 1
        p = pilot.get("domain_points") or {}
        try:
            agreed = all(float(p[domain]) == float(r[domain + "_points"])
                         for _, domain, _ in CLINICAL
                         for r in candidates)
        except (TypeError, ValueError, KeyError):
            agreed = False
        if agreed:
            equal += 1
        else:
            disagreements.append(str(pilot.get("ticker") or pilot.get("nct_id")))
    return {"matched": matched, "equal": equal, "disagreements": disagreements}

def has_saved_gate_pass(row):
    """Only a gate's exact PASS state counts, not phrases like NOT PASS.

    This inspects stored text only and never certifies a newly verified entry
    or substitutes for independent primary-source evidence checks.
    """
    parts = str(row.get("Audited gate details") or "").split("|")
    return any(re.fullmatch(r"\s*[A-Za-z][A-Za-z_0-9 -]*:\s*PASS(?:\s*[—–-].*)?\s*",
                            part, flags=re.IGNORECASE) is not None for part in parts)


def coverage_status(observed, total):
    """Classify data *coverage*, not clinical quality or trade eligibility.

    One populated row out of hundreds must never make a missing-input finding
    look resolved. OBSERVED only means the expected field is filled throughout
    this saved snapshot; it does not certify values or FDA/financing outcomes.
    """
    if not isinstance(observed, int) or not isinstance(total, int) or total <= 0 or observed < 0 or observed > total:
        return "DATA GAP"
    if observed == 0:
        return "DATA GAP"
    return "REVIEW" if observed < total else "OBSERVED"


def audit_tests(data):
    candidates = data["PDUFA candidates"]
    fda = data["FDA V3 review"]
    finance = data["Post financing gates"]
    market = data["Post market status"]
    agreement = clinical_agreement(data)
    num = len(candidates)
    public = filled(candidates, "public_approval_probability")
    trading = filled(candidates, "trade_score")
    fda_p = filled(fda, "fda_probability")
    gates = sum(has_saved_gate_pass(row) for row in finance)
    tests = [
        {"Test": "Clinical model redundancy",
         "Status": "SHARED INPUT" if agreement["matched"] and agreement["matched"] == agreement["equal"] else "REVIEW",
         "Result": f'{agreement["equal"]}/{agreement["matched"]} matching PRE pilot score inputs agree',
         "Why it matters": "Matching point ledgers are not independent clinical confirmations."},
        {"Test": "Trade Score coverage", "Status": coverage_status(trading, num),
         "Result": f"{trading}/{num} stock rows contain trade_score",
         "Why it matters": "Missing saved scores must not be replaced by a clinical mean without a distinct label."},
        {"Test": "Public PoA coverage", "Status": coverage_status(public, num),
         "Result": f"{public}/{num} stock rows contain public_approval_probability",
         "Why it matters": "All-sources PoA requires both estimates; missing does not equal 0%."},
        {"Test": "FDA V3 calculated probability", "Status": coverage_status(fda_p, len(fda)),
         "Result": f"{fda_p}/{len(fda)} FDA review rows have fda_probability",
         "Why it matters": "Approval model remains gated until review evidence is sufficient."},
        {"Test": "Post Phase 3 entry gates", "Status": coverage_status(gates, len(finance)),
         "Result": f"{gates}/{len(finance)} financing-review rows contain at least one gate PASS",
         "Why it matters": "A recorded PASS covers only its named gate, not the whole event or a trading authorization; unresolved records remain blocked."},
        {"Test": "Market data overlap", "Status": "SHARED INPUT",
         "Result": f'{len(market)} market records; momentum + relative volume reused across 2 post models',
         "Why it matters": "One quote and date may legitimately support multiple models, but not multiple independent votes."},
    ]
    return tests

def score_inputs_for_ticker(data, ticker):
    """Inspection ONLY: ticker context is not an event-verified cross-source join."""
    output = []
    candidates = [r for r in data["PDUFA candidates"] if str(r.get("ticker", "")).upper() == ticker]
    for row in candidates:
        for field in ("event_key", "pdufa_date", "phase3_status", "approval_probability",
                      "public_approval_probability", "science_score", "regulatory_score",
                      "safety_score", "cmc_score", "trade_score", "cash", "cash_runway_months",
                      "short_interest", "shares_float", "iv_30d"):
            output.append({"Source": "PDUFA candidates", "Event / Trial": row.get("event_key", ""),
                           "Input column": field, "Value": str(row.get(field) or "") if present(row.get(field)) else "MISSING",
                           "Present": "YES" if present(row.get(field)) else "NO"})
    for row in data["FDA V3 review"]:
        if str(row.get("ticker", "")).upper() != ticker:
            continue
        for field in ("fda_application_identity", "fda_clinical_score", "fda_statistics_score",
                      "fda_safety_score", "fda_cmc_score", "fda_regulatory_score",
                      "fda_hard_gate", "fda_probability", "fda_gate_reason"):
            value = row.get(field)
            output.append({"Source": "FDA V3 review", "Event / Trial": row.get("event_key", ""),
                           "Input column": field, "Value": str(value)[:180] if present(value) else "MISSING",
                           "Present": "YES" if present(value) else "NO"})
    for row in data["PRE pilots"]:
        if str(row.get("ticker", "")).upper() != ticker:
            continue
        for label, domain, maximum in CLINICAL:
            points = (row.get("domain_points") or {}).get(domain)
            src = (row.get("domain_sources") or {}).get(domain) or {}
            output.append({"Source": "PRE pilot assessment", "Event / Trial": row.get("nct_id", ""),
                           "Input column": domain + " /" + str(maximum),
                           "Value": str(points) if points is not None else "MISSING",
                           "Present": "YES" if points is not None else "NO",
                           "Evidence URL": src.get("url", ""), "Evidence as-of": src.get("published", "")})
    for row in data["Pre-readout evidence"]:
        if str(row.get("ticker", "")).upper() != ticker:
            continue
        for label, domain, maximum in CLINICAL:
            field = domain + "_points"
            value = row.get(field)
            output.append({"Source": "PRE reviewed evidence inputs", "Event / Trial": row.get("nct_id", ""),
                           "Input column": field + " /" + str(maximum),
                           "Value": str(value) if present(value) else "MISSING",
                           "Present": "YES" if present(value) else "NO",
                           "Evidence URL": row.get(domain + "_source", ""),
                           "Evidence as-of": row.get(domain + "_source_date", "")})
    for row in data["Post market status"]:
        if str(row.get("ticker", "")).upper() != ticker:
            continue
        for field in ("trailing_momentum_pct", "relative_volume", "last_session", "market_source"):
            output.append({"Source": "Post market (ticker observation only)", "Event / Trial": "",
                           "Input column": field, "Value": str(row.get(field) or "") if present(row.get(field)) else "MISSING",
                           "Present": "YES" if present(row.get(field)) else "NO"})
    for row in data["Post financing gates"]:
        key = str(row.get("Exact financing event") or "")
        if key.split("|", 1)[0].upper() != ticker:
            continue
        for field in ("Historical second closing", "Second source", "Audited gate details", "Recheck freshness"):
            output.append({"Source": "Post financing (exact event)", "Event / Trial": key,
                           "Input column": field, "Value": str(row.get(field) or "")[:180] if present(row.get(field)) else "MISSING",
                           "Present": "YES" if present(row.get(field)) else "NO"})
    return output

def render_score_input_audit():
    import pandas as pd
    import streamlit as st

    st.markdown("## SCORING INPUTS & OVERLAP")
    st.caption("Read-only input lineage from saved datasets. This does not calculate new approval or trade probabilities.")

    # Each completed nightly scan publishes its own scored-input snapshot only
    # after the collector completes; source gaps stay REVIEW, never become 0.
    nightly_path = Path("data/nightly_scoring_audit.json")
    if nightly_path.is_file():
        try:
            nightly = json.loads(nightly_path.read_text(encoding="utf-8"))
            meta = nightly.get("source_scan", {})
            when = nightly.get("generated_at_utc", "")
            status = nightly.get("status", "UNKNOWN")
            when_dt = __import__("datetime").datetime.fromisoformat(str(when).replace("Z", "+00:00"))
            current = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            stale = ((current - when_dt).total_seconds() > 48 * 3600 or
                     (current - when_dt).total_seconds() < -3600)
            st.markdown("### Most recent automated post-scan scoring audit")
            a1, a2, a3 = st.columns(3)
            a1.metric("Audit status", status)
            a2.metric("Reported input gaps", int(nightly.get("counts", {}).get("data_gaps", 0)))
            a3.metric("Source scan run", str(meta.get("run_id") or "UNKNOWN"))
            st.caption("Audit saved: " + str(when) + " · Source: " + str(meta.get("workflow") or "UNKNOWN")
                       + " · Scan result: " + str(meta.get("conclusion") or "UNKNOWN"))
            if stale:
                st.warning("The stored scoring audit is older than 48 hours or has an invalid clock time. "
                           "It must not be treated as fresh verification.")
            elif status != "NO_INPUT_GAPS_FOUND":
                st.info("Audit is complete but some scoring inputs or scan evidence require review; "
                        "that is not a failure of the stock or an FDA outcome.")
            with st.expander("Show archived nightly scoring inputs and source provenance"):
                st.dataframe(pd.DataFrame(nightly.get("checks", [])),
                             hide_index=True, use_container_width=True)
                st.dataframe(pd.DataFrame(nightly.get("sources", [])),
                             hide_index=True, use_container_width=True)
                st.caption(str(nightly.get("provenance_note", "")))
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            st.warning("Last nightly scoring audit is unreadable; the current live input tables remain available.")
    else:
        st.info("No nightly scoring audit has been published yet. The automated audit runs "
                "after each completed overnight source scan, before Gmail/GitHub checks and safe repair.")
    data = load_sources()
    tests = audit_tests(data)
    attention = sum(t["Status"] in ("DATA GAP", "REVIEW") for t in tests)
    a, b, c, d = st.columns(4)
    a.metric("Scoring models mapped", len(MODELS))
    b.metric("Input tests", len(tests))
    c.metric("Data gaps / review", attention)
    d.metric("Overlap relationships", len(OVERLAPS))
    st.caption("Data gaps are not failed trials. Shared evidence is not independently corroborating evidence.")

    st.markdown("### 1. Automatic input tests")
    flags = st.multiselect("Test status", ["DATA GAP", "REVIEW", "SHARED INPUT", "OBSERVED"],
                           default=["DATA GAP", "REVIEW", "SHARED INPUT", "OBSERVED"], key="score_audit_status")
    visible = [t for t in tests if t["Status"] in flags]
    st.dataframe(pd.DataFrame(visible, columns=["Test", "Status", "Result", "Why it matters"]),
                 hide_index=True, use_container_width=True)
    st.download_button("EXPORT INPUT TEST RESULTS", pd.DataFrame(tests).to_csv(index=False),
                       file_name="scoring_input_tests.csv", mime="text/csv", use_container_width=True)

    st.markdown("### 2. Score-to-input column map")
    names = ["ALL MODELS"] + [m[0] for m in MODELS]
    choice = st.selectbox("Inspect scoring model", names, key="score_audit_model")
    lineage = pd.DataFrame(MODELS, columns=["Score / model", "Evidence family", "Contributing columns",
                                            "Stored data source", "Scale", "Interpretation"])
    if choice != "ALL MODELS":
        lineage = lineage[lineage["Score / model"] == choice]
    st.dataframe(lineage, hide_index=True, use_container_width=True)
    st.caption("These are formula-to-input mappings reviewed from the code, not proof that each source was collected.")

    st.markdown("### 3. Overlap / double-counting inspector")
    severity = st.selectbox("Shared-input severity", ["ALL", "HIGH", "MEDIUM", "POTENTIAL"],
                            key="score_audit_overlap_filter")
    overlaps = pd.DataFrame(OVERLAPS, columns=["Model A", "Model B", "Shared evidence", "Overlap", "Treatment"])
    if severity != "ALL":
        overlaps = overlaps[overlaps["Overlap"] == severity]
    st.dataframe(overlaps, hide_index=True, use_container_width=True)
    st.caption("HIGH indicates substantial shared input, not necessarily a coding error.")

    st.markdown("### 4. Ticker input inspector")
    tickers = sorted({str(row.get("ticker") or "").upper() for row in data["PDUFA candidates"]}
                     | {str(row.get("ticker") or "").upper() for row in data["PRE pilots"]})
    tickers = [t for t in tickers if t]
    if not tickers:
        st.warning("No candidate or pilot ticker input records found.")
        return
    chosen = st.selectbox("Ticker (inspect stored fields only)", tickers,
                          index=tickers.index("TRVI") if "TRVI" in tickers else 0,
                          key="score_audit_ticker")
    inspected = score_inputs_for_ticker(data, chosen)
    if inspected:
        missing_only = st.checkbox("Show missing inputs only", value=False, key="score_audit_missing")
        inspect_df = pd.DataFrame(inspected)
        if missing_only:
            inspect_df = inspect_df[inspect_df["Present"] == "NO"]
        st.dataframe(inspect_df, hide_index=True, use_container_width=True,
                     column_config={"Evidence URL": st.column_config.LinkColumn("Source link")})
        st.caption("Stock price is ticker-level. FDA and financing checks must be joined by exact event; "
                   "PRE clinical points use exact NCT. This panel displays inputs only, not joined evidence.")
    else:
        st.info("No stored inspectable input records for this ticker.")

    with st.expander("Model separation and data-quality rules"):
        st.write("Do not add research-priority, clinical and FDA model numbers into one combined percentage. "
                 "Do not average two scores when their evidence is the same. "
                 "Blank data means NOT SCORED, not a zero efficacy or approval outcome.")
        st.write("A shared quote or SEC filing should have one canonical event/source ID, checked timestamp "
                 "and provenance. Event-specific claims require exact ticker, drug, NCT and application matches.")
        st.write("Scores shown here are existing saved data. Neither these tests nor the 'observed' label "
                 "prove source accuracy, prospective performance, or investment suitability.")
