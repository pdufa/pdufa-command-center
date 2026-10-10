import streamlit as st
import streamlit.components.v1 as components
from table_groups import begin_table_render, grouped_dataframe, grouped_editor, render_column_tabs, set_stage_sources, staged_table, stage_filter_panel
from stages import program_stage
from pipeline_universe import STAGES as PIPELINE_STAGES, SOURCE_FILES as PIPELINE_SOURCE_FILES, load_universe as read_pipeline_universe, select_records as select_pipeline_records, stage_counts as pipeline_stage_counts
from strategy_view import render_strategy_page
from today_page import render_today
from pdufa_date_gradient import segment as pdufa_segment, date_color as pdufa_date_color
import pandas as pd
import json
from pathlib import Path
from datetime import date
import calendar
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import subprocess
import sys
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from scripts.phase_pipeline import read_rows as read_phase_rows, reconcile_records as reconcile_phase_records, master_additions as phase_master_additions, manual_master_additions as manual_phase_master_additions

begin_table_render()

st.set_page_config(
    page_title="PDUFA Command Center",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """<style>
:root{--font-main:16px;--font-small:14px;--font-title:30px;--font-h2:24px;--font-h3:19px}
html,body,[class*="css"]{font-size:var(--font-main) !important}
.stApp{background:#dff5e1;color:#17301d;font-size:var(--font-main)}
.block-container{padding-top:1rem;max-width:1550px}
h1{font-size:var(--font-title) !important;line-height:1.2 !important;margin:.35rem 0 .75rem !important}
h2{font-size:var(--font-h2) !important;line-height:1.25 !important;margin:.6rem 0 .65rem !important}
h3{font-size:var(--font-h3) !important;line-height:1.3 !important;margin:.5rem 0 .5rem !important}
p,li,div,span,label{line-height:1.45}
[data-testid="stMarkdownContainer"] p{font-size:var(--font-main) !important}
[data-testid="stCaptionContainer"],.stCaption{font-size:var(--font-small) !important;line-height:1.35 !important}
[data-testid="stMetric"]{background:#ffffff;border:2px solid #000000;border-radius:14px;padding:10px 12px;color:#111111;min-height:92px}
[data-testid="stMetric"] *{color:#111111 !important}
[data-testid="stMetricLabel"]{font-size:13px !important;line-height:1.2 !important}
[data-testid="stMetricValue"]{font-size:24px !important;line-height:1.15 !important}
[data-testid="stMetricDelta"]{font-size:13px !important}
.stButton button,.stDownloadButton button,[data-testid="stLinkButton"] a{font-size:15px !important;min-height:42px !important;padding:.45rem .8rem !important}
[data-baseweb="tab"]{font-size:15px !important}
[data-baseweb="radio"] label,[data-baseweb="select"] *,[data-baseweb="input"] input{font-size:15px !important}
[data-testid="stDataFrame"]{font-size:14px !important}
[data-testid="stDataFrame"] *{font-size:14px !important}
.card{background:#ffffff;border:2px solid #000000;border-radius:16px;padding:16px;margin:10px 0;color:#111111;font-size:15px;line-height:1.4}
.hero{background:#ffffff;border:2px solid #000000;border-radius:18px;padding:18px;color:#111111;font-size:16px}
.news-critical{border-left:4px solid #f97066}.news-important{border-left:4px solid #fdb022}.news-routine{border-left:4px solid #32d583}
.muted{color:#6f7f8c;font-size:14px}.green{color:#32d583}.amber{color:#fdb022}.red{color:#f97066}
.pill{display:inline-block;padding:4px 9px;border:1px solid #34516b;border-radius:99px;margin:0 6px 6px 0;font-size:12px}
.small{font-size:14px}.section{border-left:3px solid #34516b;padding-left:12px}
a,a:link,a:visited{color:#ffffff !important;text-decoration:none}
a:hover{color:#ffffff !important;text-decoration:underline}
a:active,a:focus{color:#ff8a00 !important}
.stLinkButton a,[data-testid="stLinkButton"] a{color:#ffffff !important}
.stLinkButton a:active,[data-testid="stLinkButton"] a:active{color:#ff8a00 !important}
.calendar-event-link{
  display:block;
  background:#ffffff;
  border:1px solid #111111;
  border-radius:8px;
  padding:7px 9px;
  margin:4px 0;
  color:#17211a !important;
  font-weight:600;
  text-decoration:none !important;
  line-height:1.25;
}
.calendar-event-link:link,
.calendar-event-link:visited,
.calendar-event-link:hover{color:#17211a !important}
.calendar-event-link:active,
.calendar-event-link:focus{color:#b45309 !important}
.merged-table-wrap{overflow:auto;background:#ffffff;border:2px solid #000000;border-radius:12px;padding:0;margin:8px 0 18px;color:#111111}
.merged-pdufa-table{border-collapse:separate;border-spacing:0;background:#ffffff;color:#111111;width:max-content;min-width:100%;font-size:13px}
.merged-pdufa-table th,.merged-pdufa-table td{border-right:1px solid #777;border-bottom:1px solid #777;padding:6px 8px;text-align:center;color:#111111;background:#ffffff;white-space:nowrap}
.merged-pdufa-table th a.sort-head{color:#111111 !important;text-decoration:none !important;font-weight:800;display:block;width:100%;height:100%;cursor:pointer}
.merged-pdufa-table th a.sort-head:hover{text-decoration:underline !important}
.merged-pdufa-table th .sort-icon{display:inline-block !important;margin-left:5px;padding:1px 4px;border:1.5px solid #000000;border-radius:4px;background:#ffffff;color:#000000 !important;font-size:14px !important;line-height:1.05 !important;font-weight:900 !important;vertical-align:middle}
.merged-pdufa-table th{position:sticky;top:0;z-index:4;background:#f4f4f4}
.merged-pdufa-table th.normal-head{height:158px;vertical-align:bottom;font-weight:700}
.merged-pdufa-table th.angle-head{position:sticky;top:0;min-width:38px;width:38px;height:158px;vertical-align:bottom;background:#f4f4f4;padding:0}
.merged-pdufa-table th.angle-head > span{position:absolute;left:20px;bottom:7px;display:inline-block;transform:rotate(45deg);transform-origin:bottom left;white-space:nowrap;font-weight:700;color:#111111}
.merged-pdufa-table th.ticker-head,.merged-pdufa-table td.ticker-cell{position:sticky;left:0;z-index:5;background:#fafafa;font-weight:700}
.merged-pdufa-table th.group-head{height:38px;background:#111111 !important;color:#ffffff !important;font-weight:900;border:2px solid #000000;border-bottom:2px solid #000000;font-size:15px}
.merged-pdufa-table th.group-subhead{height:124px;vertical-align:bottom;font-weight:800;min-width:92px;width:92px;max-width:92px;top:38px}
.merged-pdufa-table th.financing-subhead{background:#fff3bf !important;border-left:2px solid #000000;border-right:1px solid #000000}
.merged-pdufa-table th.financing-subhead .sort-head{white-space:normal !important;line-height:1.15 !important}
.merged-pdufa-table td.second-fin-cell{min-width:92px;width:92px;max-width:92px;font-weight:900;border-left:1px solid #000000}
.merged-pdufa-table td.second-fin-verified{background:#d9f7df !important;color:#0b6419 !important;font-size:19px !important;font-weight:900 !important}
.merged-pdufa-table th.application-subhead{height:124px;vertical-align:bottom;font-weight:800;min-width:42px;width:42px;max-width:42px;top:34px}
.merged-pdufa-table td.application-cell{min-width:42px;width:42px;max-width:42px;font-weight:800}
.merged-pdufa-table th.compact-p,.merged-pdufa-table td.compact-p{width:64px;min-width:64px;max-width:64px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.merged-pdufa-table th.ticker-head{z-index:6}
.merged-pdufa-table td.provision-yes{font-weight:800;font-size:18px}
.merged-pdufa-table td.provision-no{color:#555555}
.merged-pdufa-table td.provision-unknown{color:#7a7a7a;font-style:italic}
.merged-pdufa-table a,.merged-pdufa-table a:link,.merged-pdufa-table a:visited{color:#0b57d0 !important;text-decoration:underline !important}

/* iPhone / mobile web-app layout */
@media (max-width: 768px){
  :root{--font-main:15px;--font-small:12px;--font-title:24px;--font-h2:20px;--font-h3:17px}
  html,body{overscroll-behavior-y:none;-webkit-text-size-adjust:100%}
  .stApp{min-height:100dvh}
  .block-container{padding:.55rem .55rem 5rem !important;max-width:100% !important}
  h1{margin:.2rem 0 .45rem !important}
  h2{margin:.45rem 0 .4rem !important}
  [data-testid="stCaptionContainer"],.stCaption{font-size:12px !important}
  [data-testid="stMetric"]{min-height:76px;padding:8px 9px;border-radius:12px}
  [data-testid="stMetricValue"]{font-size:20px !important}
  [data-testid="stMetricLabel"]{font-size:11px !important}
  .stButton button,.stDownloadButton button,[data-testid="stLinkButton"] a{
    min-height:46px !important;
    font-size:15px !important;
    border-radius:12px !important;
    touch-action:manipulation;
  }
  [data-testid="stRadio"] [role="radiogroup"]{
    display:flex !important;
    flex-wrap:nowrap !important;
    overflow-x:auto !important;
    overflow-y:hidden !important;
    gap:6px !important;
    padding:2px 0 8px !important;
    -webkit-overflow-scrolling:touch;
    scrollbar-width:none;
  }
  [data-testid="stRadio"] [role="radiogroup"]::-webkit-scrollbar{display:none}
  [data-testid="stRadio"] label{
    flex:0 0 auto !important;
    white-space:nowrap !important;
    min-height:42px !important;
  }
  [data-testid="stDataFrame"]{max-width:100vw !important;overflow-x:auto !important}
  .card,.hero{padding:12px;border-radius:13px}
  .merged-table-wrap{margin-left:-2px;margin-right:-2px;-webkit-overflow-scrolling:touch}
  .merged-pdufa-table{font-size:12px}
  .merged-pdufa-table th,.merged-pdufa-table td{padding:5px 6px}
}
</style>""",
    unsafe_allow_html=True,
)


# 100-on-100 precision gate summary. This is intentionally separate from the
# 100% directional-coverage layer: REVIEW/NO_CALL cases do not qualify.
@st.cache_data(ttl=60)
def load_100_on_100_summary():
    path = Path("data/fda_100_on_100_summary.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

@st.cache_data(ttl=60)
def load_100_on_100_live():
    path = Path("data/fda_100_on_100_live.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_historical_assessed_decisions():
    try:
        return pd.read_csv("data/historical_assessed_decisions.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_strict_historical_126_review():
    try:
        return pd.read_csv("data/strict_historical_126_review.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_data():
    # Defensive repair: older exports accidentally used literal "\\n" between CSV rows.
    # Read as text first and normalize before parsing so the master list never collapses to one record.
    from io import StringIO
    with open("data/pdufa_candidates.csv", "r", encoding="utf-8") as f:
        raw = f.read()
    if "\\n" in raw:
        raw = raw.replace("\\n", "\n")
    x = pd.read_csv(StringIO(raw))

    # Persistent second-financing milestone backfill. Kept separate from the
    # primary candidate feed so financing verification can be audited/updated
    # without rewriting unrelated PDUFA fields.
    try:
        sf = pd.read_csv("data/second_financing_status.csv", keep_default_na=False)
        sf["event_key"] = sf["event_key"].astype(str)
        x["event_key"] = x["event_key"].astype(str)
        keep = [
            "event_key","second_financing_status","second_financing_announced",
            "second_financing_running","second_financing_closed",
            "first_financing_date","first_financing_source",
            "second_financing_date","second_financing_source",
            "second_financing_audit_status","second_financing_evidence_note",
            "verified_as_of",
        ]
        sf = sf[[c for c in keep if c in sf.columns]].copy()
        x = x.merge(sf, on="event_key", how="left", validate="one_to_one")
    except Exception:
        pass

    required = ["ticker","company","drug","indication","pdufa_date"]
    for c in required:
        if c not in x:
            x[c] = pd.NA

    optional_text = [
        "event_key","signal","confidence","science_summary","regulatory_summary","trading_summary",
        "evidence_cutoff","evidence_summary","application_type","financing_status",
        "setup_phase","outcome","financing_summary","pdufa_confirmation","market_cap_bucket",
        "reported_p_values","phase3_status","nct_id","conflict_flag","monitor_eligibility",
        "check_status","last_checked","pdufa_evidence_url","trial_evidence_url",
        "financing_evidence_url","new_dilution_flag","financing_proceeds",
        "second_financing_status","second_financing_announced","second_financing_running",
        "second_financing_closed","second_financing_announcement",
        "second_financing_in_progress","second_financing_close_verified"
    ]
    optional_numeric = [
        "approval_probability","public_approval_probability","science_score","regulatory_score","safety_score",
        "cmc_score","market_cap","trade_score","short_interest","iv_30d",
        "price_last","return_30d_pct","avg_volume_20d","short_ratio","shares_float",
        "institutional_ownership_pct","cash","cash_runway_months"
    ]
    optional_dates = [
        "phase1_date","phase2_date","phase3_date","nda_submission_date",
        "fda_acceptance_date","decision_date","financing_close_date"
    ]

    for c in optional_text:
        if c not in x:
            x[c] = pd.NA
    for c in optional_numeric:
        if c not in x:
            x[c] = pd.NA
        x[c] = pd.to_numeric(x[c], errors="coerce")
    for c in optional_dates:
        if c not in x:
            x[c] = pd.NaT
        x[c] = pd.to_datetime(x[c], errors="coerce")

    x["pdufa_date"] = pd.to_datetime(x["pdufa_date"], errors="coerce")
    x["approval_probability"] = x["approval_probability"].apply(
        lambda v: v * 100 if pd.notna(v) and 0 <= float(v) <= 1 else v
    )
    x["public_approval_probability"] = x["public_approval_probability"].apply(
        lambda v: v * 100 if pd.notna(v) and 0 <= float(v) <= 1 else v
    )
    return x


@st.cache_data(ttl=120)
def load_prediction_history():
    x = pd.read_csv("data/prediction_engine_history.csv")
    required = [
        "ticker","pdufa_date","event_key","p_approval","model_class","actual_outcome",
        "validation_period","independence_status","historical_market_cap_billions",
        "market_cap_match_method","market_cap_bucket","correct"
    ]
    for col in required:
        if col not in x:
            x[col] = pd.NA
    for col in ["cap_recovery_confidence","cap_recovery_method","public_approval_probability","public_model_class","public_evidence_note","internal_direction_class","internal_direction_note","reported_p_values"]:
        if col not in x:
            x[col] = pd.NA
    x["public_approval_probability"] = pd.to_numeric(x["public_approval_probability"], errors="coerce")
    x["pdufa_date"] = pd.to_datetime(x["pdufa_date"], errors="coerce")
    x["p_approval"] = pd.to_numeric(x["p_approval"], errors="coerce")
    x["historical_market_cap_billions"] = pd.to_numeric(
        x["historical_market_cap_billions"], errors="coerce"
    )
    x["correct"] = x["correct"].astype("string")

    try:
        audit = pd.read_csv("data/prediction_engine_audit.csv")
        audit["event_key"] = audit["event_key"].astype(str)
        x["event_key"] = x["event_key"].astype(str)
        x = x.merge(audit, on="event_key", how="left")
    except Exception:
        x["audit_status"] = pd.NA
        x["failure_reason"] = pd.NA
        x["count_in_audited_accuracy"] = pd.NA
        x["verified_note"] = pd.NA
        x["source_url"] = pd.NA
        x["canonical_pdufa_date"] = pd.NA
        x["audit_action"] = pd.NA
        x["needs_rescore"] = pd.NA

    if "source_url" not in x:
        x["source_url"] = pd.NA

    # Persistent Phase 3 p-value backfill. This is display/audit evidence only;
    # it does not rewrite the frozen historical prediction inputs.
    try:
        pvalues = pd.read_csv("data/prediction_engine_pvalues.csv", keep_default_na=False)
        pvalues["event_key"] = pvalues["event_key"].astype(str)
        x["event_key"] = x["event_key"].astype(str)
        p_keep = [
            "event_key","reported_p_values","p_value_audit_status",
            "p_value_source_url","p_value_evidence_note",
        ]
        pvalues = pvalues[[c for c in p_keep if c in pvalues.columns]].copy()
        pvalues = pvalues.rename(columns={"reported_p_values":"reported_p_values_backfill"})
        x = x.merge(pvalues, on="event_key", how="left", validate="one_to_one")
        if "reported_p_values_backfill" in x:
            existing_p = x["reported_p_values"].fillna("").astype(str).str.strip()
            backfill_p = x["reported_p_values_backfill"].fillna("").astype(str).str.strip()
            x["reported_p_values"] = existing_p.where(existing_p.ne(""), backfill_p)
            x = x.drop(columns=["reported_p_values_backfill"])
    except Exception:
        for col in ["p_value_audit_status","p_value_source_url","p_value_evidence_note"]:
            if col not in x:
                x[col] = ""

    # Persistent regulatory-designation backfill. This is kept separate from
    # the frozen prediction history so display research cannot rewrite model inputs.
    try:
        designations = pd.read_csv("data/prediction_engine_designations.csv", keep_default_na=False)
        designations["event_key"] = designations["event_key"].astype(str)
        x["event_key"] = x["event_key"].astype(str)
        designation_fields = [
            "orphan_drug","no_available_therapy","serious_condition","life_threatening",
            "fast_track","breakthrough_therapy","priority_review","accelerated_approval",
            "rmat","qidp","rare_pediatric_disease","priority_review_voucher",
            "rolling_review","rtor","project_orbis","spa",
            "designation_audit_status","designation_source_url","designation_evidence_note",
        ]
        keep_cols = ["event_key"] + [c for c in designation_fields if c in designations.columns]
        x = x.merge(designations[keep_cols], on="event_key", how="left", validate="one_to_one")
    except Exception:
        for col in [
            "orphan_drug","no_available_therapy","serious_condition","life_threatening",
            "fast_track","breakthrough_therapy","priority_review","accelerated_approval",
            "rmat","qidp","rare_pediatric_disease","priority_review_voucher",
            "rolling_review","rtor","project_orbis","spa",
            "designation_audit_status","designation_source_url","designation_evidence_note",
        ]:
            if col not in x:
                x[col] = ""

    x["audit_status"] = x["audit_status"].fillna("UNREVIEWED")
    # YES here means "keep in adjusted score unless a verified invalid mapping
    # has been explicitly excluded". It is not a claim that every row is fully audited.
    x["count_in_audited_accuracy"] = x["count_in_audited_accuracy"].fillna("YES")
    return x


@st.cache_data(ttl=120)
def load_prediction_rescore_queue():
    try:
        q = pd.read_csv("data/prediction_engine_rescore_queue.csv")
    except Exception:
        q = pd.DataFrame()
    return q


@st.cache_data(ttl=120)
def load_fda_v3_historical_summary():
    try:
        with open("data/fda_v3_historical_summary.json", "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@st.cache_data(ttl=120)
def load_fda_v3_historical_backfill_queue():
    try:
        return pd.read_csv("data/fda_v3_historical_backfill_queue.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_v3_historical_backtest():
    try:
        return pd.read_csv("data/fda_v3_historical_backtest.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_directional_100pct_summary():
    try:
        with open("data/fda_directional_100pct_summary.json", "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@st.cache_data(ttl=120)
def load_fda_directional_100pct_live():
    try:
        return pd.read_csv("data/fda_directional_100pct_live.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_directional_residual_miss_audit():
    try:
        return pd.read_csv("data/fda_directional_residual_miss_audit.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_regulatory_signal_monitor():
    try:
        return pd.read_csv("data/fda_regulatory_signal_monitor.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_pdufa_extension_ledger():
    try:
        return pd.read_csv("data/fda_pdufa_extension_ledger.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def load_fda_review_engine():
    try:
        x = pd.read_csv("data/fda_review_engine.csv", keep_default_na=False)
    except Exception:
        x = pd.DataFrame()
    required = [
        "event_key","ticker","drug","pdufa_date",
        "fda_regulatory_case_id","fda_count_in_match",
        "fda_application_identity","fda_clinical_score","fda_statistics_score",
        "fda_primary_endpoint_status","fda_multiplicity_status","fda_missing_data_status",
        "fda_effect_size_status","fda_replication_status","fda_statistics_gate",
        "fda_meaningfulness_score","fda_safety_score","fda_clinical_pharmacology_score",
        "fda_nonclinical_score","fda_cmc_score","fda_process_validation_status",
        "fda_stability_status","fda_analytical_methods_status","fda_comparability_status",
        "fda_supplier_status","fda_cmc_gate","fda_inspection_status",
        "fda_warning_letter_status","fda_import_alert_status","fda_form483_status",
        "fda_facility_classification","fda_preapproval_inspection_status","fda_facility_gate",
        "fda_bimo_status","fda_data_integrity_gate",
        "fda_regulatory_score","fda_labeling_score","fda_benefit_risk_score",
        "fda_evidence_freshness","fda_hard_gate","fda_probability","fda_prediction",
        "fda_confidence","fda_gate_reason","fda_model_version",
        "fda_prediction_frozen_at","fda_last_evaluated_at","decision_date",
        "actual_fda_decision","fda_match_result","fda_source_note"
    ]
    for col in required:
        if col not in x:
            x[col] = ""
    return x[required]


@st.cache_data(ttl=120)
def load_fda_facility_registry():
    try:
        x = pd.read_csv("data/fda_facility_registry.csv", keep_default_na=False)
    except Exception:
        x = pd.DataFrame()
    required = [
        "event_key","fda_regulatory_case_id","ticker","drug","site_name","site_country",
        "site_role","fei","warning_letter_status","import_alert_status","form483_status",
        "facility_classification","preapproval_inspection_status","remediation_status",
        "evidence_as_of","source_url","source_note"
    ]
    for col in required:
        if col not in x:
            x[col] = ""
    return x[required]


@st.cache_data(ttl=120)
def load_fda_review_backfill_queue():
    try:
        x = pd.read_csv("data/fda_review_backfill_queue.csv", keep_default_na=False)
    except Exception:
        x = pd.DataFrame()
    required = [
        "event_key","ticker","drug","pdufa_date","priority","days_to_pdufa",
        "missing_components","backfill_status","source_targets","decision_date",
        "actual_fda_decision","notes"
    ]
    for col in required:
        if col not in x:
            x[col] = ""
    return x[required]


@st.cache_data(ttl=120)
def load_fda_prediction_freezes():
    try:
        x = pd.read_csv("data/fda_prediction_freezes.csv", keep_default_na=False)
    except Exception:
        x = pd.DataFrame()
    required = [
        "freeze_id","event_key","ticker","drug","pdufa_date","fda_regulatory_case_id","evidence_cutoff",
        "fda_probability","fda_prediction","fda_confidence","fda_hard_gate",
        "fda_gate_reason","frozen_at","model_version","decision_date",
        "actual_fda_decision","match_result"
    ]
    for col in required:
        if col not in x:
            x[col] = ""
    return x[required]


@st.cache_data(ttl=60)
def load_recheck_status():
    try:
        x = pd.read_csv("data/recheck_status.csv", keep_default_na=False)
    except Exception:
        x = pd.DataFrame()
    required = [
        "event_key","ticker","company","drug","pdufa_date","run_status","requested_scope",
        "started_at_utc","completed_at_utc","last_successful_recheck_utc","change_count","error_count"
    ]
    for cat in ["pdufa_date","phase3","financing","cash_runway","market_data","ownership_insiders"]:
        required += [f"{cat}_status", f"{cat}_note", f"{cat}_source"]
    for col in required:
        if col not in x:
            x[col] = ""
    return x[required]


def run_recheck_worker(event_key=None, run_all=False, categories=None):
    categories = categories or ["pdufa_date","phase3","financing","cash_runway","market_data","ownership_insiders"]
    cmd = [sys.executable, "scripts/recheck_events.py", "--categories", ",".join(categories)]
    if run_all:
        cmd.append("--all")
    elif event_key:
        cmd += ["--event-key", str(event_key)]
    else:
        raise ValueError("event_key or run_all is required")
    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Recheck failed").strip())
    # Refresh the FDA-only decision layer after evidence recheck.
    fda_cmd = [sys.executable, "scripts/fda_decision_engine.py"]
    if event_key:
        fda_cmd += ["--event-key", str(event_key)]
    fda_result = subprocess.run(
        fda_cmd,
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if fda_result.returncode != 0:
        raise RuntimeError((fda_result.stderr or fda_result.stdout or "FDA decision engine failed").strip())

    # Keep the same regulatory stack in sync for manual and nightly rechecks.
    for script in [
        "scripts/fda_regulatory_signal_monitor.py",
        "scripts/fda_directional_100pct.py",
        "scripts/fda_pdufa_extension_tracker.py",
        "scripts/fda_100_on_100_gate.py",
    ]:
        step = subprocess.run(
            [sys.executable, script],
            cwd=str(Path(__file__).resolve().parent),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if step.returncode != 0:
            raise RuntimeError((step.stderr or step.stdout or f"{script} failed").strip())

    load_data.clear()
    load_recheck_status.clear()
    load_fda_review_engine.clear()
    load_fda_review_backfill_queue.clear()
    load_fda_prediction_freezes.clear()
    load_fda_regulatory_signal_monitor.clear()
    load_fda_directional_100pct_live.clear()
    load_fda_directional_100pct_summary.clear()
    load_100_on_100_summary.clear()
    load_100_on_100_live.clear()
    load_historical_assessed_decisions.clear()
    load_strict_historical_126_review.clear()
    load_fda_pdufa_extension_ledger.clear()
    payload = (result.stdout or "").strip().splitlines()
    return payload[-1] if payload else "Recheck completed"


def _plain_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _classify_story(title, description=""):
    text = f"{title} {description}".lower()

    financing_words = [
        "public offering", "registered direct", "private placement", "atm offering",
        "at-the-market", "shelf registration", "s-3", "424b", "financing",
        "offering closes", "offering closed", "prices offering", "priced offering",
        "dilution", "securities offering",
    ]
    regulatory_words = [
        "fda", "pdufa", "complete response letter", " crl", "adcom",
        "advisory committee", "nda", "bla", "snda", "sbla", "fast track",
        "breakthrough therapy", "priority review", "orphan drug", "clinical hold",
    ]
    clinical_words = [
        "phase 3", "phase iii", "pivotal", "topline", "top-line", "trial",
        "primary endpoint", "secondary endpoint", "efficacy", "safety data",
        "clinical data", "study results",
    ]
    trading_words = [
        "analyst", "price target", "upgrade", "downgrade", "short interest",
        "institutional", "hedge fund", "insider", "options activity",
        "acquisition", "merger", "licensing deal", "partnership",
    ]

    if any(k in text for k in financing_words):
        category = "FINANCING / SEC"
    elif any(k in text for k in regulatory_words):
        category = "FDA / REGULATORY"
    elif any(k in text for k in clinical_words):
        category = "CLINICAL"
    elif any(k in text for k in trading_words):
        category = "TRADING"
    else:
        category = "COMPANY"

    critical_phrases = [
        "complete response letter", " crl", "clinical hold", "fda rejects",
        "fda declines", "fda denies", "fda approves", "approved by the fda",
        "pdufa date extended", "pdufa date changed", "pdufa extension",
        "public offering", "registered direct", "atm offering", "at-the-market",
        "prices offering", "priced offering", "safety signal", "patient death",
        "fatal adverse", "trial stopped", "trial halted",
    ]
    important_phrases = [
        "pdufa", "priority review", "fast track", "breakthrough therapy",
        "orphan drug", "nda accepted", "bla accepted", "phase 3", "phase iii",
        "pivotal", "topline", "top-line", "primary endpoint", "financing",
        "offering closed", "offering closes", "partnership", "licensing",
        "upgrade", "downgrade",
    ]

    if any(k in text for k in critical_phrases):
        priority = "CRITICAL"
    elif any(k in text for k in important_phrases):
        priority = "IMPORTANT"
    else:
        priority = "ROUTINE"

    return category, priority


@st.cache_data(ttl=900, show_spinner=False)
def fetch_ticker_news(ticker, company, drug="", days=7):
    terms = [ticker]
    if company:
        terms.append(f'"{company}"')
    if drug and str(drug).strip() and str(drug).strip().lower() != "nan":
        terms.append(f'"{str(drug).strip()}"')

    company_clause = " OR ".join(terms)
    catalyst_clause = (
        'FDA OR PDUFA OR "Phase 3" OR pivotal OR trial OR approval OR CRL '
        'OR offering OR financing OR SEC OR partnership OR analyst'
    )
    query = f"({company_clause}) ({catalyst_clause}) when:{int(days)}d"
    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(
            {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        )
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 PDUFA-Command-Center/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
        root = ET.fromstring(raw)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

    stories = []
    for item in root.findall(".//item"):
        title = _plain_text(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        description = _plain_text(item.findtext("description"))
        pub_raw = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = _plain_text(source_el.text if source_el is not None else "") or "News source"

        try:
            published = parsedate_to_datetime(pub_raw)
            published_iso = published.isoformat()
        except Exception:
            published_iso = ""

        category, priority = _classify_story(title, description)
        stories.append(
            {
                "ticker": ticker,
                "title": title,
                "link": link,
                "source": source,
                "published": published_iso,
                "category": category,
                "priority": priority,
                "description": description,
            }
        )

    deduped = []
    seen = set()
    for story in stories:
        key = re.sub(r"[^a-z0-9]+", "", story["title"].lower())
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(story)

    return deduped[:25], None


def _story_timestamp(value):
    if not value:
        return pd.Timestamp.min.tz_localize("UTC")
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert("UTC")
    except Exception:
        return pd.Timestamp.min.tz_localize("UTC")


@st.cache_data(ttl=60)
def load_pipeline_universe_data(signature, pipeline_today):
    return read_pipeline_universe(Path("data"), today=pipeline_today)


@st.cache_data(ttl=60)
def load_issue_trial_catalog(signature):
    columns = [
        "issue", "ticker", "company", "drug", "trial_name", "nct_id",
        "evidence_url", "target_population_note", "phase", "status",
        "source_updated", "checked_at",
    ]
    path = Path("data/issue_trials.csv")
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        catalog = pd.read_csv(path, dtype=str).fillna("")
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame(columns=columns)
    ledger_path = Path("data/all_phase_trials.csv")
    if ledger_path.exists():
        try:
            ledger = pd.read_csv(ledger_path, dtype=str).fillna("")
            if "nct_id" in ledger:
                ledger = ledger.drop_duplicates("nct_id").set_index("nct_id")
                for column in ("phase", "status", "source_updated", "checked_at"):
                    if column in ledger:
                        catalog[column] = catalog["nct_id"].map(ledger[column]).fillna("")
        except (OSError, ValueError, pd.errors.ParserError):
            pass
    for column in columns:
        if column not in catalog:
            catalog[column] = ""
    return catalog[columns]


@st.cache_data(ttl=60)
def load_phase_pipeline_data(version):
    records = read_phase_rows(Path("data/phase_pipeline.csv"))
    try:
        state = json.loads(Path("data/phase_pipeline_state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    return records, state


def current_phase_pipeline():
    path = Path("data/phase_pipeline.csv")
    version = path.stat().st_mtime_ns if path.exists() else 0
    records, state = load_phase_pipeline_data(version)
    source_today = datetime.now(timezone.utc).date()
    records = reconcile_phase_records(records, [], source_today, int(state.get("source_max_age_days", 180)))
    return records, state


def master_with_phase3(live):
    records, state = current_phase_pipeline()
    additions = phase_master_additions(records, live.to_dict("records"))
    additions += manual_phase_master_additions(records, live.to_dict("records") + additions, st.session_state.get("pipeline_master_transfers", {}))
    result = pd.concat([live.copy(), pd.DataFrame(additions)], ignore_index=True, sort=False) if additions else live.copy()
    for col in ("pdufa_date", "phase1_date", "phase2_date", "phase3_date", "phase3_start_date", "nda_submission_date", "fda_acceptance_date", "decision_date", "financing_close_date"):
        if col in result:
            result[col] = pd.to_datetime(result[col], errors="coerce")
    for col in ("approval_probability", "public_approval_probability", "trade_score", "market_cap", "cash", "cash_runway_months", "short_interest", "iv_30d"):
        if col in result:
            result[col] = pd.to_numeric(result[col], errors="coerce")
    if "current_stage" not in result:
        result["current_stage"] = pd.NA
    fallback = pd.Series("PHASE 3 / REGULATORY REVIEW", index=result.index)
    if "pdufa_date" in result:
        fallback.loc[result["pdufa_date"].notna()] = "PDUFA SCHEDULED"
    if "decision_date" in result:
        local_today = pd.Timestamp(datetime.now(ZoneInfo("America/Los_Angeles")).date())
        fallback.loc[result["decision_date"].notna() & result["decision_date"].le(local_today)] = "FDA DECISION RECORDED"
    result["current_stage"] = result["current_stage"].fillna(fallback)
    return result, additions, state


df = load_data()
prediction_history = load_prediction_history()
prediction_rescore_queue = load_prediction_rescore_queue()
fda_v3_hist_summary = load_fda_v3_historical_summary()
fda_v3_hist_queue = load_fda_v3_historical_backfill_queue()
fda_v3_hist_backtest = load_fda_v3_historical_backtest()
fda_directional_summary = load_fda_directional_100pct_summary()
fda_directional_live = load_fda_directional_100pct_live()
historical_assessed_decisions = load_historical_assessed_decisions()
historical_assessed_by_key = {
    str(r["event_key"]): r for r in historical_assessed_decisions.to_dict("records")
}
fda_directional_residual = load_fda_directional_residual_miss_audit()
fda_regulatory_signals = load_fda_regulatory_signal_monitor()
fda_extension_ledger = load_fda_pdufa_extension_ledger()
fda_reviews = load_fda_review_engine()
fda_facilities = load_fda_facility_registry()
fda_backfill_queue = load_fda_review_backfill_queue()
fda_freezes = load_fda_prediction_freezes()
if not fda_reviews.empty and "event_key" in df:
    fda_merge_cols = ["event_key"] + [c for c in fda_reviews.columns if c.startswith("fda_")]
    df["event_key"] = df["event_key"].astype(str)
    fda_reviews["event_key"] = fda_reviews["event_key"].astype(str)
    df = df.merge(
        fda_reviews[fda_merge_cols].drop_duplicates("event_key", keep="last"),
        on="event_key",
        how="left",
        validate="many_to_one"
    )

stage_pipeline_records, _stage_scan = current_phase_pipeline()
stage_live_records = df.to_dict("records")
stage_arrivals = phase_master_additions(stage_pipeline_records, stage_live_records)
stage_arrivals += manual_phase_master_additions(stage_pipeline_records, stage_live_records + stage_arrivals, st.session_state.get("pipeline_master_transfers", {}))
stage_phase2 = {}
for _stage_record in sorted(stage_pipeline_records, key=lambda r: r.get("source_updated", ""), reverse=True):
    if _stage_record.get("destination") == "PIPELINE":
        stage_phase2.setdefault(_stage_record["program_key"], _stage_record)
set_stage_sources(stage_live_records + stage_arrivals + list(stage_phase2.values()) + prediction_history.to_dict("records"))

# Startup data validation: fail loudly on structural problems instead of silently
# rendering a misleading one-row/partial dashboard.
required_source_columns = ["ticker","company","drug","indication","pdufa_date"]
missing_source_columns = [c for c in required_source_columns if c not in df.columns]
if missing_source_columns:
    st.error("DATA ERROR — missing required column(s): " + ", ".join(missing_source_columns))
    st.stop()
if len(df) <= 1:
    st.error("DATA ERROR — PDUFA feed contains one or fewer parsed rows.")
    st.stop()
if df["ticker"].isna().all():
    st.error("DATA ERROR — ticker column is empty.")
    st.stop()

today = pd.Timestamp(datetime.now(ZoneInfo("America/Los_Angeles")).date())
future = df[df["pdufa_date"].notna() & (df["pdufa_date"] >= today)].copy()
future["days"] = (future["pdufa_date"] - today).dt.days
future = future.sort_values("pdufa_date")

# Normalize optional fields used by the new functional display.
if "market_cap" not in df:
    for alt in ["market_cap_usd", "mkt_cap", "marketcap"]:
        if alt in df:
            df["market_cap"] = pd.to_numeric(df[alt], errors="coerce")
            break
    else:
        df["market_cap"] = pd.NA
if "trade_score" not in df:
    score_cols = [c for c in ["science_score","regulatory_score","safety_score","cmc_score"] if c in df]
    df["trade_score"] = df[score_cols].mean(axis=1) if score_cols else pd.NA
for c in ["financing_status","setup_phase","short_interest","iv_30d","outcome",
          "phase1_date","phase2_date","phase3_date","nda_submission_date",
          "fda_acceptance_date","decision_date"]:
    if c not in df:
        df[c] = pd.NA

for c in ["phase1_date","phase2_date","phase3_date","nda_submission_date",
          "fda_acceptance_date","decision_date"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")
for c in ["market_cap","trade_score","short_interest","iv_30d"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Refresh normalized values into future. A verified FDA decision closes the
# matter immediately, even when FDA acts before the scheduled PDUFA target.
future = df[df["pdufa_date"].notna() & (df["pdufa_date"] >= today)].copy()
future = future[
    ~(future["decision_date"].notna() & (future["decision_date"].dt.normalize() <= today))
].copy()
future["days"] = (future["pdufa_date"] - today).dt.days
future = future.sort_values("pdufa_date")

def fmt_cap(v):
    if pd.isna(v):
        return "Not available"
    v = float(v)
    if v >= 1_000_000_000:
        return "$" + f"{v/1_000_000_000:.1f}B"
    return "$" + f"{v/1_000_000:.0f}M"

def fmt_pct(v, decimals=0):
    if pd.isna(v):
        return "Not available"
    x = float(v)
    if -1 <= x <= 1:
        x *= 100
    return f"{x:.{decimals}f}%"

def fmt_app_pct(v, decimals=1):
    if v is None or pd.isna(v):
        return "Not scored"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "Not scored"
    if 0 <= x <= 1:
        x *= 100
    return f"{x:.{decimals}f}%"

def combined_probability_direction(row):
    p = displayed_probability_text(row, 1)
    f = predicted_fda_direction(row)
    if not p or f not in ["APPROVED", "CRL", "REVIEW"]:
        return ""
    return f"{p} · {f}"


def optimizer_original_direction(row):
    """Frozen/pre-decision direction used for historical threshold optimization."""
    model = safe_text(row.get("model_class"), "").upper()
    if model in ["APPROVED", "CRL"]:
        return model
    return predicted_fda_direction(row)


def optimizer_gate_call(row, approve_min, crl_max):
    """High-confidence overlay: keep an original direction only beyond locked probability thresholds."""
    p = displayed_probability_value(row)
    if p is None or pd.isna(p):
        return "REVIEW"
    p = float(p)
    base = optimizer_original_direction(row)
    if base == "APPROVED" and p >= float(approve_min):
        return "APPROVED"
    if base == "CRL" and p <= float(crl_max):
        return "CRL"
    return "REVIEW"


def optimizer_metrics(frame, approve_min, crl_max):
    """Return called-case Match % and coverage without counting REVIEW as a miss."""
    if frame is None or frame.empty:
        return {"eligible":0, "calls":0, "correct":0, "match_pct":pd.NA, "coverage_pct":pd.NA}

    calls = frame.apply(lambda r: optimizer_gate_call(r, approve_min, crl_max), axis=1)
    actual = frame.apply(
        lambda r: normalize_fda_direction(r.get("actual_outcome", r.get("outcome"))), axis=1
    )
    eligible_mask = actual.isin(["APPROVED","CRL"])
    called_mask = calls.isin(["APPROVED","CRL"]) & eligible_mask
    eligible = int(eligible_mask.sum())
    n_calls = int(called_mask.sum())
    correct = int((calls[called_mask] == actual[called_mask]).sum()) if n_calls else 0
    match_pct = pd.NA if n_calls == 0 else correct / n_calls * 100.0
    coverage_pct = pd.NA if eligible == 0 else n_calls / eligible * 100.0
    return {
        "eligible": eligible,
        "calls": n_calls,
        "correct": correct,
        "match_pct": match_pct,
        "coverage_pct": coverage_pct,
    }


def optimize_match_gate(frame, minimum_coverage_pct=30.0, minimum_calls=5):
    """Tune thresholds on one cohort only. Maximize Match %, then coverage, then calls."""
    if frame is None or frame.empty:
        return None

    best = None
    # Conservative search: CRL threshold 5-45; approval threshold 55-99.
    for crl_max in range(5, 46):
        for approve_min in range(55, 100):
            if crl_max >= approve_min:
                continue
            m = optimizer_metrics(frame, approve_min, crl_max)
            if m["calls"] < int(minimum_calls):
                continue
            if pd.isna(m["coverage_pct"]) or float(m["coverage_pct"]) < float(minimum_coverage_pct):
                continue
            key = (
                float(m["match_pct"]) if not pd.isna(m["match_pct"]) else -1.0,
                float(m["coverage_pct"]) if not pd.isna(m["coverage_pct"]) else -1.0,
                int(m["calls"]),
                float(approve_min - crl_max),
            )
            if best is None or key > best["key"]:
                best = {
                    "approve_min": approve_min,
                    "crl_max": crl_max,
                    "metrics": m,
                    "key": key,
                }
    return best


def optimizer_case_table(frame, approve_min, crl_max):
    """Case-level audit table for the locked gate."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    out = frame.copy()
    out["P%"] = out.apply(lambda r: displayed_probability_text(r, 1), axis=1)
    out["Original F"] = out.apply(optimizer_original_direction, axis=1)
    out["Optimized F"] = out.apply(lambda r: optimizer_gate_call(r, approve_min, crl_max), axis=1)
    out["Actual FDA"] = out.apply(
        lambda r: normalize_fda_direction(r.get("actual_outcome", r.get("outcome"))) or "", axis=1
    )
    out["Match %"] = out.apply(
        lambda r: (
            "100%" if r["Optimized F"] in ["APPROVED","CRL"] and r["Optimized F"] == r["Actual FDA"]
            else ("0%" if r["Optimized F"] in ["APPROVED","CRL"] and r["Actual FDA"] in ["APPROVED","CRL"] else "")
        ),
        axis=1,
    )
    return out


def calendar_app_text(row, field):
    """Never display a missing/unscored calendar probability as 0%."""
    value = row.get(field)
    if value is None or pd.isna(value):
        return "Not scored"
    confidence = safe_text(row.get("confidence"), "").upper()
    if float(value) == 0 and confidence in ["", "NOT SCORED", "UNSCORED"]:
        return "Not scored"
    return fmt_app_pct(value, 1)

def fmt_num(v, decimals=0):
    if pd.isna(v):
        return "Not available"
    return f"{float(v):,.{decimals}f}"

def safe_text(v, default="Not available"):
    if v is None or pd.isna(v):
        return default
    s = str(v).strip()
    return default if not s or s.lower() in ["nan", "none", "<na>"] else s

def render_historical_assessed_decisions(event_keys):
    review = load_strict_historical_126_review()
    if not review.empty:
        st.markdown("### STRICT REVIEW — ALL 126 ORIGINAL ABSTENTIONS")
        s1,s2,s3,s4 = st.columns(4)
        s1.metric("Strict evaluated", f"{len(review)}/126")
        s2.metric("New Strict approval", int(review["fda_prediction"].eq("APPROVED").sum()))
        s3.metric("New Strict CRL", int(review["fda_prediction"].eq("CRL").sum()))
        s4.metric("Still REVIEW", int(review["fda_prediction"].eq("REVIEW").sum()))
        st.caption("All 126 were source-screened and evaluated with FDA-V3.2. Source screening is not exhaustive dossier verification. Candidate source links and imported dates cannot pass gates. Missing evidence remains REVIEW; CRL calls are model inferences from verified failures. The original 20 qualifications are outside this run.")
        with st.expander("STRICT RESULTS AND MISSING EVIDENCE", expanded=True):
            selected_review = review[review["event_key"].isin(set(event_keys))]
            columns = ["ticker", "drug", "pdufa_date", "fda_prediction", "fda_hard_gate",
                       "fda_statistics_gate", "fda_cmc_gate", "fda_facility_gate", "cutoff_status",
                       "evidence_cutoff", "review_note", "fda_gate_reason", "missing_statistics_subchecks",
                       "missing_cmc_subchecks", "missing_facility_subchecks", "source_urls"]
            grouped_dataframe(selected_review[columns], use_container_width=True, hide_index=True, height=420)
            st.download_button("DOWNLOAD ALL 126 STRICT RESULTS (.CSV)", review.to_csv(index=False).encode("utf-8"),
                               file_name="strict_historical_126_review.csv", mime="text/csv", key="download_strict_126")
    st.markdown("### ASSESSED HISTORICAL DECISIONS")
    ledger = historical_assessed_decisions
    if ledger.empty:
        st.info("Recorded historical assessments are not available yet.")
        return
    selected = ledger[ledger["event_key"].isin(set(event_keys))].copy()
    subset = st.selectbox(
        "Decision set",
        ["Broad decisions — strict gate withheld", "All assessed decisions", "Strict qualified decisions"],
        key="historical_decision_set",
    )
    if subset == "Broad decisions — strict gate withheld":
        selected = selected[selected["assessment_basis"].eq("BROAD")]
    elif subset == "Strict qualified decisions":
        selected = selected[selected["assessment_basis"].eq("STRICT")]
    approved = int(selected["assessed_direction"].eq("APPROVED").sum())
    crl = int(selected["assessed_direction"].eq("CRL").sum())
    scored = selected[selected["actual_outcome"].isin(["APPROVED", "CRL"])]
    matches = int(scored["match_result"].eq("MATCH").sum())
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Recorded decisions", len(selected))
    c2.metric("PASS / Approval", approved)
    c3.metric("CRL", crl)
    c4.metric("Historical matches", f"{matches}/{len(scored)}")
    c5.metric("Historical match %", f"{100 * matches / len(scored):.2f}%" if len(scored) else "—")
    st.caption(
        "Each event has a recorded PASS or CRL suggestion. Strict REVIEW means the evidence gate withheld qualification; "
        "the broad suggestion remains visible. These are retrospective development results. "
        "The year, market-cap and search filters above also apply here."
    )
    display = pd.DataFrame(index=selected.index)
    display["Ticker"] = selected.apply(
        lambda r: stock_chart_url(r.get("ticker")), axis=1
    ) if not selected.empty else pd.Series(dtype="object")
    display["PDUFA Date"] = selected["pdufa_date"]
    display["SUGGESTION"] = selected["assessed_direction"].replace({"APPROVED": "PASS"})
    display["FDA Decision"] = selected["actual_outcome"]
    display["MATCH"] = selected["match_result"]
    display["Decision basis"] = selected["assessment_basis"]
    display["Strict status"] = selected["strict_status"].replace({"REVIEW_NO_CALL_ANALYZED": "REVIEW — ANALYZED"})
    display["Decision reason"] = selected["decision_reason"]
    display["Strict evidence gap"] = selected["strict_reason"]
    grouped_dataframe(
        display, use_container_width=True, hide_index=True,
        height=min(650, 120 + 34 * len(display)),
        column_config={"Ticker": st.column_config.LinkColumn("Ticker", display_text=r"ticker=([^&]+)")},
    )
    st.download_button(
        "DOWNLOAD ASSESSED DECISIONS (.CSV)",
        data=selected.to_csv(index=False).encode("utf-8"),
        file_name="historical_assessed_decisions.csv", mime="text/csv",
        key="download_historical_assessed_decisions",
    )


def prediction_v2_history_status(row):
    """Audit-safe status for historical validation rows."""
    count_ok = str(row.get("count_in_audited_accuracy", "")).upper() == "YES"
    needs_rescore = str(row.get("needs_rescore", "")).upper() == "YES"
    status = safe_text(row.get("audit_status"), "UNREVIEWED")
    if needs_rescore or not count_ok:
        return "REBUILD / RESCORE"
    if status == "CLEAN_MODEL_MISS":
        return "CLEAN MODEL MISS"
    if status in ["CLEAN_CORRECT", "VALID_PDUFA_DELAYED_ACTION"]:
        return "CLEAN / KEEP"
    return "REVIEW"


def prospective_gate_state(row):
    """Conservative FDA decision layer for live/future PDUFA rows."""
    persistent_call = safe_text(row.get("fda_prediction"), "").upper()
    persistent_model = safe_text(row.get("fda_model_version"), "")
    if persistent_model and persistent_call in ["APPROVED","CRL","REVIEW"]:
        return (
            persistent_call,
            safe_text(row.get("fda_confidence"), "INSUFFICIENT FDA EVIDENCE"),
            safe_text(row.get("fda_gate_reason"), "Persistent FDA review record")
        )

    reasons = []

    pdufa_status = safe_text(row.get("pdufa_confirmation"), "").lower()
    monitor = safe_text(row.get("monitor_eligibility"), "").upper()
    conflict = safe_text(row.get("conflict_flag"), "").upper()
    phase3 = safe_text(row.get("phase3_status"), "").lower()
    pdufa_url = safe_text(row.get("pdufa_evidence_url"), "")
    trial_url = safe_text(row.get("trial_evidence_url"), "")

    identity_ok = bool(pdufa_url) and (
        "verified" in pdufa_status or "confirmed" in pdufa_status or monitor == "PASS"
    )
    if not identity_ok:
        reasons.append("PDUFA identity/evidence not fully verified")

    evidence_ok = bool(trial_url) or ("phase 3" in phase3) or ("pivotal" in phase3) or ("complete" in phase3)
    if not evidence_ok:
        reasons.append("pivotal/Phase 3 evidence incomplete")

    if conflict not in ["", "NONE", "NO", "FALSE", "0", "PASS"]:
        reasons.append("unresolved evidence conflict")

    component_cols = ["science_score","regulatory_score","safety_score","cmc_score"]
    components = {}
    for col in component_cols:
        value = row.get(col)
        components[col] = None if pd.isna(value) else float(value)

    for col,label in [
        ("science_score","clinical"),
        ("regulatory_score","regulatory"),
        ("safety_score","safety"),
        ("cmc_score","CMC/manufacturing"),
    ]:
        if components[col] is None:
            reasons.append(f"{label} score missing")

    hard_fail = False
    if components["cmc_score"] is not None and components["cmc_score"] < 50:
        hard_fail = True
        reasons.append("CMC/manufacturing hard gate failed")
    if components["safety_score"] is not None and components["safety_score"] < 50:
        hard_fail = True
        reasons.append("safety hard gate failed")
    if components["regulatory_score"] is not None and components["regulatory_score"] < 50:
        hard_fail = True
        reasons.append("regulatory hard gate failed")

    p = row.get("approval_probability")
    p = None if pd.isna(p) else float(p)
    if p is not None and 0 <= p <= 1:
        p *= 100

    if hard_fail:
        call = "CRL RISK / REVIEW"
        confidence = "HIGH RISK"
    elif reasons:
        call = "REVIEW"
        confidence = "INSUFFICIENT EVIDENCE"
    elif p is None:
        call = "REVIEW"
        confidence = "NO APP %"
    elif p >= 95:
        call = "APPROVED"
        confidence = "PRECISION MODE"
    else:
        call = "REVIEW"
        confidence = "ABSTAIN FOR ACCURACY"

    return call, confidence, " | ".join(dict.fromkeys(reasons)) if reasons else "All V2 gates passed"


def public_direction_state(row):
    """PUBLIC-ONLY direction. Never uses I App %, internal model scores, audit labels, or internal direction."""
    explicit = safe_text(row.get("public_model_class"), "").upper()
    if explicit in ["APPROVED", "CRL"]:
        return explicit

    p = row.get("public_approval_probability")
    p = None if pd.isna(p) else float(p)
    if p is not None and 0 <= p <= 1:
        p *= 100

    # The public field itself must be produced only from decision-safe public evidence.
    # If it is missing or ambiguous, abstain.
    if p is None:
        return "REVIEW"
    if p >= 90:
        return "APPROVED"
    if p <= 10:
        return "CRL"
    return "REVIEW"

def internal_direction_state(row):
    """Full-intelligence direction using decision-safe internal research plus model/public evidence."""
    explicit_internal = safe_text(row.get("internal_direction_class"), "").upper()
    if explicit_internal in ["APPROVED", "CRL"]:
        return explicit_internal

    p_public_dir = public_direction_state(row)
    p = row.get("approval_probability", row.get("p_approval"))
    p = None if pd.isna(p) else float(p)
    if p is not None and 0 <= p <= 1:
        p *= 100

    # Strong decision-safe public evidence can override a misleading raw I App probability.
    if p_public_dir in ["APPROVED", "CRL"]:
        return p_public_dir

    # If public evidence is mixed, abstain rather than force a directional call.
    if p_public_dir == "REVIEW":
        return "REVIEW"

    if p is None:
        return "REVIEW"
    if p >= 95:
        return "APPROVED"
    if p <= 10:
        return "CRL"
    return "REVIEW"


def ip_consensus_value(row):
    """Transparent 50/50 consensus of I App and P App only."""
    i = row.get("approval_probability", row.get("p_approval"))
    p = row.get("public_approval_probability")
    if i is None or p is None or pd.isna(i) or pd.isna(p):
        return pd.NA
    i = float(i)
    p = float(p)
    if 0 <= i <= 1:
        i *= 100
    if 0 <= p <= 1:
        p *= 100
    return (i + p) / 2.0


def ip_consensus_direction(row):
    """Consensus direction: call only when I and P directions agree."""
    i_dir = internal_direction_state(row)
    p_dir = public_direction_state(row)
    if i_dir in ["APPROVED","CRL"] and i_dir == p_dir:
        return i_dir
    return "REVIEW"


def displayed_probability_value(row):
    """Primary P% shown in Streamlit. Use stored approval_probability when available;
    fall back to the all-source composite only when needed. Missing stays blank."""
    v = row.get("approval_probability", row.get("p_approval"))
    if v is not None and not pd.isna(v):
        x = float(v)
        if 0 <= x <= 1:
            x *= 100
        return x
    score = all_source_probability_value(row)
    if score is None or pd.isna(score):
        return pd.NA
    return float(score)


def displayed_probability_text(row, decimals=1):
    v = displayed_probability_value(row)
    if v is None or pd.isna(v):
        return ""
    return f"{float(v):.{decimals}f}%"


def all_source_probability_value(row):
    """Our consensus PoA: equal-weight internal and public-evidence FDA PoA."""
    vals = []
    for field in ["approval_probability", "public_approval_probability"]:
        v = row.get(field, row.get("p_approval") if field == "approval_probability" else pd.NA)
        if v is None or pd.isna(v):
            return pd.NA
        v = float(v)
        if 0 <= v <= 1:
            v *= 100
        vals.append(v)
    return sum(vals) / 2.0


def all_source_direction_state(row):
    """Direction from the all-source probability, gated by I/P disagreement."""
    score = all_source_probability_value(row)
    if score is None or pd.isna(score):
        return "REVIEW"
    if internal_direction_state(row) != public_direction_state(row):
        return "REVIEW"
    return "APPROVED" if float(score) >= 50 else "CRL"


def normalize_fda_direction(value):
    """Map a final FDA outcome into the same APPROVED/CRL direction vocabulary."""
    text_value = safe_text(value, "").upper()
    if not text_value or text_value in ["PENDING", "NA", "N/A", "UNKNOWN", "NOT AVAILABLE"]:
        return None
    if "APPROV" in text_value:
        return "APPROVED"
    if "CRL" in text_value or "COMPLETE RESPONSE" in text_value or "REJECT" in text_value or "DECLIN" in text_value:
        return "CRL"
    return None


def resolved_fda_direction(row):
    """Return a final FDA direction only when the decision is actually resolved."""
    historical = normalize_fda_direction(row.get("actual_outcome"))
    if historical is not None:
        return historical

    live = normalize_fda_direction(row.get("outcome"))
    if live is None:
        return None

    decision_date = pd.to_datetime(row.get("decision_date"), errors="coerce")
    if pd.notna(decision_date) and pd.Timestamp(decision_date).normalize() <= today:
        return live

    # A passed PDUFA target is not itself proof of an FDA decision.
    # Live cases remain open until a verified actual decision date is stored.
    return None


def fda_decision_display(row):
    """Display the resolved FDA outcome; future/unresolved events remain PENDING."""
    actual = resolved_fda_direction(row)
    return actual if actual is not None else "PENDING"


def suggestion_word_display(row):
    """Human-readable suggestion derived directly from SUGGESTION %."""
    score = displayed_probability_value(row)
    if score is None or pd.isna(score):
        return ""
    return "PASS" if float(score) >= 50 else "CRL"


def predicted_fda_direction(row):
    """Best decision-safe direction available before FDA acts.

    Priority:
    1) all-source call when all source inputs exist and agree;
    2) I+P consensus when both independent direction layers agree;
    3) prospective V2 call when its hard gates produce an actionable call.
    Conflicts/weak evidence remain REVIEW rather than being forced.
    """
    all_dir = all_source_direction_state(row)
    if all_dir in ["APPROVED", "CRL"]:
        return all_dir

    consensus_dir = ip_consensus_direction(row)
    if consensus_dir in ["APPROVED", "CRL"]:
        return consensus_dir

    # Historical validation rows carry a frozen pre-decision model_class.
    # Use it before the prospective V2 fallback so historical F/Match reflect
    # the prediction that was actually frozen for that case.
    frozen_model = safe_text(row.get("model_class"), "").upper()
    if frozen_model in ["APPROVED", "CRL"]:
        return frozen_model

    try:
        v2_call = prospective_gate_state(row)[0]
    except Exception:
        v2_call = "REVIEW"
    if v2_call in ["APPROVED", "CRL"]:
        return v2_call

    return "REVIEW"


def direction_fda_display(row):
    """Lifecycle display: prediction before FDA action; 100%/0% match after FDA action."""
    predicted = predicted_fda_direction(row)
    actual = resolved_fda_direction(row)

    if actual is None:
        return predicted

    if predicted not in ["APPROVED", "CRL"]:
        return f"Not scored · FDA {actual}"

    if predicted == actual:
        return f"100% MATCH · {actual}"

    return f"0% MATCH · Pred {predicted} / FDA {actual}"


def match_percent_display(row):
    """Populate only when both approval probability and a resolved FDA decision exist."""
    approval = displayed_probability_value(row)
    actual = resolved_fda_direction(row)
    if approval is None or pd.isna(approval) or actual is None:
        return ""
    predicted = predicted_fda_direction(row)
    if predicted not in ["APPROVED", "CRL"]:
        return ""
    return "100%" if predicted == actual else "0%"


def make_event_key(row):
    source_key = safe_text(row.get("event_key"), "")
    if source_key:
        return source_key
    pdate = "nodate" if pd.isna(row.get("pdufa_date")) else pd.Timestamp(row.get("pdufa_date")).strftime("%Y-%m-%d")
    return " | ".join([
        safe_text(row.get("ticker"), ""),
        safe_text(row.get("drug"), ""),
        safe_text(row.get("indication"), ""),
        pdate,
    ])

APP_BASE_URL = "https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/"

def stock_chart_url(ticker):
    """Open the dedicated Streamlit stock chart page for any ticker."""
    symbol = safe_text(ticker, "").upper().strip()
    return APP_BASE_URL + "Stock_Chart?" + urllib.parse.urlencode({"ticker": symbol})

def event_detail_url(row, source="live", return_page="MASTER TABLE"):
    event_key = safe_text(row.get("event_key"), "") if source == "history" else make_event_key(row)
    return APP_BASE_URL + "?" + urllib.parse.urlencode({
        "page": "detail",
        "event": event_key,
        "ticker": safe_text(row.get("ticker"), ""),
        "source": source,
        "return": return_page,
    })

df["event_key"] = df.apply(make_event_key, axis=1)

def go_page(page_name):
    st.session_state._pending_nav = page_name
    st.session_state.detail_open = False
    for _qp in ["event", "ticker", "page", "source", "return"]:
        if _qp in st.query_params:
            del st.query_params[_qp]

def go_individual(ticker=None, event_key=None, source="live", return_page=None):
    if ticker is not None:
        st.session_state.selected_ticker = str(ticker)
    if event_key is not None:
        st.session_state.selected_event_key = str(event_key)
    st.session_state.selected_detail_source = source
    st.session_state.detail_return_page = return_page or st.session_state.get("nav", "MASTER TABLE")
    st.session_state.detail_open = True
    if len(st.query_params):
        st.query_params.clear()

SPECIAL_PROVISION_COLUMNS = [
    ("Orphan Drug", ("orphan_drug", "orphan")),
    ("No Available Therapy", ("no_available_therapy", "no_therapy")),
    ("Serious Condition", ("serious_condition",)),
    ("Life-Threatening", ("life_threatening", "life_threatening_condition")),
    ("Fast Track", ("fast_track", "fast_track_designation")),
    ("Breakthrough", ("breakthrough_therapy", "breakthrough", "btd")),
    ("Priority Review", ("priority_review",)),
    ("Accelerated Approval", ("accelerated_approval",)),
    ("RMAT", ("rmat", "rmat_designation")),
    ("QIDP", ("qidp",)),
    ("Rare Pediatric", ("rare_pediatric_disease", "rare_pediatric")),
    ("PRV", ("priority_review_voucher", "prv")),
    ("Rolling Review", ("rolling_review",)),
    ("RTOR", ("rtor", "real_time_oncology_review")),
    ("Project Orbis", ("project_orbis",)),
    ("SPA", ("spa", "special_protocol_assessment")),
]
SPECIAL_PROVISION_LABELS = [label for label, _ in SPECIAL_PROVISION_COLUMNS]


def _provision_status(value):
    if value is None or (not isinstance(value, (list, tuple, dict, set)) and pd.isna(value)):
        return ""
    if isinstance(value, bool):
        return "✓" if value else ""
    text = str(value).strip()
    if not text:
        return ""
    low = text.lower()
    if low in {"true", "yes", "y", "1", "granted", "designated", "verified", "confirmed", "applicable", "active"}:
        return "✓"
    if low in {
        "false", "no", "n", "0", "not granted", "not designated", "not applicable",
        "none", "unknown", "unverified", "not verified", "pending", "review"
    }:
        return ""
    return ""


def _designation_from_evidence(row, label):
    """Use only explicit positive statements already saved for this exact event."""
    evidence_fields = [
        "regulatory_summary", "evidence_summary", "science_summary",
        "public_evidence_note", "internal_direction_note"
    ]
    text = " ".join(
        safe_text(row.get(field), "")
        for field in evidence_fields
        if field in row.index
    ).lower()
    if not text:
        return ""

    negative_phrases = {
        "Priority Review": [
            "priority review was not granted", "priority review not granted",
            "did not grant priority review", "standard review"
        ],
        "Fast Track": [
            "fast track was not granted", "fast track not granted",
            "fast track for low-light indication must not transfer",
            "fast track must not transfer"
        ],
        "Breakthrough": [
            "breakthrough was not granted", "breakthrough not granted",
            "breakthrough designation not granted"
        ],
        "Orphan Drug": [
            "orphan was not granted", "orphan not granted",
            "orphan designation not granted"
        ],
        "Accelerated Approval": [
            "accelerated approval is a pathway, not designation",
            "accelerated approval pathway separate from designation",
            "eligibility issue noted"
        ],
    }
    if any(phrase in text for phrase in negative_phrases.get(label, [])):
        return ""

    positive_patterns = {
        "Orphan Drug": [
            r"orphan drug designation", r"orphan designation",
            r"orphan designations", r"granted orphan", r"grants orphan"
        ],
        "No Available Therapy": [
            r"no available therap", r"no approved therap", r"no fda-approved treatment"
        ],
        "Serious Condition": [r"serious condition"],
        "Life-Threatening": [r"life-threatening condition", r"life threatening condition"],
        "Fast Track": [
            r"fast track designation", r"granted fast track", r"grants fast track",
            r"\bfast track\b"
        ],
        "Breakthrough": [
            r"breakthrough therapy designation", r"breakthrough designation",
            r"breakthrough and orphan designations", r"granted breakthrough", r"grants breakthrough"
        ],
        "Priority Review": [
            r"priority review goal", r"grants priority review", r"granted priority review",
            r"confirms .*priority review", r"supports .*priority review",
            r"\bpriority review\b"
        ],
        "Accelerated Approval": [
            r"granted accelerated approval", r"under accelerated approval",
            r"accelerated approval pathway accepted", r"accelerated approval application"
        ],
        "RMAT": [
            r"rmat designation", r"regenerative medicine advanced therapy designation",
            r"granted rmat", r"grants rmat"
        ],
        "QIDP": [
            r"qidp designation", r"qualified infectious disease product designation",
            r"granted qidp", r"grants qidp"
        ],
        "Rare Pediatric": [
            r"rare pediatric disease designation", r"granted rare pediatric", r"grants rare pediatric"
        ],
        "PRV": [r"priority review voucher", r"\bprv\b"],
        "Rolling Review": [r"rolling review"],
        "RTOR": [r"real-time oncology review", r"real time oncology review", r"\brtor\b"],
        "Project Orbis": [r"project orbis"],
        "SPA": [r"special protocol assessment", r"\bspa agreement\b", r"fda .* spa"],
    }
    return "✓" if any(re.search(pattern, text) for pattern in positive_patterns.get(label, [])) else ""


def add_special_provision_columns(frame):
    """Add special-provision columns; show ✓ only when explicit saved evidence supports it."""
    out = frame.copy()
    for label, aliases in SPECIAL_PROVISION_COLUMNS:
        source = next((name for name in aliases if name in out.columns), None)
        explicit = out[source].apply(_provision_status) if source else pd.Series("", index=out.index, dtype="object")
        fallback = out.apply(lambda row: _designation_from_evidence(row, label), axis=1)
        out[label] = explicit.where(explicit == "✓", fallback)
    return out


def _second_financing_file_version():
    try:
        p = Path("data/second_financing_status.csv")
        stt = p.stat()
        return f"{stt.st_mtime_ns}:{stt.st_size}"
    except Exception:
        return "missing"


@st.cache_data(ttl=15)
def _load_second_financing_backfill(version):
    """Load auditable second-financing milestones keyed to exact live PDUFA events."""
    try:
        sf = pd.read_csv("data/second_financing_status.csv", keep_default_na=False)
    except Exception:
        return pd.DataFrame()
    if "event_key" not in sf.columns:
        return pd.DataFrame()
    sf["event_key"] = sf["event_key"].astype(str)
    return sf.drop_duplicates("event_key", keep="last").set_index("event_key", drop=False)


def load_second_financing_backfill():
    # File version participates in the cache key, so a data-only deploy cannot
    # leave the old 3-row verified state cached after the CSV changes.
    return _load_second_financing_backfill(_second_financing_file_version())


SECOND_FINANCING_COLUMNS = ["Announced", "Running", "Closed"]
SECOND_FINANCING_HEADER_LABELS = {
    "Announced": "2F Announced",
    "Running": "2F Running",
    "Closed": "2F Closed",
}


def _second_financing_flags(row):
    """Return explicit second-financing stage flags without inferring from generic financing."""
    explicit_map = {
        "Announced": ["second_financing_announced", "second_financing_announcement"],
        "Running": ["second_financing_running", "second_financing_in_progress"],
        "Closed": ["second_financing_closed", "second_financing_close_verified"],
    }
    result = {name: "" for name in SECOND_FINANCING_COLUMNS}

    for label, aliases in explicit_map.items():
        for alias in aliases:
            if alias in row.index:
                if _provision_status(row.get(alias)) == "✓":
                    result[label] = "✓"
                    break

    explicit_status = safe_text(row.get("second_financing_status"), "").strip().lower()
    if explicit_status:
        if any(k in explicit_status for k in ["closed", "complete", "completed"]):
            result["Closed"] = "✓"
        elif any(k in explicit_status for k in ["running", "in progress", "pending", "open"]):
            result["Running"] = "✓"
        elif any(k in explicit_status for k in ["announced", "priced", "launched"]):
            result["Announced"] = "✓"

    evidence = " ".join(
        safe_text(row.get(field), "")
        for field in [
            "financing_summary", "evidence_summary", "regulatory_summary",
            "trading_summary", "financing_status"
        ]
        if field in row.index
    ).lower()

    if not evidence:
        return result

    negative = [
        "does not establish second financing sequence",
        "second financing remains unverified",
        "second financing sequence remains unverified",
        "second-close sequence not verified",
        "second close sequence not verified",
        "no post-phase-3 sequence proven",
        "does not satisfy any post-readout second-close rule",
    ]
    if any(phrase in evidence for phrase in negative):
        return result

    if not re.search(r"\b(second|2nd)[ -]?(financing|finance|close|offering)\b", evidence):
        return result

    if re.search(r"\b(second|2nd)[ -]?(financing|finance|offering)\b.{0,80}\b(announced|priced|launched)\b", evidence):
        result["Announced"] = "✓"
    if re.search(r"\b(second|2nd)[ -]?(financing|finance|offering)\b.{0,100}\b(running|in progress|pending|open|expected to close)\b", evidence):
        result["Running"] = "✓"
    if re.search(r"\b(second|2nd)[ -]?(financing|finance|close|offering)\b.{0,100}\b(closed|completed|complete|verified)\b", evidence):
        result["Closed"] = "✓"

    return result


def add_second_financing_columns(frame):
    """Add 2nd-financing checks from exact event-key verification first, then saved row evidence."""
    out = frame.copy()
    if out.empty:
        for col in SECOND_FINANCING_COLUMNS:
            out[col] = ""
        return out

    sf = load_second_financing_backfill()
    flags = []

    for _, row in out.iterrows():
        result = _second_financing_flags(row)
        event_key = safe_text(row.get("event_key"), "")

        if event_key and not sf.empty and event_key in sf.index:
            saved = sf.loc[event_key]
            if isinstance(saved, pd.DataFrame):
                saved = saved.iloc[-1]

            if _provision_status(saved.get("second_financing_announced")) == "✓":
                result["Announced"] = "✓"
            if _provision_status(saved.get("second_financing_running")) == "✓":
                result["Running"] = "✓"
            if _provision_status(saved.get("second_financing_closed")) == "✓":
                result["Closed"] = "✓"

            status = safe_text(saved.get("second_financing_status"), "").upper()
            audit = safe_text(saved.get("second_financing_audit_status"), "").upper()
            if status == "CLOSED" and audit == "VERIFIED_SECOND_POST_PHASE3_FINANCING":
                # A verified completed second financing necessarily passed through
                # announced/running/closed stages, so all three milestones display.
                result["Announced"] = "✓"
                result["Running"] = "✓"
                result["Closed"] = "✓"

        flags.append(result)

    for col in SECOND_FINANCING_COLUMNS:
        out[col] = [d.get(col, "") for d in flags]
    return out


APPLICATION_COLUMNS = ["N", "B"]


def _application_flags(row):
    """Return NDA/BLA flags only when the exact application type is explicit."""
    result = {"N": "", "B": ""}
    fields = [
        safe_text(row.get("application_type"), ""),
        safe_text(row.get("regulatory_summary"), ""),
        safe_text(row.get("evidence_summary"), ""),
        safe_text(row.get("public_evidence_note"), ""),
        safe_text(row.get("internal_direction_note"), ""),
    ]
    text = " ".join(fields).lower()

    # Explicit application type takes priority.
    app_type = safe_text(row.get("application_type"), "").strip().lower()
    if re.search(r"\bs?nda\b|new drug application", app_type):
        result["N"] = "✓"
    if re.search(r"\bs?bla\b|biologics license application|biologic license application", app_type):
        result["B"] = "✓"

    # Fallback to exact saved evidence when application_type is generic/blank.
    if not result["N"] and re.search(r"\b(snda|nda)\b|new drug application", text):
        result["N"] = "✓"
    if not result["B"] and re.search(r"\b(sbla|bla)\b|biologics license application|biologic license application", text):
        result["B"] = "✓"

    return result


def add_application_columns(frame):
    out = frame.copy()
    if out.empty:
        for col in APPLICATION_COLUMNS:
            out[col] = ""
        return out
    flags = out.apply(_application_flags, axis=1)
    for col in APPLICATION_COLUMNS:
        out[col] = flags.apply(lambda d: d.get(col, ""))
    return out


def special_provision_column_config():
    return {
        label: st.column_config.TextColumn(
            label,
            help=f"{label}: ✓ means verified for this exact drug/indication/application; blank means not verified/applicable in the loaded evidence.",
            width="small",
        )
        for label in SPECIAL_PROVISION_LABELS
    }


def _merged_table_sort_series(frame, col):
    """Build a display-aware sort key so visible values sort numerically when appropriate."""
    raw = frame[col]
    text_values = raw.fillna("").astype(str).str.strip()

    if col in SPECIAL_PROVISION_LABELS or col in SECOND_FINANCING_COLUMNS or col in APPLICATION_COLUMNS:
        return text_values.eq("✓").astype(int)

    if col == "Ticker":
        def ticker_label(value):
            value = str(value)
            if value.startswith("http"):
                parsed = urllib.parse.urlparse(value)
                return urllib.parse.parse_qs(parsed.query).get("ticker", [""])[0].upper()
            return value.upper()
        return text_values.apply(ticker_label)

    lower_col = str(col).lower()
    if "date" in lower_col or col in {"Canonical PDUFA", "PDUFA"}:
        parsed_dates = pd.to_datetime(text_values.replace({"":"NaT", "Not available":"NaT", "NA":"NaT"}), errors="coerce")
        if parsed_dates.notna().any():
            return parsed_dates

    if col == "F":
        return text_values.str.upper().map({"CRL":0, "REVIEW":1, "APPROVED":2}).fillna(-1)

    if col == "P":
        extracted = text_values.str.extract(r"(?i)p\s*(?:=|<|≤|>)?\s*([0-9]*\.?[0-9]+)", expand=False)
        return pd.to_numeric(extracted, errors="coerce")

    if col == "C" or "%" in str(col):
        extracted = text_values.str.extract(r"(-?[0-9]+(?:\.[0-9]+)?)", expand=False)
        return pd.to_numeric(extracted, errors="coerce")

    if "market cap" in lower_col:
        def cap_number(value):
            value = str(value).strip().upper().replace("$", "").replace(",", "")
            if value in {"", "NA", "NOT AVAILABLE"}:
                return float("nan")
            mult = 1.0
            if value.endswith("B"):
                mult = 1_000_000_000.0
                value = value[:-1]
            elif value.endswith("M"):
                mult = 1_000_000.0
                value = value[:-1]
            elif value.endswith("K"):
                mult = 1_000.0
                value = value[:-1]
            try:
                return float(value) * mult
            except Exception:
                return float("nan")
        return text_values.apply(cap_number)

    numeric = pd.to_numeric(text_values.str.replace(",", "", regex=False), errors="coerce")
    if numeric.notna().sum() >= max(1, int(len(frame) * 0.5)):
        return numeric

    return text_values.str.lower()


COLUMN_HELP = {
    "Ticker": "Public-company ticker. Click the ticker to open the event detail page.",
    "PDUFA Date": "FDA target action date for this application/review cycle.",
    "DECISION DATE": "Actual FDA decision/action posting date. Once populated from a verified FDA decision, the PDUFA matter is closed/decided.",
    "PDUFA": "FDA target action date for this application/review cycle.",
    "SUGGESTION %": "ChatGPT/model pre-decision probability of FDA approval for this event.",
    "SUGGESTION": "Suggestion in words from SUGGESTION %: PASS at 50% or higher; CRL below 50%.",
    "FDA MODEL %": "FDA-only regulatory approval probability. Trading variables are excluded.",
    "FDA CALL": "FDA-only directional call: APPROVED, CRL, or REVIEW.",
    "FDA GATE": "FDA-like hard-gate status: PASS, FAIL, or REVIEW/unknown.",
    "FDA Decision": "Final FDA outcome when resolved. Future or unresolved events show PENDING.",
    "MATCH %": "100% when the model direction matched the resolved FDA decision, 0% when it missed; blank while pending.",
    "P%": "All-sources model probability of FDA approval for this event.",
    "P": "Reported pivotal/Phase 3 p-value evidence saved for the event.",
    "F": "Model-predicted FDA direction: APPROVED, CRL, or REVIEW.",
    "Match %": "Historical direction match: 100% when the model direction matched the final FDA outcome, 0% when it missed; blank before a final outcome.",
    "C": "Combined display of the approval probability and model FDA direction.",
    "Probability of Approval % — Public": "Approval probability using public-source evidence only.",
    "Probability of Approval % — All Sources": "Approval probability using all permitted saved evidence sources.",
    "Public P%": "Approval probability using public-source evidence only.",
    "I Direction": "Internal-evidence direction call.",
    "P Direction": "Public-evidence direction call.",
    "All-Source Direction": "Direction call using all permitted evidence sources.",
    "Direction / FDA Match": "Predicted FDA direction before decision; after decision, shows whether the direction matched the FDA result.",
    "Company": "Issuer/company associated with the PDUFA event.",
    "Drug": "Drug, biologic, or product under FDA review.",
    "Indication": "Disease/condition or use being reviewed by FDA.",
    "Days Left": "Calendar days from today to the PDUFA target date.",
    "Market Cap": "Saved market capitalization for the company/event.",
    "Historical Market Cap": "Historical market capitalization used for this validation event.",
    "Market Cap Bucket": "Market-cap range assigned to this event.",
    "Cap Bucket": "Market-cap range assigned to this event.",
    "Trade Score": "Saved trading-setup score; separate from FDA approval probability.",
    "Outcome": "Current/final FDA outcome when known.",
    "Actual FDA Outcome": "Final FDA decision used to score the historical prediction.",
    "Model Prediction": "Frozen model direction predicted before the FDA decision.",
    "Correct / Wrong": "Whether Model Prediction matches Actual FDA Outcome.",
    "Time": "Current PDUFA timing/window status.",
    "Signal": "Saved trading/setup signal.",
    "Confidence": "Saved model confidence label.",
    "Application": "FDA application type when known.",
    "N": "NDA/sNDA indicator. A check means the exact application is verified as an NDA-family filing.",
    "B": "BLA/sBLA indicator. A check means the exact application is verified as a BLA-family filing.",
    "Announced": "Second post-Phase-3 financing has been verified as announced.",
    "Running": "Second post-Phase-3 financing has been verified as in progress.",
    "Closed": "Second post-Phase-3 financing has been verified as closed.",
    "Financing": "Saved financing status for the company/event.",
    "Phase": "Current trading/PDUFA workflow phase.",
    "Short %": "Saved short interest as a percentage of float.",
    "IV (30d)": "Saved 30-day implied-volatility measure.",
    "Record Source": "Whether this row comes from the live saved feed or historical model set.",
    "V2 Status": "Prediction Engine V2 validation/gating status.",
    "Audit Status": "Historical audit status for this event.",
    "Failure Reason": "Reason an audited row failed, was blocked, or required repair.",
    "Canonical PDUFA": "Verified canonical PDUFA date used after audit/reconciliation.",
    "Audit Action": "Audit repair or disposition applied to the row.",
    "Needs Rescore": "Whether the event still requires a decision-safe model rescore.",
    "Count in Adjusted Accuracy": "Whether this row is eligible for the adjusted historical accuracy calculation.",
    "Audit Source": "Source used to verify the historical audit result.",
    "Validation Period": "Validation cohort/period assigned to the event.",
    "Validation Role": "Whether the row is tuning, retrospective, holdout, or other validation role.",
    "V2 Call": "Prospective V2 direction call after the V2 evidence gates.",
    "V2 Confidence": "Confidence assigned to the V2 call.",
    "V2 Gate Reason": "Reason the V2 gate allowed, blocked, or abstained on the call.",
    "PDUFA Verification": "Status of the saved evidence confirming the exact PDUFA event/date.",
    "Phase 3": "Status of the pivotal/Phase 3 evidence for this event.",
    "Eligibility": "Whether the event passes the saved monitoring eligibility rules.",
    "Conflict": "Saved evidence-conflict flag for the event."
}

def _column_help_text(col):
    if col in COLUMN_HELP:
        return COLUMN_HELP[col]
    if col in SPECIAL_PROVISION_LABELS:
        return f"{col}: FDA special regulatory provision/designation. A check means verified for this exact drug/indication/application."
    return f"{col}: field shown for this PDUFA event."

def _sort_header_button(col, col_index):
    """Render separate sort and help controls for a merged-table header."""
    label = html.escape(str(col))
    help_text = html.escape(_column_help_text(col), quote=True)
    sort_title = html.escape(f"Sort {col}", quote=True)
    return (
        f'<span class="header-controls">'
        f'<button type="button" class="sort-head" data-col-index="{int(col_index)}" '
        f'title="{sort_title}">'
        f'<span class="sort-label">{label}</span>'
        f'<span class="sort-icon" aria-hidden="true">⇅</span>'
        f'</button>'
        f'<span class="help-icon" role="img" tabindex="0" '
        f'title="{help_text}" aria-label="{help_text}">?</span>'
        f'</span>'
    )


def _merged_sort_payload(frame, col):
    """Return browser-ready sort type and values using the same value-aware rules."""
    series = _merged_table_sort_series(frame, col)

    if pd.api.types.is_datetime64_any_dtype(series):
        values = []
        for v in series:
            if pd.isna(v):
                values.append("")
            else:
                values.append(str(pd.Timestamp(v).value))
        return "number", values

    if pd.api.types.is_numeric_dtype(series):
        values = []
        for v in series:
            if pd.isna(v):
                values.append("")
            else:
                try:
                    values.append(str(float(v)))
                except Exception:
                    values.append("")
        return "number", values

    return "text", [
        "" if pd.isna(v) else str(v).strip().lower()
        for v in series
    ]


def render_merged_table(frame, heading, height_px=690):
    """Group prediction fields while preserving each pane's sortable headers."""
    if frame is None or frame.empty:
        return
    frame = staged_table(frame)
    st.markdown(f"### {heading}")
    # The merged HTML table renders the STAGE checkbox filter inside its own
    # column header; do not place a separate Streamlit filter above it.
    render_column_tabs(frame, "merged_" + heading,
                       lambda fields, token: _render_merged_table_panel(frame[fields], heading, height_px))


def _render_merged_table_panel(frame, heading, height_px=690):
    """Render one merged table with immediate client-side sortable headers."""
    if frame is None or frame.empty:
        return


    rendered_frame = frame.copy()
    cols = list(rendered_frame.columns)
    stage_labels = (sorted(rendered_frame["STAGE"].fillna("STAGE UNKNOWN — REVIEW").astype(str).unique())
                    if "STAGE" in rendered_frame else [])
    stage_filter_button = (
        '<button type="button" class="stage-filter-head" '
        'title="Choose one or more STAGE values" aria-label="Filter STAGE">▾</button>'
    )
    finance_filter_button = (
        '<button type="button" class="finance-filter-head" '
        'title="Choose financing states" aria-label="Filter FINANCING">▾</button>'
    )
    financing_labels = ("ANNOUNCED", "STARTED", "RUNNING", "FINISHED", "REVIEW / UNVERIFIED")
    finance_menu_html = (
        '<div class="finance-filter-menu" hidden><strong>FINANCING · select multiple</strong>'
        '<div class="stage-menu-actions"><button type="button" data-fin-all>Select all</button>'
        '<button type="button" data-fin-none>Clear all</button></div>'
        '<div class="stage-checkbox-list">' +
        "".join('<label><input type="checkbox" class="finance-choice" checked value="' +
                html.escape(label, quote=True) + '"> ' + html.escape(label.title()) + '</label>'
                for label in financing_labels) +
        '</div><label class="stage-order-label">Sort financing rows: '
        '<select class="finance-sort-order"><option value="keep">Keep current order</option>'
        '<option value="forward">Announced → Finished</option>'
        '<option value="reverse">Finished → Announced</option>'
        '</select></label><div class="finance-count"></div></div>'
    ) if "FINANCING" in cols else ""
    stage_menu_html = ('<div class="stage-filter-menu" hidden>'
        '<strong>STAGE · select multiple</strong><div class="stage-menu-actions">'
        '<button type="button" data-stage-all>Select all</button>'
        '<button type="button" data-stage-none>Clear all</button></div>'
        '<div class="stage-checkbox-list">' +
        "".join('<label><input type="checkbox" class="stage-choice" checked value="' +
                html.escape(label, quote=True) + '"> ' + html.escape(label) + '</label>'
                for label in stage_labels) +
        '</div><label class="stage-order-label">Sort STAGE rows: '
        '<select class="stage-sort-order">'
        '<option value="workflow-up">Phase 2 → FDA</option>'
        '<option value="workflow-down">FDA → Phase 2</option>'
        '<option value="alpha-up">STAGE A → Z</option>'
        '<option value="alpha-down">STAGE Z → A</option>'
        '<option value="pdufa-up">PDUFA days: closest first</option>'
        '<option value="pdufa-down">PDUFA days: latest first</option>'
        '</select></label><div class="stage-count"></div></div>') if stage_labels else ""

    sort_meta = {}
    for col_index, col in enumerate(cols):
        kind, values = _merged_sort_payload(rendered_frame, col)
        sort_meta[col] = {"kind": kind, "values": values, "index": col_index}

    has_second_financing_group = all(col in cols for col in SECOND_FINANCING_COLUMNS)
    has_application_group = all(col in cols for col in APPLICATION_COLUMNS)
    has_grouped_headers = has_second_financing_group or has_application_group
    header_cells = []
    header_top = []
    header_bottom = []

    if has_grouped_headers:
        financing_started = False
        application_started = False
        for col_index, col in enumerate(cols):
            sort_button = _sort_header_button(col, col_index)
            if col == "STAGE":
                sort_button += stage_filter_button
            if col == "FINANCING":
                sort_button += finance_filter_button
            if col in SECOND_FINANCING_COLUMNS:
                if not financing_started:
                    header_top.append('<th class="group-head" colspan="3">2nd Financing</th>')
                    financing_started = True
                visible_button = _sort_header_button(
                    SECOND_FINANCING_HEADER_LABELS.get(col, col), col_index
                ).replace(
                    f'data-col-index="{int(col_index)}"',
                    f'data-col-index="{int(col_index)}" data-source-col="{html.escape(str(col), quote=True)}"'
                )
                header_bottom.append(f'<th class="group-subhead financing-subhead">{visible_button}</th>')
                continue

            if col in APPLICATION_COLUMNS:
                if not application_started:
                    header_top.append('<th class="group-head" colspan="2">Application</th>')
                    application_started = True
                header_bottom.append(f'<th class="application-subhead">{sort_button}</th>')
                continue

            if col in SPECIAL_PROVISION_LABELS:
                header_top.append(f'<th class="angle-head" rowspan="2"><span>{sort_button}</span></th>')
            else:
                extra = ' ticker-head' if col == "Ticker" else ''
                if col in {"P%", "P"}:
                    extra += ' compact-p'
                header_top.append(f'<th class="normal-head{extra}" rowspan="2">{sort_button}</th>')
    else:
        for col_index, col in enumerate(cols):
            sort_button = _sort_header_button(col, col_index)
            if col == "STAGE":
                sort_button += stage_filter_button
            if col == "FINANCING":
                sort_button += finance_filter_button
            if col in SPECIAL_PROVISION_LABELS:
                header_cells.append(f'<th class="angle-head"><span>{sort_button}</span></th>')
            else:
                extra = ' ticker-head' if col == "Ticker" else ''
                if col in {"P%", "P"}:
                    extra += ' compact-p'
                header_cells.append(f'<th class="normal-head{extra}">{sort_button}</th>')

    rows = []
    for row_pos, (_, row) in enumerate(rendered_frame.iterrows()):
        cells = []
        for col in cols:
            raw = row.get(col, "")
            val = "" if pd.isna(raw) else str(raw)
            cls = ""
            if col in SPECIAL_PROVISION_LABELS:
                cls = " provision-yes" if val == "✓" else " provision-unknown"

            meta = sort_meta[col]
            sort_value = meta["values"][row_pos]
            sort_attrs = (
                f' title="{html.escape(val, quote=True)}" data-sort="{html.escape(str(sort_value), quote=True)}"'
                f' data-sort-type="{meta["kind"]}"'
            )

            if col == "Ticker" and val.startswith("http"):
                parsed = urllib.parse.urlparse(val)
                ticker_label = urllib.parse.parse_qs(parsed.query).get("ticker", ["Open"])[0]
                shown = html.escape(ticker_label)
                chart_url = stock_chart_url(ticker_label)
                link_target = "_top" if heading == "PREDICTION ENGINE TABLE" else "_blank"
                rendered = f'<a href="{html.escape(chart_url, quote=True)}" target="{link_target}" rel="noopener">{shown}</a>'
                cells.append(f'<td class="ticker-cell{cls}"{sort_attrs}>{rendered}</td>')
            elif col == "Audit Source" and val.startswith("http"):
                rendered = f'<a href="{html.escape(val, quote=True)}" target="_blank">Source</a>'
                cells.append(f'<td class="{cls.strip()}"{sort_attrs}>{rendered}</td>')
            else:
                extra_cls = " compact-p" if col in {"P%", "P"} else ""
                if col in SECOND_FINANCING_COLUMNS:
                    extra_cls += " second-fin-cell"
                    if val == "✓":
                        extra_cls += " second-fin-verified"
                if col in APPLICATION_COLUMNS:
                    extra_cls += " application-cell"
                cells.append(
                    f'<td class="{(cls + extra_cls).strip()}"{sort_attrs}>'
                    f'{html.escape(val)}</td>'
                )
        stage_value = row.get("STAGE", "STAGE UNKNOWN — REVIEW")
        stage_for_row = html.escape("STAGE UNKNOWN — REVIEW" if pd.isna(stage_value)
                                    else str(stage_value), quote=True)
        fin_value = row.get("FINANCING", "REVIEW / UNVERIFIED")
        fin_for_row = html.escape("REVIEW / UNVERIFIED" if pd.isna(fin_value)
                                  else str(fin_value), quote=True)
        rows.append(f'<tr data-original-index="{row_pos}" data-stage="{stage_for_row}" '
                    f'data-financing="{fin_for_row}">' + "".join(cells) + "</tr>")

    if has_grouped_headers:
        thead_html = (
            '<thead><tr>' + "".join(header_top) + '</tr>'
            '<tr>' + "".join(header_bottom) + '</tr></thead>'
        )
    else:
        thead_html = '<thead><tr>' + "".join(header_cells) + '</tr></thead>'

    local_css = """
    <style>
    html,body{margin:0;padding:0;background:#fff;font-family:Arial,Helvetica,sans-serif;color:#111}
    .merged-table-wrap{overflow:auto;background:#fff;border:2px solid #000;border-radius:12px;max-height:%dpx}
    .merged-pdufa-table{border-collapse:separate;border-spacing:0;background:#fff;color:#111;width:100%%;table-layout:fixed;font-size:13px}
    .merged-pdufa-table th,.merged-pdufa-table td{border-right:1px solid #777;border-bottom:1px solid #777;padding:6px 8px;text-align:center;color:#111;background:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .merged-pdufa-table th.normal-head{white-space:normal;overflow-wrap:anywhere}
    .merged-pdufa-table td.ticker-cell,.merged-pdufa-table th.ticker-head{width:88px}
    .merged-pdufa-table th{position:sticky;top:0;z-index:4;background:#f4f4f4}
    .merged-pdufa-table th.normal-head{height:158px;vertical-align:bottom;font-weight:700}
    .merged-pdufa-table th.angle-head{position:sticky;top:0;min-width:38px;width:38px;height:158px;vertical-align:bottom;background:#f4f4f4;padding:0}
    .merged-pdufa-table th.angle-head>span{position:absolute;left:20px;bottom:7px;display:inline-block;transform:rotate(45deg);transform-origin:bottom left;white-space:nowrap;font-weight:700;color:#111}
    .merged-pdufa-table th.ticker-head,.merged-pdufa-table td.ticker-cell{position:sticky;left:0;z-index:5;background:#fafafa;font-weight:700}
    .merged-pdufa-table th.ticker-head{z-index:6}
    .merged-pdufa-table th.compact-p,.merged-pdufa-table td.compact-p{width:64px;min-width:64px;max-width:64px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .merged-pdufa-table th.group-head{height:38px;background:#111 !important;color:#fff !important;font-weight:900;border:2px solid #000;border-bottom:2px solid #000;font-size:15px}
    .merged-pdufa-table th.group-subhead{height:124px;vertical-align:bottom;font-weight:800;min-width:92px;width:92px;max-width:92px;top:38px}
    .merged-pdufa-table th.financing-subhead{background:#fff3bf !important;border-left:2px solid #000;border-right:1px solid #000}
    .merged-pdufa-table th.financing-subhead .sort-head{white-space:normal !important;line-height:1.15 !important}
    .merged-pdufa-table td.second-fin-cell{min-width:92px;width:92px;max-width:92px;font-weight:900;border-left:1px solid #000}
    .merged-pdufa-table td.second-fin-verified{background:#d9f7df !important;color:#0b6419 !important;font-size:19px !important;font-weight:900 !important}
    .merged-pdufa-table th.application-subhead{height:124px;vertical-align:bottom;font-weight:800;min-width:42px;width:42px;max-width:42px;top:34px}
    .merged-pdufa-table td.application-cell{min-width:42px;width:42px;max-width:42px;font-weight:800}
    .merged-pdufa-table .provision-yes{font-weight:900}
    .header-controls{display:inline-flex;align-items:center;justify-content:center;gap:8px;width:100%%}
    .stage-filter-head{display:inline-flex;align-items:center;justify-content:center;
      margin-left:5px;width:26px;height:25px;cursor:pointer;border:2px solid #111;
      border-radius:5px;background:#fff;color:#111;font-size:16px;font-weight:900}
    .stage-filter-head:hover{background:#f5d77a}
    .finance-filter-head{display:inline-flex;align-items:center;justify-content:center;
      margin-left:5px;width:26px;height:25px;cursor:pointer;border:2px solid #111;
      border-radius:5px;background:#fff;color:#111;font-size:16px;font-weight:900}
    .finance-filter-head:hover{background:#f5d77a}
    .stage-filter-menu{position:fixed;z-index:5000;min-width:270px;max-width:min(380px,85vw);
      max-height:390px;padding:12px;background:#fff;color:#111;border:2px solid #111;
      border-radius:8px;box-shadow:0 6px 16px #0003;overflow:auto;text-align:left;font-size:14px}
    .stage-filter-menu[hidden]{display:none}
    .finance-filter-menu{position:fixed;z-index:5000;min-width:270px;max-width:min(380px,85vw);
      max-height:390px;padding:12px;background:#fff;color:#111;border:2px solid #111;
      border-radius:8px;box-shadow:0 6px 16px #0003;overflow:auto;text-align:left;font-size:14px}
    .finance-filter-menu[hidden]{display:none}
    .finance-count{font-size:12px;margin-top:9px;color:#555}
    .stage-menu-actions{display:flex;gap:7px;margin:10px 0}
    .stage-menu-actions button{border:1px solid #111;padding:5px 8px;border-radius:4px;
      background:#eee;cursor:pointer}
    .stage-checkbox-list{display:flex;flex-direction:column;gap:8px}
    .stage-checkbox-list label{display:flex;gap:8px;align-items:flex-start;white-space:normal}
    .stage-checkbox-list input{margin-top:3px}
    .stage-count{font-size:12px;margin-top:9px;color:#555}
    .stage-order-label{display:block;margin-top:10px;font-weight:700}
    .stage-sort-order{width:100%%;margin-top:5px;padding:5px;border:1px solid #222;
      border-radius:4px;background:#fff;color:#111}

    .sort-head{appearance:none;-webkit-appearance:none;border:0;background:transparent;color:#111;font:inherit;font-weight:800;cursor:pointer;padding:2px 3px;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center}
    .sort-head:hover .sort-icon,.sort-head:focus .sort-icon{background:#111;color:#fff}
    .help-icon{display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto;width:18px;height:18px;border:1.5px solid #555;border-radius:50%%;background:#fff;color:#111;font-size:11px;line-height:1;font-weight:900;vertical-align:middle;cursor:help}
    .help-icon:hover,.help-icon:focus{background:#111;color:#fff;border-color:#111;outline:none}
    .sort-icon{display:inline-block;margin-left:5px;padding:2px 5px;border:2px solid #000;border-radius:5px;background:#fff;color:#000;font-size:15px;line-height:1;font-weight:900;vertical-align:middle}
    a{color:#111}
    </style>
    """ % int(height_px)

    sort_js = """
    <script>
    (() => {
      const table = document.querySelector('.merged-pdufa-table');
      if (!table) return;
      const tbody = table.querySelector('tbody');
      const stageTrigger = table.querySelector('.stage-filter-head');
      const stageMenu = document.querySelector('.stage-filter-menu');
      const financeTrigger = table.querySelector('.finance-filter-head');
      const financeMenu = document.querySelector('.finance-filter-menu');
      const financeChoices = financeMenu ? Array.from(financeMenu.querySelectorAll('.finance-choice')) : [];
      const chosenFinance = () => new Set(financeChoices.filter(c => c.checked).map(c => c.value));
      if (stageTrigger && stageMenu) {
        const choices = Array.from(stageMenu.querySelectorAll('.stage-choice'));
        const updateStages = () => {
          const selected = new Set(choices.filter(c => c.checked).map(c => c.value));
          const selectedFin = chosenFinance();
          Array.from(tbody.querySelectorAll('tr')).forEach(row => {
            row.hidden = !selected.has(row.dataset.stage || '') ||
              (!!financeChoices.length && !selectedFin.has(row.dataset.financing || ''));
            row.style.display = row.hidden ? 'none' : '';
          });
          const shown = Array.from(tbody.querySelectorAll('tr')).filter(r => !r.hidden).length;
          stageMenu.querySelector('.stage-count').textContent =
            shown + ' rows shown · ' + selected.size + ' stages checked';
        };
        const positionMenu = () => {
          const rect = stageTrigger.getBoundingClientRect();
          stageMenu.style.left = Math.min(rect.left, window.innerWidth - 295) + 'px';
          stageMenu.style.top = Math.min(rect.bottom + 5, window.innerHeight - 170) + 'px';
        };
        stageTrigger.addEventListener('click', event => {
          event.preventDefault();
          event.stopPropagation();
          stageMenu.hidden = !stageMenu.hidden;
          if (!stageMenu.hidden) positionMenu();
        });
        stageMenu.addEventListener('click', event => event.stopPropagation());
        const stageSort = stageMenu.querySelector('.stage-sort-order');
        const stageRank = value => {
          const v = String(value || '').toUpperCase();
          if (v.startsWith('FDA APPROVED') || v.startsWith('FDA CRL')) return 110;
          if (v.includes('FDA DECISION PENDING')) return 100;
          if (v.includes('PDUFA / FDA REVIEW')) return 90;
          if (v.includes('FDA APPLICATION ACCEPTED')) return 80;
          if (v.includes('NDA/BLA SUBMITTED')) return 75;
          if (v.includes('2ND FINANCING CLOSED')) return 70;
          if (v.includes('FINANCING IN PROGRESS')) return 60;
          if (v.includes('FINANCING ANNOUNCED')) return 55;
          if (v.includes('PHASE 3 RESULTS') || v.includes('PHASE 3 COMPLETED')) return 50;
          if (v.includes('PHASE 3 ONGOING')) return 40;
          if (v.includes('PHASE 3')) return 35;
          if (v.includes('PHASE 2 COMPLETED')) return 20;
          if (v.includes('PHASE 2')) return 10;
          return 999;
        };
        const sortStageRows = () => {
          const mode = stageSort.value;
          const headers = Array.from(table.querySelectorAll('.sort-head'));
          const daysHeader = headers.find(h => h.querySelector('.sort-label')?.textContent.trim() === 'DAYS TO PDUFA');
          const daysIndex = daysHeader ? Number(daysHeader.dataset.colIndex) : -1;
          const rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort((a,b) => {
            const sa = a.dataset.stage || '';
            const sb = b.dataset.stage || '';
            let result = 0;
            if (mode.startsWith('workflow')) result = stageRank(sa) - stageRank(sb);
            else if (mode.startsWith('alpha')) result = sa.localeCompare(sb,undefined,{numeric:true,sensitivity:'base'});
            else if (daysIndex >= 0) {
              const da = Number(a.children[daysIndex]?.dataset.sort);
              const db = Number(b.children[daysIndex]?.dataset.sort);
              const ea = !a.children[daysIndex]?.dataset.sort?.trim();
              const eb = !b.children[daysIndex]?.dataset.sort?.trim();
              result = ea && eb ? 0 : ea ? 1 : eb ? -1 : da - db;
            }
            if (mode.endsWith('down') && !mode.startsWith('pdufa')) result *= -1;
            if (mode === 'pdufa-down' && daysIndex >= 0) {
              const aa = a.children[daysIndex]?.dataset.sort?.trim();
              const bb = b.children[daysIndex]?.dataset.sort?.trim();
              if (aa && bb) result *= -1;
            }
            return result || Number(a.dataset.originalIndex) - Number(b.dataset.originalIndex);
          });
          rows.forEach(row => tbody.appendChild(row));
        };
        choices.forEach(choice => choice.addEventListener('change', () => {
          updateStages(); sortStageRows();
        }));
        stageSort.addEventListener('change', sortStageRows);
        stageMenu.querySelector('[data-stage-all]').addEventListener('click', () => {
          choices.forEach(choice => choice.checked = true);
          updateStages(); sortStageRows();
        });
        stageMenu.querySelector('[data-stage-none]').addEventListener('click', () => {
          choices.forEach(choice => choice.checked = false);
          updateStages(); sortStageRows();
        });
        document.addEventListener('click', () => stageMenu.hidden = true);
        updateStages();
        sortStageRows();
      }

      if (financeTrigger && financeMenu) {
        const financeSort = financeMenu.querySelector('.finance-sort-order');
        const refreshFinancing = () => {
          const selected = chosenFinance();
          const selectedStage = stageMenu ?
            new Set(Array.from(stageMenu.querySelectorAll('.stage-choice'))
              .filter(c => c.checked).map(c => c.value)) : null;
          Array.from(tbody.querySelectorAll('tr')).forEach(row => {
            row.hidden = !selected.has(row.dataset.financing || '') ||
              (!!selectedStage && !selectedStage.has(row.dataset.stage || ''));
            row.style.display = row.hidden ? 'none' : '';
          });
          const shown = Array.from(tbody.querySelectorAll('tr')).filter(r => !r.hidden).length;
          financeMenu.querySelector('.finance-count').textContent =
            shown + ' rows shown · ' + selected.size + ' statuses checked';
        };
        const sortFinance = () => {
          const mode = financeSort.value;
          if (mode === 'keep') return;
          const flow = mode === 'reverse'
            ? ['FINISHED','RUNNING','STARTED','ANNOUNCED','REVIEW / UNVERIFIED']
            : ['ANNOUNCED','STARTED','RUNNING','FINISHED','REVIEW / UNVERIFIED'];
          const ranks = new Map(flow.map((value,i) => [value,i]));
          const rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort((a,b) => (ranks.get(a.dataset.financing) ?? 999) -
                             (ranks.get(b.dataset.financing) ?? 999) ||
                             Number(a.dataset.originalIndex) - Number(b.dataset.originalIndex));
          rows.forEach(row => tbody.appendChild(row));
        };
        const positionFinanceMenu = () => {
          const rect = financeTrigger.getBoundingClientRect();
          financeMenu.style.left = Math.max(0, Math.min(rect.left, window.innerWidth - 295)) + 'px';
          financeMenu.style.top = Math.max(0, Math.min(rect.bottom + 5, window.innerHeight - 170)) + 'px';
        };
        financeTrigger.addEventListener('click', event => {
          event.preventDefault(); event.stopPropagation();
          financeMenu.hidden = !financeMenu.hidden;
          if (stageMenu) stageMenu.hidden = true;
          if (!financeMenu.hidden) positionFinanceMenu();
        });
        financeMenu.addEventListener('click', event => event.stopPropagation());
        financeChoices.forEach(choice => choice.addEventListener('change', () => {
          refreshFinancing(); sortFinance();
        }));
        financeMenu.querySelector('[data-fin-all]').addEventListener('click', () => {
          financeChoices.forEach(choice => choice.checked = true);
          refreshFinancing();
        });
        financeMenu.querySelector('[data-fin-none]').addEventListener('click', () => {
          financeChoices.forEach(choice => choice.checked = false);
          refreshFinancing();
        });
        financeSort.addEventListener('change', sortFinance);
        document.addEventListener('click', () => financeMenu.hidden = true);
        refreshFinancing();
      }

      const buttons = Array.from(table.querySelectorAll('button.sort-head'));
      let activeIndex = null;
      let ascending = true;

      const compare = (a, b, index, asc) => {
        const ca = a.children[index];
        const cb = b.children[index];
        const va = (ca?.dataset.sort ?? '').trim();
        const vb = (cb?.dataset.sort ?? '').trim();
        const type = ca?.dataset.sortType || 'text';

        const aEmpty = va === '';
        const bEmpty = vb === '';
        if (aEmpty && bEmpty) {
          return Number(a.dataset.originalIndex) - Number(b.dataset.originalIndex);
        }
        if (aEmpty) return 1;
        if (bEmpty) return -1;

        let cmp = 0;
        if (type === 'number') {
          const na = Number(va);
          const nb = Number(vb);
          cmp = (na === nb) ? 0 : (na < nb ? -1 : 1);
        } else {
          cmp = va.localeCompare(vb, undefined, {numeric:true, sensitivity:'base'});
        }
        if (cmp === 0) {
          cmp = Number(a.dataset.originalIndex) - Number(b.dataset.originalIndex);
        }
        return asc ? cmp : -cmp;
      };

      const setIcons = () => {
        buttons.forEach(btn => {
          const idx = Number(btn.dataset.colIndex);
          const icon = btn.querySelector('.sort-icon');
          if (!icon) return;
          icon.textContent = idx === activeIndex ? (ascending ? '▲' : '▼') : '⇅';
        });
      };

      table.querySelectorAll('.help-icon').forEach(help => {
        help.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
        });
      });

      buttons.forEach(btn => {
        btn.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          const index = Number(btn.dataset.colIndex);
          if (activeIndex === index) {
            ascending = !ascending;
          } else {
            activeIndex = index;
            ascending = true;
          }
          const rows = Array.from(tbody.querySelectorAll('tr'));
          rows.sort((a,b) => compare(a,b,index,ascending));
          rows.forEach(row => tbody.appendChild(row));
          setIcons();
        });
      });

      setIcons();
    })();
    </script>
    """

    table_html = (
        local_css
        + f'<div class="merged-table-wrap">'
        + '<table class="merged-pdufa-table">'
        + thead_html
        + '<tbody>'
        + "".join(rows)
        + '</tbody></table></div>'
        + stage_menu_html
        + finance_menu_html
        + sort_js
    )

    st.caption(
        "Click the boxed ⇅ icon in any column heading to sort immediately. "
        "The icon changes to ▲ ascending or ▼ descending; click it again to reverse the order."
    )
    components.html(table_html, height=int(height_px) + 25, scrolling=False)


def table_view(frame, return_page="MASTER TABLE"):
    out = frame.copy()

    # Guarantee every master-table column exists even if the source feed is incomplete.
    defaults = {
        "ticker":"", "company":"Not available", "drug":"Not available", "indication":"Not available",
        "pdufa_date":pd.NaT, "decision_date":pd.NaT, "market_cap":pd.NA, "market_cap_bucket":"Not available",
        "approval_probability":pd.NA, "public_approval_probability":pd.NA, "trade_score":pd.NA, "financing_status":"Not available",
        "setup_phase":"Not available", "short_interest":pd.NA, "iv_30d":pd.NA, "signal":"Not available",
        "confidence":"Not scored", "outcome":"Pending", "application_type":"FDA"
    }
    for c, default in defaults.items():
        if c not in out:
            out[c] = default

    out["pdufa_date"] = pd.to_datetime(out["pdufa_date"], errors="coerce")
    out["PDUFA Date"] = out["pdufa_date"].apply(
        lambda d: "Not available" if pd.isna(d) else pd.Timestamp(d).strftime("%Y-%m-%d")
    )
    out["decision_date"] = pd.to_datetime(out["decision_date"], errors="coerce")
    out["DECISION DATE"] = out["decision_date"].apply(
        lambda d: "" if pd.isna(d) else pd.Timestamp(d).strftime("%Y-%m-%d")
    )
    out["Days Left"] = (out["pdufa_date"] - today).dt.days.astype("Int64")
    out["Days Left"] = out["Days Left"].astype("string").replace("<NA>", "Not available")
    if "_detail_source" not in out:
        out["_detail_source"] = "live"
    out["Ticker Link"] = out.apply(
        lambda r: event_detail_url(
            r,
            source=safe_text(r.get("_detail_source"), "live"),
            return_page=return_page
        ),
        axis=1
    )
    out["Market Cap"] = out["market_cap"].map(fmt_cap)
    out["Cap Bucket"] = out["market_cap_bucket"].fillna("Not available").astype(str)
    out["Probability of Approval % — Public"] = out["public_approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
    out["Probability of Approval % — All Sources"] = out.apply(
        lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1
    )
    out["I Direction"] = out.apply(internal_direction_state, axis=1)
    out["P Direction"] = out.apply(public_direction_state, axis=1)
    out["All-Source Direction"] = out.apply(all_source_direction_state, axis=1)
    out["Direction / FDA Match"] = out.apply(direction_fda_display, axis=1)
    out["Trade Score"] = out["trade_score"].apply(
        lambda v: "Not scored" if pd.isna(v) else f"{float(v):.0f}"
    )
    out["Financing"] = out["financing_status"].fillna("Not available").astype(str)
    out["Phase"] = out["setup_phase"].fillna("Not available").astype(str)
    out["Short %"] = out["short_interest"].map(fmt_pct)
    out["IV (30d)"] = out["iv_30d"].map(fmt_pct)
    out["Signal"] = out["signal"].fillna("Not available").astype(str)
    out["Confidence"] = out["confidence"].fillna("Not scored").astype(str)
    out["Outcome"] = out["outcome"].fillna("Pending").astype(str)
    out["Application"] = out["application_type"].fillna("Not available").astype(str)
    out["Record Source"] = out["_detail_source"].apply(
        lambda v: "Historical Model" if str(v) == "history" else "Saved Feed"
    )
    out = add_special_provision_columns(out)
    out["STAGE"] = frame.apply(program_stage, axis=1)

    for c in ["ticker","company","drug","indication"]:
        out[c] = out[c].fillna("Not available").astype(str)

    return out.rename(columns={
        "company":"Company","drug":"Drug","indication":"Indication","Ticker Link":"Ticker"
    })[[
        "Ticker","STAGE","PDUFA Date","DECISION DATE","Probability of Approval % — Public","Probability of Approval % — All Sources","Direction / FDA Match","I Direction","P Direction","All-Source Direction","Company","Drug","Indication",
        *SPECIAL_PROVISION_LABELS,
        "Days Left","Market Cap","Cap Bucket","Trade Score","Outcome","Signal","Confidence","Application",
        "Financing","Phase","Short %","IV (30d)","Record Source"
    ]]

query_event = st.query_params.get("event")
query_ticker = st.query_params.get("ticker")
query_page = st.query_params.get("page")
query_source = st.query_params.get("source") or "live"
query_return = st.query_params.get("return") or "MASTER TABLE"

if query_page == "detail" and query_event:
    st.session_state.selected_event_key = str(query_event)
    if query_ticker:
        st.session_state.selected_ticker = str(query_ticker)
    st.session_state.selected_detail_source = str(query_source)
    st.session_state.detail_return_page = str(query_return)
    st.session_state.detail_open = True
    st.query_params.clear()


def _scan_scope_frame(scope):
    scope = str(scope).upper()
    active = df[df["pdufa_date"].notna() & (df["pdufa_date"] >= today)].copy()
    if scope == "TODAY":
        return active[active["pdufa_date"].dt.date == date.today()].copy()
    if scope == "WEEK":
        end = today + pd.Timedelta(days=7)
        return active[(active["pdufa_date"] >= today) & (active["pdufa_date"] <= end)].copy()
    return active.copy()

def _record_streamlit_scan(action, scope):
    frame = _scan_scope_frame(scope)
    stamp = pd.Timestamp.now(tz="America/Los_Angeles").strftime("%Y-%m-%d %H:%M:%S %Z")
    request = {
        "action": action,
        "scope": scope,
        "requested_at": stamp,
        "candidate_count": int(len(frame)),
    }
    st.session_state.scan_request = request
    log = st.session_state.get("scan_log", [])
    log.insert(0, request)
    st.session_state.scan_log = log[:25]
    return frame, request

def scan_inputs_today():
    load_data.clear()
    return _record_streamlit_scan("RESCAN INPUTS", "TODAY")

def scan_inputs_week():
    load_data.clear()
    return _record_streamlit_scan("RESCAN INPUTS", "WEEK")

def scan_inputs_all():
    load_data.clear()
    return _record_streamlit_scan("RESCAN INPUTS", "ALL")

def scan_approval_today():
    load_prediction_history.clear()
    return _record_streamlit_scan("PROBABILITY OF APPROVAL", "TODAY")

def scan_approval_week():
    load_prediction_history.clear()
    return _record_streamlit_scan("PROBABILITY OF APPROVAL", "WEEK")

def scan_approval_all():
    load_prediction_history.clear()
    return _record_streamlit_scan("PROBABILITY OF APPROVAL", "ALL")

if "nav" not in st.session_state:
    st.session_state.nav = "MASTER TABLE"
if "detail_open" not in st.session_state:
    st.session_state.detail_open = False
if "selected_detail_source" not in st.session_state:
    st.session_state.selected_detail_source = "live"
if "detail_return_page" not in st.session_state:
    st.session_state.detail_return_page = "MASTER TABLE"
if "selected_ticker" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_ticker = str(base.iloc[0]["ticker"]) if not base.empty else ""
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "position_candidates" not in st.session_state:
    st.session_state.position_candidates = []
if "selected_event_key" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_event_key = make_event_key(base.iloc[0]) if not base.empty else ""

st.title("🧬 BIO PDUFA COMMAND CENTER")
st.caption("BUILD 2026-10-06K · FDA DECISION ENGINE V3.2 STRICT + DIRECTIONAL V1.9 + REGULATORY BLIND-SPOT MONITOR · STATS + CMC + FACILITY + BIMO GATES · FINANCING CACHE FIX")
st.caption("OPERATING FLOW: MASTER TABLE → WATCHLIST → ANALYSIS → INVEST. Use the calendar, decisions, scans and research pages for supporting review.")
st.caption("Approval scoring is independent: Internal PoA + Public-Evidence PoA form Our Consensus PoA. Direction / FDA Match remains separately validated against final FDA outcomes.")

if "_pending_nav" in st.session_state:
    st.session_state.nav = st.session_state.pop("_pending_nav")
    st.session_state.detail_open = False

nav_options = ["PIPELINE","TODAY","MASTER TABLE","DISEASE & MARKET HORIZON","STRATEGY","2. PDUFA CALENDAR","4. DECISION","5. SCANS","6. RECHECK","9. PREDICTION ENGINE","10. MATCH OPTIMIZER","11. PLAN"]
# Existing sessions and saved detail links may still refer to removed pages.
if st.session_state.nav not in nav_options:
    st.session_state.nav = "MASTER TABLE"
if st.session_state.detail_return_page not in nav_options:
    st.session_state.detail_return_page = "MASTER TABLE"
if st.session_state.detail_open:
    page = "__DETAIL__"
else:
    st.radio("Navigation", nav_options, horizontal=True, key="nav", label_visibility="collapsed")
    page = st.session_state.nav
    if len(st.query_params):
        st.query_params.clear()

if page == "TODAY":
    try:
        _phase_today = pd.read_csv("data/phase3_announcements.csv", keep_default_na=False)
    except (OSError, pd.errors.ParserError):
        _phase_today = pd.DataFrame()
    try:
        _finance_today = pd.read_csv("data/second_financing_status.csv", keep_default_na=False)
    except (OSError, pd.errors.ParserError):
        _finance_today = pd.DataFrame()
    try:
        _intake_state = json.loads(Path("data/phase3_intake_status.json").read_text(encoding="utf-8"))
        st.caption("Phase 3 registry intake: " + str(_intake_state.get("status", "UNKNOWN")) + " · " + str(_intake_state.get("studies_checked", 0)) + " studies checked in latest run · " + str(_intake_state.get("stored_results", 0)) + " cumulative records · " + str(_intake_state.get("finished_at", "not completed")))
        if _intake_state.get("status") not in ("COMPLETE", "COMPLETE WITH WARNINGS"):
            st.warning("Phase 3 historical/daily registry scan is incomplete. Counts are partial. Corporate press-release discovery is a separate evidence source.")
        elif _intake_state.get("status") == "COMPLETE WITH WARNINGS":
            st.warning("Phase 3 registry collection finished with source warnings; the overall PDUFA universe may still be incomplete.")
    except (OSError, ValueError):
        st.warning("Phase 3 automated intake has not yet reported a completed scan. Historical coverage remains incomplete.")
    render_today(df, _phase_today, _finance_today)

if page == "MASTER TABLE":
    st.markdown("## MASTER TABLE — PROGRAM REVIEW THROUGH FDA DECISION")
    st.caption("Verified Phase 3 programs and manually selected PIPELINE programs arrive here. Watchlist, Analysis and Invest follow below; recorded phases, scores and entry eligibility remain subject to their own evidence checks.")
    master, phase3_arrivals, phase_pipeline_state = master_with_phase3(df)
    master = master.reset_index(drop=True)
    manual_arrivals = sum(row.get("pipeline_transfer_mode") == "MANUAL REVIEW" for row in phase3_arrivals)
    st.caption(f"{len(phase3_arrivals) - manual_arrivals:,} additional Phase 3 programs · {manual_arrivals:,} manual PIPELINE reviews · PDUFA dates remain blank until confirmed.")
    if master.empty:
        st.info("No PDUFA records are currently loaded.")
    else:
        # Canonical columns collapse equivalent names without discarding conflicting evidence.
        aliases = {
            "Ticker": ["ticker", "symbol"],
            "Drug": ["drug", "drug_name", "product_name"],
            "Indication": ["indication", "disease"],
            "Current Stage": ["current_stage"],
            "Next Milestone": ["next_milestone"],
            "Phase 3 Started": ["phase3_start_date"],
            "Moved to Master": ["pipeline_promoted_at"],
            "Stage Evidence": ["pipeline_evidence_status"],
            "NCT": ["nct_id", "nct"],
            "Phase 3 Readout": ["phase3_date", "phase_3_date", "readout_date"],
            "P (p-value)": ["reported_p_values", "p_value"],
            "Trial Status": ["trial_status", "study_status"],
            "Financing #1 Date": ["first_financing_date"],
            "Financing #2 Date": ["second_financing_date"],
            "Financing Type": ["second_financing_type", "financing_type"],
            "Financing Proceeds": ["financing_proceeds"],
            "Dilution / ATM": ["new_dilution_flag"],
            "Cash": ["cash"],
            "Cash Runway (months)": ["cash_runway_months"],
            "NDA Submission": ["nda_submission_date"],
            "FDA Acceptance": ["fda_acceptance_date"],
            "PDUFA Date": ["pdufa_date"],
            "FDA PoA": ["approval_probability"],
            "Entry Gate": ["entry_gate"],
            "Market Cap": ["market_cap", "market_cap_usd"],
            "Evidence Status": ["check_status"],
        }
        combined = pd.DataFrame(index=master.index)
        consumed = set()
        for title, choices in aliases.items():
            present = [c for c in choices if c in master.columns]
            if present:
                combined[title] = master[present[0]]
                consumed.add(present[0])
                for other in present[1:]:
                    # Keep alternative values separate if both sources disagree.
                    left = combined[title].astype("string").fillna("").str.strip()
                    right = master[other].astype("string").fillna("").str.strip()
                    conflict = left.ne("") & right.ne("") & left.ne(right)
                    if conflict.any():
                        combined[other + " (alternate)"] = master[other]
                    else:
                        combined[title] = combined[title].where(left.ne(""), master[other])
                    consumed.add(other)
        for col in master.columns:
            if col not in consumed and col not in combined.columns:
                combined[col] = master[col]
        # Add computed views from Funnel, Trading Flow and Market Cap without
        # duplicating their shared source columns.
        if "Ticker" in combined:
            tickers = combined["Ticker"].fillna("").astype(str).str.upper()
            combined["Watchlist #2"] = tickers.isin(
                {str(x).upper() for x in st.session_state.get("watchlist", [])}
            )
            combined["Entry Review"] = tickers.isin(
                {str(x).upper() for x in st.session_state.get("position_candidates", [])}
            )
        if "PDUFA Date" in combined:
            dates = pd.to_datetime(combined["PDUFA Date"], errors="coerce")
            combined["DAYS TO PDUFA"] = (dates - today).dt.days.astype("Int64")
            combined["PDUFA Horizon"] = combined["DAYS TO PDUFA"].map(pdufa_segment)
        if "Market Cap" in combined:
            cap = pd.to_numeric(combined["Market Cap"], errors="coerce")
            combined["Market Cap Band"] = pd.cut(
                cap, bins=[0, 300_000_000, 1_000_000_000, 3_000_000_000, 10_000_000_000, float("inf")],
                labels=["UNDER $300M", "$300M–$1B", "$1B–$3B", "$3B–$10B", "OVER $10B"],
                include_lowest=True, right=False
            ).astype("string").fillna("UNKNOWN")
        if "Financing #2 Date" in combined:
            combined["Second Financing Date Recorded"] = (
                combined["Financing #2 Date"].notna()
                & combined["Financing #2 Date"].astype(str).str.strip().ne("")
            )
            combined["Financing Close Verified"] = "REVIEW — verify SEC/company closing evidence"
        if "Entry Gate" in combined:
            combined["Funnel Stage (provisional)"] = combined["Entry Gate"].fillna("REVIEW").astype(str).map(
                lambda v: "ENTRY REVIEW" if v.upper() == "PASS" else "REVIEW / DISCOVERY"
            )
        # FDA directional assessments are event-level only when ticker, drug,
        # and PDUFA date uniquely match. Never join by ticker alone.
        if isinstance(fda_directional_live, pd.DataFrame) and not fda_directional_live.empty:
            fda_keys = ("ticker", "drug", "pdufa_date")
            if all(k in fda_directional_live.columns for k in fda_keys) and all(k in master.columns for k in fda_keys):
                fda_subset = fda_directional_live.copy()
                def _event_key(frame):
                    return (
                        frame["ticker"].fillna("").astype(str).str.upper().str.strip()
                        + "|" + frame["drug"].fillna("").astype(str).str.upper().str.strip()
                        + "|" + pd.to_datetime(frame["pdufa_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
                    )
                fda_subset["_event_key"] = _event_key(fda_subset)
                source_keys = _event_key(master)
                valid = fda_subset["_event_key"].str.split("|", regex=False).map(
                    lambda parts: len(parts) == 3 and all(parts)
                )
                fda_subset = fda_subset[valid & ~fda_subset["_event_key"].duplicated(keep=False)]
                fda_subset = fda_subset.set_index("_event_key")
                for field, label in (("forced_direction", "FDA Direction"), ("directional_score", "FDA Direction Score"),
                                     ("confidence", "FDA Confidence"), ("strict_v3_prediction", "FDA Strict Prediction")):
                    if field in fda_subset:
                        combined[label] = source_keys.map(fda_subset[field])
        # Step 1: preserve Trading Flow and Funnel derived fields.
        def _finance_closed(row):
            values = []
            for field in ("second_financing_status", "second_financing_close_verified", "second_financing_closed"):
                value = row.get(field, "")
                values.append("" if pd.isna(value) else str(value).upper())
            status = " ".join(values)
            return "SECOND_CLOSE_VERIFIED" in status or "RED_CLOSED" in status or any(v in ("YES", "TRUE", "1", "VERIFIED") for v in values)
        closed_flags = master.apply(_finance_closed, axis=1)
        readout_flags = pd.to_datetime(master.get("phase3_date", pd.Series(pd.NaT, index=master.index)), errors="coerce").notna()
        gate_flags = master.get("entry_gate", pd.Series("REVIEW", index=master.index)).fillna("REVIEW").astype(str).str.upper().eq("PASS")
        combined["Funnel Stage"] = "4 · WATCHLIST / ENTRY REVIEW"
        combined.loc[~readout_flags, "Funnel Stage"] = "1 · DISCOVERY / READOUT REVIEW"
        combined.loc[readout_flags & ~closed_flags, "Funnel Stage"] = "3 · FINANCING REVIEW"
        combined.loc[readout_flags & closed_flags & gate_flags, "Funnel Stage"] = "5 · ENTRY REVIEW — GATE PASS"
        combined["Second Financing Verified"] = closed_flags.map({True: "YES", False: "REVIEW"})
        combined["🟢 Financing Started"] = ""
        combined["🟡 Financing In Progress"] = ""
        combined["🔴 Financing Closed"] = closed_flags.map({True: "🔴 CLOSED", False: ""})
        status_values = master.get("second_financing_status", pd.Series("", index=master.index)).fillna("").astype(str).str.upper()
        combined.loc[status_values.str.contains("STARTED|ANNOUNCED", regex=True), "🟢 Financing Started"] = "🟢 STARTED"
        combined.loc[status_values.str.contains("IN_PROGRESS|PENDING|PRICED", regex=True), "🟡 Financing In Progress"] = "🟡 IN PROGRESS"
        for source, label in (("second_financing_status", "Financing #2 Status"), ("second_financing_source", "Financing Close Evidence"), ("market_cap_bucket", "Validated Market Cap Bucket"), ("public_approval_probability", "Our FDA PoA"), ("trade_score", "Our Trade/PDUFA Score"), ("phase3_date", "Company Readout Date"), ("nct_id", "NCT"), ("trial_status", "Trial Status"), ("primary_completion", "Primary Completion"), ("study_completion", "Study Completion"), ("results_first_posted", "Results First Posted")):
            if source in master:
                combined[label] = master[source]
        submitted = pd.to_datetime(master.get("nda_submission_date", pd.Series(pd.NaT, index=master.index)), errors="coerce").notna()
        accepted = pd.to_datetime(master.get("fda_acceptance_date", pd.Series(pd.NaT, index=master.index)), errors="coerce").notna()
        combined["NDA/BLA Status"] = "REVIEW"
        combined.loc[submitted, "NDA/BLA Status"] = "SUBMITTED"
        combined.loc[accepted, "NDA/BLA Status"] = "FDA ACCEPTED"
        # Step 2: attach FDA monitor data by exact, unique event identity.
        def _attach_event_fields(source_frame, prefix):
            if not isinstance(source_frame, pd.DataFrame) or source_frame.empty:
                return
            keys = ("ticker", "drug", "pdufa_date")
            if not all(k in source_frame.columns for k in keys) or not all(k in master.columns for k in keys):
                return
            def make_key(frame):
                return frame["ticker"].fillna("").astype(str).str.upper().str.strip() + "|" + frame["drug"].fillna("").astype(str).str.upper().str.strip() + "|" + pd.to_datetime(frame["pdufa_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
            source = source_frame.copy()
            source["_master_key"] = make_key(source)
            source = source[source["_master_key"].map(lambda v: all(v.split("|")))]
            source = source[~source["_master_key"].duplicated(keep=False)].set_index("_master_key")
            target = make_key(master)
            for field in source.columns:
                if field not in keys:
                    label = prefix + " · " + field.replace("_", " ").title()
                    combined[label] = target.map(source[field])
        _attach_event_fields(fda_regulatory_signals, "FDA Monitor")
        _attach_event_fields(fda_extension_ledger, "FDA Extension")
        _attach_event_fields(fda_directional_live, "FDA Directional")
        # Preserve detailed FDA review fields merged into df at startup.
        for field in master.columns:
            if field.startswith("fda_") and field not in combined:
                combined[field] = master[field]
        # Step 3: market-cap bands and historical All PDUFA coverage.
        if "Market Cap" in combined:
            cap_numeric = pd.to_numeric(combined["Market Cap"], errors="coerce")
            fine_edges = [0, 300e6, 500e6, 750e6, 1e9, 2e9, 3e9, 5e9, 7.5e9, 10e9, float("inf")]
            fine_labels = ["<$300M", "$300M–$500M", "$500M–$750M", "$750M–$1B", "$1B–$2B", "$2B–$3B", "$3B–$5B", "$5B–$7.5B", "$7.5B–$10B", ">$10B"]
            combined["Detailed Market Cap Band"] = pd.cut(cap_numeric, bins=fine_edges, labels=fine_labels, right=False).astype("string").fillna("UNKNOWN")
        # Historical cohorts are not live events. Expose their columns in the
        # master schema without fabricating event-level joins.
        historical_count = len(prediction_history) if isinstance(prediction_history, pd.DataFrame) else 0
        combined["Record Source"] = master.get("record_source", pd.Series("LIVE PDUFA EVENT", index=master.index)).fillna("LIVE PDUFA EVENT")
        # Bring every loaded source schema into the master, preserving provenance.
        # Unique event keys are required; duplicate or incomplete keys are
        # intentionally left blank rather than assigned to the wrong drug.
        extra_sources = (
            ("FDA Facilities", fda_facilities),
            ("FDA Backfill", fda_backfill_queue),
            ("FDA Freezes", fda_freezes),
            ("Historical Predictions", prediction_history),
        )
        for prefix, frame in extra_sources:
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                continue
            keys = ("ticker", "drug", "pdufa_date")
            eligible = all(k in frame.columns for k in keys) and all(k in master.columns for k in keys)
            source_keys = None
            if eligible:
                def _complete_keys(f):
                    parts = [
                        f[k].fillna("").astype(str).str.strip().str.upper()
                        if k != "pdufa_date" else
                        pd.to_datetime(f[k], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
                        for k in keys
                    ]
                    valid = parts[0].ne("") & parts[1].ne("") & parts[2].ne("")
                    return parts[0] + "|" + parts[1] + "|" + parts[2], valid
                source_keys, source_valid = _complete_keys(frame)
                target_keys, target_valid = _complete_keys(master)
                unique = source_valid & ~source_keys.duplicated(keep=False)
            for field in frame.columns:
                label = prefix + " · " + str(field)
                if label in combined.columns:
                    continue
                if eligible and field not in keys:
                    mapping = pd.Series(frame.loc[unique, field].to_numpy(), index=source_keys.loc[unique])
                    combined[label] = target_keys.map(mapping).where(target_valid)
                else:
                    # Retain column discoverability while keeping unrelated
                    # historical rows and incomplete keys out of live records.
                    combined[label] = pd.Series(pd.NA, index=combined.index, dtype="object")
        # All source fields are visible in the master, including fields that
        # cannot safely be joined. No synthetic evidence is treated as a pass.
        # Shared column tabs keep related fields compact and preserve every source column.
        if "watchlist" not in st.session_state:
            st.session_state["watchlist"] = []
        ticker_values = combined["Ticker"].fillna("").astype(str).str.upper().str.strip()
        watch_values = {str(x).upper().strip() for x in st.session_state["watchlist"]}
        combined.insert(0, "Watchlist", ticker_values.isin(watch_values))
        st.markdown("### PDUFA COUNTDOWN — DATE GRADIENT")
        st.caption("Five categories: 0–30 red · 31–60 orange · 61–90 yellow · 90+ green · NO PDUFA YET gray. Darker shading means a nearer FDA target date within its segment. Past-due dates are separate.")
        if "DAYS TO PDUFA" in combined.columns:
            countdown = combined.loc[combined["DAYS TO PDUFA"].isna() | (combined["DAYS TO PDUFA"] >= 0), [c for c in ("Ticker", "Drug", "Indication", "PDUFA Date", "DAYS TO PDUFA", "PDUFA Horizon") if c in combined.columns]].copy()
            if not countdown.empty:
                countdown["PDUFA Horizon"] = countdown["DAYS TO PDUFA"].map(lambda d: "NO PDUFA YET" if pd.isna(d) else pdufa_segment(d))
                countdown["PDUFA Date"] = countdown["PDUFA Date"].where(countdown["DAYS TO PDUFA"].notna(), "Not verified")
                countdown = countdown.sort_values("DAYS TO PDUFA", kind="stable", na_position="last")
                tab_labels = ["ALL", "0–30 DAYS", "31–60 DAYS", "61–90 DAYS", "90+ DAYS", "NO PDUFA YET"]
                category_tabs = st.tabs([f"{label} ({len(countdown) if label == 'ALL' else int((countdown['PDUFA Horizon'] == label).sum())})" for label in tab_labels])
                for label, category_tab in zip(tab_labels, category_tabs):
                    with category_tab:
                        section = countdown.copy() if label == "ALL" else countdown.loc[countdown["PDUFA Horizon"] == label].copy()
                        if section.empty:
                            st.info(f"No candidates in {label}.")
                        else:
                            styled_section = section.style.apply(lambda row: [pdufa_date_color(row["DAYS TO PDUFA"]) if col in ("PDUFA Date", "DAYS TO PDUFA", "PDUFA Horizon") else "" for col in section.columns], axis=1)
                            st.dataframe(styled_section, use_container_width=True, hide_index=True, height=min(460, 80 + 35 * len(section)))
            else:
                st.info("No PDUFA candidates available in the loaded events.")
        st.markdown("### MASTER TABLE — WATCHLIST")
        st.caption("Ticker → STAGE → DAYS TO PDUFA stays visible in every view. Related fields are grouped into tabs; use the field selector for additional sections.")
        display_view = stage_filter_panel(combined, key="master_table", source=master, expanded=True)
        display_fields = list(display_view.columns)
        display_help = {c: st.column_config.TextColumn(c + " ⓘ", help=f"{c}: source or calculated event field; verify evidence and reporting date.") for c in display_fields if c != "Watchlist"}
        display_help["Watchlist"] = st.column_config.CheckboxColumn("WATCHLIST ⓘ", help="Check to add this ticker to your Watchlist.", default=False)
        edited_master = grouped_editor(display_view, stage_controls=False, use_container_width=True, hide_index=True, height=650, column_config=display_help, disabled=[c for c in display_fields if c != "Watchlist"], key="master_watchlist_main_editor")
        changed_watch = edited_master["Watchlist"].fillna(False).astype(bool).ne(display_view["Watchlist"].fillna(False).astype(bool))
        if changed_watch.any():
            selected_watch = set(watch_values)
            for row_id in display_view.index[changed_watch]:
                ticker = ticker_values.loc[row_id]
                if ticker:
                    if bool(edited_master.loc[row_id, "Watchlist"]):
                        selected_watch.add(ticker)
                    else:
                        selected_watch.discard(ticker)
            st.session_state["watchlist"] = sorted(selected_watch)
            st.rerun()
        st.caption(f"Watchlist: {len(watch_values)} tickers selected")
        # Watchlist rows can be promoted independently to Analysis and Invest.
        for state_key in ("master_analysis", "master_invest"):
            if state_key not in st.session_state:
                st.session_state[state_key] = []
        @st.fragment(run_every="60s")
        def render_watchlist_indicators():
            st.markdown("### WATCHLIST — SELECTED STOCKS")
            current_watch = {str(v).upper().strip() for v in st.session_state.get("watchlist", [])}
            watch_rows = combined[ticker_values.isin(current_watch)].copy()
            if not watch_rows.empty:
                watch_rows = stage_filter_panel(watch_rows, key="watchlist_stage", source=master)
            st.caption(f"{len(watch_rows):,} selected event rows · {len(current_watch):,} tickers")
            # Eight paired technical indicators are displayed in both ENTRY and EXIT mode.
            # Never synthesize trade calls when a verified scanner feed is unavailable.
            indicator_names = ["Volume / RVOL", "Bollinger (20,2)", "Phase 3 AVWAP",
                               "EMA (10/20/50)", "RSI (14)", "MACD (12/26/9)",
                               "OBV", "ATR (14)"]
            signal_mode = st.radio("WATCHLIST INDICATORS", ["ENTRY", "EXIT", "BOTH"],
                                   horizontal=True, key="watchlist_indicator_mode")
            st.caption("Eight matching indicators per stock. NOT SCANNED means no validated technical signal has been loaded; it is not a buy or sell recommendation.")
            indicator_file = Path("data/watchlist_indicator_signals.csv")
            signal_rows = pd.DataFrame()
            if indicator_file.exists():
                try:
                    signal_rows = pd.read_csv(indicator_file, dtype=str, keep_default_na=False)
                    if not {"ticker", "mode"}.issubset(signal_rows.columns):
                        signal_rows = pd.DataFrame()
                    else:
                        signal_rows["ticker"] = signal_rows["ticker"].str.upper().str.strip()
                        signal_rows["mode"] = signal_rows["mode"].str.upper().str.strip()
                except (OSError, ValueError, pd.errors.ParserError):
                    signal_rows = pd.DataFrame()
                    st.warning("Indicator data could not be loaded; signals are marked NOT SCANNED.")
            active_modes = ["ENTRY", "EXIT"] if signal_mode == "BOTH" else [signal_mode]
            displayed_indicators = []
            if not watch_rows.empty:
                tickers_for_signals = watch_rows["Ticker"].fillna("").astype(str).str.upper().str.strip()
                for active_mode in active_modes:
                    mode_rows = signal_rows.loc[signal_rows["mode"].eq(active_mode)] if not signal_rows.empty else pd.DataFrame()
                    if not mode_rows.empty:
                        mode_rows = mode_rows.drop_duplicates("ticker", keep="last").set_index("ticker")
                    for indicator in indicator_names:
                        label = f"{active_mode} | {indicator}" if signal_mode == "BOTH" else indicator
                        displayed_indicators.append(label)
                        if not mode_rows.empty and indicator in mode_rows.columns:
                            values = tickers_for_signals.map(mode_rows[indicator])
                            watch_rows[label] = values.fillna("").replace("", "NOT SCANNED").to_numpy()
                        else:
                            watch_rows[label] = "NOT SCANNED"
                    timestamp_label = f"{active_mode} | Updated" if signal_mode == "BOTH" else "Signal Updated"
                    displayed_indicators.append(timestamp_label)
                    if not mode_rows.empty and "updated_at" in mode_rows.columns:
                        watch_rows[timestamp_label] = tickers_for_signals.map(mode_rows["updated_at"]).fillna("NOT SCANNED").to_numpy()
                    else:
                        watch_rows[timestamp_label] = "NOT SCANNED"
            else:
                displayed_indicators = [
                    f"{mode} | {name}" if signal_mode == "BOTH" else name
                    for mode in active_modes for name in indicator_names
                ] + (["ENTRY | Updated", "EXIT | Updated"] if signal_mode == "BOTH" else ["Signal Updated"])
            st.caption("This watchlist display refreshes every 60 seconds while the app is open. Live indicator calculations require a connected 1-minute data feed and scanner; missing signals stay NOT SCANNED.")
            if st.button("↻ REFRESH WATCHLIST NOW", key="refresh_watchlist_signals"):
                st.rerun(scope="fragment")
            watch_cols = [c for c in ("Ticker", "STAGE", "DAYS TO PDUFA", "Drug", "Indication", "PDUFA Date", "Funnel Stage", "Entry Gate", "FDA PoA", "Financing #2 Date", "Second Financing Verified", "Market Cap", "Evidence Status") if c in watch_rows.columns]
            watch_cols += displayed_indicators
            if watch_rows.empty:
                st.info("No Watchlist stocks selected. Check WATCHLIST in the Master Table above.")
            else:
                analysis_set = {str(v).upper().strip() for v in st.session_state["master_analysis"]}
                watch_rows.insert(0, "Add to Analysis", watch_rows["Ticker"].fillna("").astype(str).str.upper().str.strip().isin(analysis_set))
                visible = ["Add to Analysis"] + watch_cols
                watch_config = {c: st.column_config.TextColumn(c + " ⓘ", help="Watchlist event field: " + c) for c in watch_cols}
                watch_config["Add to Analysis"] = st.column_config.CheckboxColumn("Analysis ⓘ", help="Check to add this ticker to the Analysis table; uncheck to remove it.")
                watch_edited = grouped_editor(watch_rows[visible], stage_controls=False, use_container_width=True, hide_index=True, height=360, column_config=watch_config, disabled=watch_cols, key="watchlist_promotion_editor")
                changed_analysis = watch_edited["Add to Analysis"].fillna(False).astype(bool).ne(watch_rows["Add to Analysis"].fillna(False).astype(bool))
                if changed_analysis.any():
                    for row_id in watch_rows.index:
                        ticker = str(watch_rows.loc[row_id, "Ticker"]).upper().strip()
                        if not ticker:
                            continue
                        if changed_analysis.loc[row_id]:
                            (analysis_set.add if bool(watch_edited.loc[row_id, "Add to Analysis"]) else analysis_set.discard)(ticker)
                    st.session_state["master_analysis"] = sorted(analysis_set)
                    st.rerun()
        render_watchlist_indicators()
        def attach_technical_columns(rows, selected_mode):
            """Read one shared signal snapshot; do not infer missing trading signals."""
            names = ["Volume / RVOL", "Bollinger (20,2)", "Phase 3 AVWAP",
                     "EMA (10/20/50)", "RSI (14)", "MACD (12/26/9)",
                     "OBV", "ATR (14)"]
            modes = ["ENTRY", "EXIT"] if selected_mode == "BOTH" else [selected_mode]
            columns = []
            out = rows.copy()
            source = Path("data/watchlist_indicator_signals.csv")
            feed = pd.DataFrame()
            if source.exists():
                try:
                    feed = pd.read_csv(source, dtype=str, keep_default_na=False)
                    if {"ticker", "mode"}.issubset(feed.columns):
                        feed["ticker"] = feed["ticker"].str.upper().str.strip()
                        feed["mode"] = feed["mode"].str.upper().str.strip()
                    else:
                        feed = pd.DataFrame()
                except (OSError, ValueError, pd.errors.ParserError):
                    feed = pd.DataFrame()
            symbols = out["Ticker"].fillna("").astype(str).str.upper().str.strip() if "Ticker" in out else pd.Series(dtype=str)
            for mode in modes:
                subset = feed.loc[feed["mode"].eq(mode)].drop_duplicates("ticker", keep="last").set_index("ticker") if not feed.empty else pd.DataFrame()
                for name in names:
                    label = f"{mode} | {name}" if selected_mode == "BOTH" else name
                    columns.append(label)
                    if not subset.empty and name in subset.columns:
                        out[label] = symbols.map(subset[name]).fillna("").replace("", "NOT SCANNED").to_numpy()
                    else:
                        out[label] = "NOT SCANNED"
                label = f"{mode} | Updated" if selected_mode == "BOTH" else "Signal Updated"
                columns.append(label)
                if not subset.empty and "updated_at" in subset.columns:
                    out[label] = symbols.map(subset["updated_at"]).fillna("").replace("", "NOT SCANNED").to_numpy()
                else:
                    out[label] = "NOT SCANNED"
            return out, columns

        @st.fragment(run_every="60s")
        def render_analysis_invest_signals():
            # Keep both tables on the same signal snapshot and display mode.
            shared_mode = st.radio("ANALYSIS / INVEST INDICATORS",
                                   ["ENTRY", "EXIT", "BOTH"], horizontal=True,
                                   index=2, key="analysis_invest_indicator_mode")
            st.caption("Refreshes every minute while open. Signals require the connected scanner; NOT SCANNED means no validated data.")
            if st.button("↻ REFRESH ANALYSIS / INVEST", key="refresh_analysis_invest_signals"):
                st.rerun(scope="fragment")
            analysis_tickers = {str(v).upper().strip() for v in st.session_state["master_analysis"]}
            invest_tickers = {str(v).upper().strip() for v in st.session_state["master_invest"]}
            analysis_rows = combined[ticker_values.isin(analysis_tickers)].copy()
            if not analysis_rows.empty:
                analysis_rows = stage_filter_panel(analysis_rows, key="analysis_stage", source=master)
            st.markdown("#### ANALYSIS" + f" ({len(analysis_rows):,})")
            detail_cols = [c for c in ("Ticker", "STAGE", "DAYS TO PDUFA", "Drug", "Indication", "PDUFA Date", "Entry Gate", "FDA PoA", "Evidence Status", "Financing #2 Date", "Market Cap") if c in combined.columns]
            if analysis_rows.empty:
                st.info("No candidates selected for Analysis. Use the Analysis checkbox in Watchlist above.")
            else:
                analysis_rows, tech_cols = attach_technical_columns(analysis_rows, shared_mode)
                analysis_rows.insert(0, "Add to Invest", analysis_rows["Ticker"].fillna("").astype(str).str.upper().str.strip().isin(invest_tickers))
                invest_config = {c: st.column_config.TextColumn(c + " ⓘ", help="Analysis event field: " + c) for c in detail_cols + tech_cols}
                invest_config["Add to Invest"] = st.column_config.CheckboxColumn("Invest ⓘ", help="Check to add this ticker to Invest; uncheck to remove it.")
                edited_analysis = grouped_editor(analysis_rows[["Add to Invest"] + detail_cols + tech_cols], stage_controls=False, use_container_width=True, hide_index=True, height=360, column_config=invest_config, disabled=detail_cols + tech_cols, key="analysis_to_invest_editor")
                invest_changed = edited_analysis["Add to Invest"].fillna(False).astype(bool).ne(analysis_rows["Add to Invest"].fillna(False).astype(bool))
                if invest_changed.any():
                    for row_id in analysis_rows.index[invest_changed]:
                        ticker = str(analysis_rows.loc[row_id, "Ticker"]).upper().strip()
                        if ticker:
                            if bool(edited_analysis.loc[row_id, "Add to Invest"]):
                                invest_tickers.add(ticker)
                            else:
                                invest_tickers.discard(ticker)
                    st.session_state["master_invest"] = sorted(invest_tickers)
                    st.rerun()
            invest_rows = combined[ticker_values.isin(invest_tickers)].copy()
            if not invest_rows.empty:
                invest_rows = stage_filter_panel(invest_rows, key="invest_stage", source=master)
            st.markdown("#### INVEST" + f" ({len(invest_rows):,})")
            if invest_rows.empty:
                st.info("No candidates selected for Invest. Use the Invest checkbox in Analysis above.")
            else:
                invest_rows, tech_cols = attach_technical_columns(invest_rows, shared_mode)
                grouped_dataframe(invest_rows[detail_cols + tech_cols], stage_controls=False, use_container_width=True, hide_index=True)

        render_analysis_invest_signals()
        st.caption("Lists are session-only. Invest tracks candidates; it does not place orders.")

        with st.expander("Additional original-source tables (preserved without unsafe joins)"):
            for source_name, source_frame in (("FDA regulatory signals", fda_regulatory_signals), ("FDA extensions", fda_extension_ledger), ("FDA facilities", fda_facilities), ("FDA backfill queue", fda_backfill_queue), ("FDA prediction freezes", fda_freezes), ("Historical predictions", prediction_history)):
                st.markdown("#### " + source_name)
                if isinstance(source_frame, pd.DataFrame) and not source_frame.empty:
                    st.caption(f"{len(source_frame):,} records · {len(source_frame.columns)} columns")
                    grouped_dataframe(source_frame, use_container_width=True, hide_index=True)
                else:
                    st.info("No loaded records.")
    st.caption("The Master Table consolidates loaded source columns. Missing evidence is not treated as verified.")

elif page == "PIPELINE":
    st.markdown("## PIPELINE — ALL CLINICAL AND REGULATORY STAGES")
    pipeline_today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    pipeline_signature = tuple(
        (name, (Path("data") / name).stat().st_mtime_ns)
        for name in PIPELINE_SOURCE_FILES if (Path("data") / name).exists()
    )
    universe = load_pipeline_universe_data(pipeline_signature, pipeline_today)
    with st.container(border=True):
        st.markdown("### PICK DEVELOPMENT STAGES")
        enabled_stages = st.pills(
            "Stages to display",
            options=list(PIPELINE_STAGES),
            selection_mode="multi",
            default=list(PIPELINE_STAGES),
            key="pipeline_universe_stages_pills",
            width="stretch",
            help="Click one or more stages to filter the pipeline.",
        )
    # The DATES selector belongs immediately below "Stages to display".
    # Do not project a company's application deadline onto unrelated trials.
    date_bands = (
        "0–30 DAYS", "31–60 DAYS", "61–90 DAYS", "+90 DAYS",
        "NO PDUFA YET", "PAST / RECHECK",
    )
    band_colors = {
        "0–30 DAYS": "#fce0e0",
        "31–60 DAYS": "#ffead5",
        "61–90 DAYS": "#fff6ce",
        "+90 DAYS": "#e0f2de",
        "NO PDUFA YET": "#edf0f3",
        "PAST / RECHECK": "#eadff3",
    }
    dates = pd.to_datetime(
        universe["pdufa_date"].astype(str).str[:10],
        format="%Y-%m-%d", errors="coerce",
    )
    universe = universe.copy()
    universe["Days to PDUFA"] = (dates - pd.Timestamp(pipeline_today)).dt.days

    def date_band(days):
        if pd.isna(days):
            return "NO PDUFA YET"
        if days < 0:
            return "PAST / RECHECK"
        if days <= 30:
            return "0–30 DAYS"
        if days <= 60:
            return "31–60 DAYS"
        if days <= 90:
            return "61–90 DAYS"
        return "+90 DAYS"

    universe["DATES"] = universe["Days to PDUFA"].map(date_band)
    with st.container(border=True):
        st.markdown("### PICK PDUFA DATES")
        date_symbols = {
            "0–30 DAYS": "🔴",
            "31–60 DAYS": "🟠",
            "61–90 DAYS": "🟡",
            "+90 DAYS": "🟢",
            "NO PDUFA YET": "⚪",
            "PAST / RECHECK": "🟣",
        }
        date_counts = universe["DATES"].value_counts().to_dict()
        selected_dates = st.pills(
            "DATES to display",
            options=list(date_bands),
            selection_mode="multi",
            default=list(date_bands),
            format_func=lambda band: (
                f"{date_symbols[band]} {band} ({date_counts.get(band, 0):,})"
            ),
            key="pipeline_universe_dates_pills",
            width="stretch",
            help="Click one or more countdown ranges; colors match the pipeline table.",
        )
        sort_dates = st.selectbox(
            "Sort pipeline", ["Closest PDUFA first", "Ticker A–Z"],
            key="pipeline_universe_date_sort",
        )
        st.caption("Colored circles identify the date bands; rows retain their date colors. "
                   "Countdowns update daily. NO PDUFA YET means no linked PDUFA date; "
                   "PAST / RECHECK does not imply an FDA decision.")
    date_filtered = universe[universe["DATES"].isin(selected_dates)].copy()
    st.markdown("### COUNT FOR EACH STAGE")
    st.dataframe(
        pipeline_stage_counts(date_filtered), use_container_width=True,
        hide_index=True, height=530,
    )
    st.caption("Counts reflect your selected DATES ranges. A trial may be counted in multiple development stages; the combined list counts it once.")
    search = st.text_input("Find ticker, drug, indication or NCT ID", key="pipeline_universe_search").strip()
    visible = select_pipeline_records(date_filtered, enabled_stages, search)
    date_order = {band: index for index, band in enumerate(date_bands)}
    visible = visible.assign(_date_rank=visible["DATES"].map(date_order))
    if sort_dates == "Ticker A–Z":
        visible = visible.sort_values(["ticker", "_date_rank", "Days to PDUFA"], na_position="last")
    else:
        visible = visible.sort_values(["_date_rank", "Days to PDUFA", "ticker"], na_position="last")
    visible = visible.drop(columns=["_date_rank"])
    st.metric("Trials / programs displayed", f"{len(visible):,}")
    trial_count = visible.loc[visible["nct_id"].ne(""), "nct_id"].nunique()
    st.caption(f"Unique registered trial IDs in this list: {trial_count:,}")
    state_path = Path("data/all_phase_scan_state.json")
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            st.caption(
                f"Clinical scan: {state.get('companies_checked', 0):,} / "
                f"{state.get('registry_companies', 0):,} registry companies checked · "
                f"{state.get('status', 'UNKNOWN')} · "
                f"Company warnings: {state.get('companies_with_warnings', 0):,}"
            )
            if "tracked_trials_total" in state:
                st.caption(
                    f"Saved trial IDs checked: {state.get('tracked_trials_checked', 0):,} / "
                    f"{state.get('tracked_trials_total', 0):,} · "
                    f"Trial check warnings: {state.get('tracked_trials_with_warnings', 0):,}"
                )
        except (OSError, ValueError):
            pass
    st.caption("Source and evidence status are retained on each record. Posted results do not establish trial success, and a past PDUFA target does not establish an FDA decision. Historical outcomes are marked as recorded evidence.")
    if not enabled_stages:
        st.info("Choose at least one stage to display records.")
    elif not selected_dates:
        st.info("Choose at least one DATES range to display records.")
    elif visible.empty:
        st.info("No loaded records match these stages or search.")
    else:
        labels = {
            "DATES": "DATES", "Days to PDUFA": "Days to PDUFA",
            "ticker": "Ticker", "company": "Company", "current_stage": "Current Stage",
            "record_type": "Record Type", "drug": "Drug", "indication": "Indication",
            "nct_id": "NCT ID", "registered_phase": "Registered Phase", "status": "Trial Status",
            "results_posted": "Results Posted", "nda_submission_date": "NDA/BLA Submission Date",
            "fda_acceptance_date": "FDA Acceptance Date", "pdufa_date": "PDUFA Target",
            "decision_date": "FDA Decision Date", "outcome": "Recorded Outcome",
            "evidence_status": "Evidence Status", "checked_at": "Last Checked",
            "source_url": "Source", "evidence_note": "Evidence Note",
        }
        st.dataframe(
            visible[list(labels)].rename(columns=labels).style.apply(
                lambda row: [
                    f"background-color:{band_colors.get(row['DATES'], '#ffffff')};color:#18202a;"
                    for _ in row
                ], axis=1,
            ),
            use_container_width=True, hide_index=True, height=560,
            column_config={"Source": st.column_config.LinkColumn("Source")},
        )
    if st.button("REFRESH PIPELINE DATA", key="pipeline_refresh"):
        load_pipeline_universe_data.clear()
        st.rerun()

elif page == "DISEASE & MARKET HORIZON":
    st.markdown("## DISEASE & MARKET HORIZON")
    st.caption("Disease burden, competing therapies, and commercial opportunity for each Phase 3 drug and indication. Unverified values must remain blank—not estimated as facts.")
    st.link_button("Open disease and market research sheet", "https://docs.google.com/spreadsheets/d/1lBfjuXloQnoUTOJZYnu6v6PAHrZSqJoWn_-6L6wt-fY/edit#gid=204610070")
    st.markdown("### Disease burden and addressable patients")
    st.info("Research fields: U.S./global prevalence, incidence, diagnosed patients, eligible patients, treatable population, severity, and unmet need. Record geography, year, definition, and source.")

    issue_trials_path = Path("data/issue_trials.csv")
    issue_ledger_path = Path("data/all_phase_trials.csv")
    issue_trials_signature = (
        issue_trials_path.stat().st_mtime_ns if issue_trials_path.exists() else 0,
        issue_ledger_path.stat().st_mtime_ns if issue_ledger_path.exists() else 0,
    )
    issue_trials = load_issue_trial_catalog(issue_trials_signature)
    st.markdown("### Clinical trials by issue")
    if issue_trials.empty:
        st.info("No curated issue trials are loaded.")
    else:
        issue_options = sorted(issue_trials["issue"].dropna().astype(str).loc[lambda s: s.ne("")].unique())
        selected_issues = st.multiselect(
            "Issues to display",
            options=issue_options,
            default=issue_options,
            key="issue_trial_issue_filter",
        )
        issue_visible = issue_trials[issue_trials["issue"].isin(selected_issues)].copy()
        if issue_visible.empty:
            st.info("Choose at least one issue to display its trials.")
        else:
            issue_visible["ClinicalTrials.gov"] = issue_visible["nct_id"].map(
                lambda nct: "https://clinicaltrials.gov/study/" + str(nct)
            )
            issue_labels = {
                "issue": "Issue",
                "ticker": "Ticker",
                "company": "Company",
                "drug": "Drug",
                "trial_name": "Trial",
                "nct_id": "NCT ID",
                "phase": "Phase",
                "status": "Trial Status",
                "target_population_note": "Target Population",
                "source_updated": "Registry Updated",
                "checked_at": "Registry Checked",
                "evidence_url": "Evidence",
                "ClinicalTrials.gov": "ClinicalTrials.gov",
            }
            issue_columns = [
                "issue", "ticker", "company", "drug", "trial_name", "nct_id",
                "phase", "status", "target_population_note", "source_updated",
                "checked_at", "ClinicalTrials.gov", "evidence_url",
            ]
            st.dataframe(
                issue_visible[issue_columns].rename(columns=issue_labels),
                use_container_width=True,
                hide_index=True,
                height=560,
                column_config={
                    "ClinicalTrials.gov": st.column_config.LinkColumn("ClinicalTrials.gov"),
                    "Evidence": st.column_config.LinkColumn("Evidence"),
                },
            )
            st.caption(
                f"{len(issue_visible):,} curated trial records across "
                f"{issue_visible['issue'].nunique():,} issue groups. "
                "Trial status and registry dates are refreshed from ClinicalTrials.gov by the daily scan."
            )

    st.markdown("### Competing therapies")
    st.info("Compare approved therapies and Phase 2/3 competitors by mechanism, efficacy, safety, dosing, price/access, and development status. Mark direct head-to-head evidence separately from cross-trial comparisons.")
    st.markdown("### Commercial valuation and our scores")
    st.info("Estimate penetration, potential peak sales, sales relative to market cap, Competitive Advantage Score, and Commercial Opportunity Score. Keep OUR FDA PoA separate from OUR TRADE SCORE and Entry Gate.")
    st.warning("This page is a research framework linked to the Google Sheet. Live company-by-company epidemiology, competitor research, score calculation, and Sheet synchronization are not yet connected.")


elif page == "STRATEGY":
    # Derive this view from the same persisted Pipeline universe and stage
    # selection as PIPELINE; curate only exact NCT annotations, never its scope.
    strategy_today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    strategy_signature = tuple(
        (name, (Path("data") / name).stat().st_mtime_ns)
        for name in PIPELINE_SOURCE_FILES if (Path("data") / name).exists()
    )
    strategy_universe = load_pipeline_universe_data(strategy_signature, strategy_today)
    issue_trials_path = Path("data/issue_trials.csv")
    issue_ledger_path = Path("data/all_phase_trials.csv")
    issue_trials_signature = (
        issue_trials_path.stat().st_mtime_ns if issue_trials_path.exists() else 0,
        issue_ledger_path.stat().st_mtime_ns if issue_ledger_path.exists() else 0,
    )
    strategy_catalog = load_issue_trial_catalog(issue_trials_signature)
    render_strategy_page(strategy_universe, strategy_catalog)


elif page == "2. PDUFA CALENDAR":
    st.markdown("## 2. PDUFA CALENDAR — UPCOMING CATALYSTS")
    st.caption("Four weeks at a time. Move backward or forward in 4-week blocks without losing the event drill-down.")

    if "calendar_offset_weeks" not in st.session_state:
        st.session_state.calendar_offset_weeks = 0

    nav1, nav2, nav3 = st.columns([1,1,1])
    with nav1:
        if st.button("← PREVIOUS 4 WEEKS", use_container_width=True):
            st.session_state.calendar_offset_weeks -= 4
            st.rerun()
    with nav2:
        if st.button("TODAY", use_container_width=True):
            st.session_state.calendar_offset_weeks = 0
            st.rerun()
    with nav3:
        if st.button("NEXT 4 WEEKS →", use_container_width=True):
            st.session_state.calendar_offset_weeks += 4
            st.rerun()

    window_start = today + pd.Timedelta(weeks=st.session_state.calendar_offset_weeks)
    window_end = window_start + pd.Timedelta(days=27)

    st.markdown(
        f"### {window_start.strftime('%b %d, %Y')} – {window_end.strftime('%b %d, %Y')}"
    )

    week_sets = []
    for i in range(4):
        week_start = window_start + pd.Timedelta(days=7*i)
        week_end = week_start + pd.Timedelta(days=6)
        hits = df[
            df["pdufa_date"].notna() &
            (df["pdufa_date"] >= week_start) &
            (df["pdufa_date"] <= week_end)
        ].copy().sort_values(["pdufa_date","ticker"])
        week_sets.append((week_start,week_end,hits))

    st.metric("PDUFA DECISIONS IN THIS 4-WEEK WINDOW", sum(len(x[2]) for x in week_sets))

    cols = st.columns(4)
    for i,(week_start,week_end,hits) in enumerate(week_sets):
        with cols[i]:
            st.metric(
                f"Week {i+1}: {week_start.strftime('%b %d')}–{week_end.strftime('%b %d')}",
                len(hits)
            )

    week_pick = st.radio(
        "Drill into week",
        ["Week 1","Week 2","Week 3","Week 4"],
        horizontal=True,
        key=f"calendar_week_pick_{st.session_state.calendar_offset_weeks}"
    )
    wi = int(week_pick[-1]) - 1
    wstart,wend,whits = week_sets[wi]

    st.markdown(f"### {week_pick}: {wstart.strftime('%b %d, %Y')} – {wend.strftime('%b %d, %Y')}")
    if whits.empty:
        st.info("No saved PDUFA events in this week.")
    else:
        display = table_view(whits, return_page="2. PDUFA CALENDAR")
        event = grouped_dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=min(560, 110 + 36*len(display)),
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this exact PDUFA detail page",
                ),
                "Probability of Approval % — Public": st.column_config.TextColumn(
                    "Probability of Approval % — Public", help="Public-only approval probability", width="medium"
                ),
                "Probability of Approval % — All Sources": st.column_config.TextColumn(
                    "Probability of Approval % — All Sources", help="All-source approval probability", width="medium"
                ),
            },
            on_select="rerun",
            selection_mode="single-row",
            key=f"calendar_week_table_{st.session_state.calendar_offset_weeks}_{wi}"
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = whits.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row), source="live", return_page="2. PDUFA CALENDAR")
            st.rerun()

    st.divider()
    st.markdown("### Month Calendar")
    months = sorted({(d.year,d.month) for d in df["pdufa_date"].dropna()})
    opts = [f"{calendar.month_name[m]} {y}" for y,m in months] or [date.today().strftime("%B %Y")]

    window_month_label = f"{calendar.month_name[window_start.month]} {window_start.year}"
    default_month_index = opts.index(window_month_label) if window_month_label in opts else 0

    choice = st.selectbox("Month", opts, index=default_month_index)
    mi = opts.index(choice)
    y,m = months[mi] if months else (date.today().year,date.today().month)

    hdr = st.columns(7)
    for col,n in zip(hdr,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
        col.markdown(f"**{n}**")

    for week in calendar.Calendar().monthdatescalendar(y,m):
        cols = st.columns(7)
        for col,day in zip(cols,week):
            with col:
                st.markdown(
                    f"**{day.day}**" if day.month == m
                    else f"<span class='muted'>{day.day}</span>",
                    unsafe_allow_html=True
                )
                hits = df[df["pdufa_date"].dt.date == day]
                for hit_idx, r in hits.iterrows():
                    calendar_label = html.escape(
                        f"{r.ticker} · Public {calendar_app_text(r, 'public_approval_probability')} · "
                        f"All {fmt_app_pct(all_source_probability_value(r), 1)} · "
                        f"Dir {direction_fda_display(r)} · "
                        f"{pd.Timestamp(r.get('pdufa_date')).strftime('%b %d')}"
                    )
                    calendar_url = html.escape(
                        event_detail_url(r, source="live", return_page="2. PDUFA CALENDAR"),
                        quote=True
                    )
                    st.markdown(
                        f'<a class="calendar-event-link" href="{calendar_url}" target="_self">{calendar_label}</a>',
                        unsafe_allow_html=True
                    )

elif page == "9. PREDICTION ENGINE":
    st.markdown("## 9. PREDICTION ENGINE — MODEL VALIDATION")
    st.caption("Canonical $300M–$10B historical cohort. 2020–2022 are retrospective development history, 2023 is the tuning year, 2024 is the first locked validation year, 2025 is the later holdout, and 2026 is current/model-development history. Missing historical vendor/public probabilities are never fabricated.")

    hist = prediction_history.copy()
    hist = hist[
        hist["pdufa_date"].notna() &
        (hist["pdufa_date"] >= pd.Timestamp("2020-01-01")) &
        (hist["pdufa_date"] <= pd.Timestamp("2026-09-30"))
    ].copy()
    if "public_approval_probability" not in hist:
        hist["public_approval_probability"] = pd.NA
    hist["Probability of Approval % — Public"] = hist["public_approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
    hist["Probability of Approval % — All Sources"] = hist.apply(lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1)
    hist["P%"] = hist.apply(lambda r: displayed_probability_text(r, 1), axis=1)
    hist["SUGGESTION %"] = hist.apply(lambda r: displayed_probability_text(r, 1), axis=1)
    hist["SUGGESTION"] = hist.apply(suggestion_word_display, axis=1)
    hist["FDA Decision"] = hist.apply(fda_decision_display, axis=1)
    hist["MATCH %"] = hist.apply(match_percent_display, axis=1)
    hist["F"] = hist.apply(predicted_fda_direction, axis=1)
    hist["Match %"] = hist.apply(match_percent_display, axis=1)
    hist["C"] = hist.apply(combined_probability_direction, axis=1)
    hist["I Direction"] = hist.apply(internal_direction_state, axis=1)
    hist["P Direction"] = hist.apply(public_direction_state, axis=1)
    hist["I+P Direction"] = hist.apply(ip_consensus_direction, axis=1)
    hist["All-Source Direction"] = hist.apply(all_source_direction_state, axis=1)
    hist["Direction / FDA Match"] = hist.apply(direction_fda_display, axis=1)
    hist["Correct / Wrong"] = hist["correct"].astype(str).map(
        {"True":"Correct","False":"Wrong","true":"Correct","false":"Wrong"}
    ).fillna("NA")
    hist["Historical Market Cap"] = hist["historical_market_cap_billions"].apply(
        lambda v: "NA" if pd.isna(v) else f"${float(v):.2f}B"
    )

    hist["V2 Status"] = hist.apply(prediction_v2_history_status, axis=1)
    hist["Audit Eligible"] = hist["count_in_audited_accuracy"].astype(str).str.upper().eq("YES")
    hist["Needs Rescore Bool"] = hist["needs_rescore"].astype(str).str.upper().eq("YES")

    f1,f2,f3,f4,f5 = st.columns([1.1,1.2,1.2,1.4,2.0])
    with f1:
        available_pred_years = sorted(hist["pdufa_date"].dropna().dt.year.astype(int).unique().tolist())
        year_pick = st.selectbox("Year", ["All"] + available_pred_years, key="pred_year")
    with f2:
        pred_pick = st.selectbox("Prediction", ["All","APPROVED","CRL"], key="pred_class")
    with f3:
        actual_pick = st.selectbox("Actual FDA", ["All","APPROVED","CRL"], key="pred_actual")
    with f4:
        bucket_pick = st.selectbox(
            "Market Cap Bucket", ["All","$300M–$1B","$1B–$3B","$3B–$10B"], key="pred_bucket"
        )
    with f5:
        pred_search = st.text_input("Search ticker or event key", key="pred_search")

    g1,g2 = st.columns([1.5,4])
    with g1:
        v2_pick = st.selectbox(
            "V2 Audit State",
            ["All","CLEAN / KEEP","CLEAN MODEL MISS","REBUILD / RESCORE","REVIEW"],
            key="pred_v2_state"
        )
    with g2:
        st.caption("V2 never overwrites legacy predictions. Rows that fail identity/date/leakage checks are blocked from validation until rebuilt.")

    hview = hist.copy()
    if year_pick != "All":
        hview = hview[hview["pdufa_date"].dt.year == int(year_pick)]
    if pred_pick != "All":
        hview = hview[hview["model_class"] == pred_pick]
    if actual_pick != "All":
        hview = hview[hview["actual_outcome"] == actual_pick]
    if bucket_pick != "All":
        hview = hview[hview["market_cap_bucket"] == bucket_pick]
    if v2_pick != "All":
        hview = hview[hview["V2 Status"] == v2_pick]
    if pred_search:
        q = pred_search.lower()
        hview = hview[
            hview["ticker"].astype(str).str.lower().str.contains(q, na=False) |
            hview["event_key"].astype(str).str.lower().str.contains(q, na=False)
        ]

    render_historical_assessed_decisions(hview["event_key"])
    st.markdown("### ORIGINAL MODEL AND AUDIT RECORDS")
    st.caption("The original probability-derived suggestions below are preserved for comparison with the assessed decisions above.")

    # Recalculate every summary box from the CURRENT filtered selection.
    filtered_correct = hview["Correct / Wrong"].eq("Correct")
    filtered_avg_i = hview["p_approval"].mean() * 100 if not hview.empty else float("nan")
    filtered_avg_p = pd.to_numeric(hview.get("public_approval_probability"), errors="coerce").mean()
    if pd.notna(filtered_avg_p) and filtered_avg_p <= 1:
        filtered_avg_p = filtered_avg_p * 100
    i_scored = pd.to_numeric(hview["p_approval"], errors="coerce").notna().sum()
    p_scored = pd.to_numeric(hview.get("public_approval_probability"), errors="coerce").notna().sum()
    i_coverage = 0.0 if hview.empty else (i_scored / len(hview)) * 100
    p_coverage = 0.0 if hview.empty else (p_scored / len(hview)) * 100
    hview["_all_source_score"] = hview.apply(all_source_probability_value, axis=1)
    all_scored = pd.to_numeric(hview["_all_source_score"], errors="coerce").notna().sum()
    all_coverage = 0.0 if hview.empty else (all_scored / len(hview)) * 100
    filtered_avg_all = pd.to_numeric(hview["_all_source_score"], errors="coerce").mean()
    audited = hview[hview["count_in_audited_accuracy"].astype(str).str.upper().eq("YES")].copy()
    audited_correct = audited["Correct / Wrong"].eq("Correct")

    # Precision mode: only make an APPROVED call at >=95% I App.
    # Everything else abstains/reviews. This threshold currently yields 100%
    # historical called-case accuracy on the clean audited cohort, but low coverage.
    audited["_i_pct"] = pd.to_numeric(audited["p_approval"], errors="coerce") * 100
    precision_called = audited[audited["_i_pct"] >= 95].copy()
    precision_correct = precision_called["actual_outcome"].astype(str).str.upper().eq("APPROVED")
    precision_accuracy = float("nan") if precision_called.empty else precision_correct.mean() * 100
    precision_coverage = 0.0 if audited.empty else len(precision_called) / len(audited) * 100

    # Public-evidence precision backtest.
    audited["_p_public_pct"] = pd.to_numeric(audited.get("public_approval_probability"), errors="coerce") * 100
    public_called = audited[
        (audited["_p_public_pct"] >= 90) | (audited["_p_public_pct"] <= 10)
    ].copy()
    public_expected = public_called["_p_public_pct"].apply(lambda v: "APPROVED" if v >= 90 else "CRL")
    public_correct = public_expected.eq(public_called["actual_outcome"].astype(str).str.upper())
    public_precision_accuracy = float("nan") if public_called.empty else public_correct.mean() * 100
    public_precision_coverage = 0.0 if audited.empty else len(public_called) / len(audited) * 100

    audited["I Direction"] = audited.apply(internal_direction_state, axis=1)
    audited["P Direction"] = audited.apply(public_direction_state, axis=1)
    i_dir_called = audited[audited["I Direction"].isin(["APPROVED","CRL"])].copy()
    p_dir_called = audited[audited["P Direction"].isin(["APPROVED","CRL"])].copy()
    i_dir_correct = i_dir_called["I Direction"].eq(i_dir_called["actual_outcome"].astype(str).str.upper())
    p_dir_correct = p_dir_called["P Direction"].eq(p_dir_called["actual_outcome"].astype(str).str.upper())
    i_direction_accuracy = float("nan") if i_dir_called.empty else i_dir_correct.mean() * 100
    p_direction_accuracy = float("nan") if p_dir_called.empty else p_dir_correct.mean() * 100
    i_direction_coverage = 0.0 if audited.empty else len(i_dir_called) / len(audited) * 100
    p_direction_coverage = 0.0 if audited.empty else len(p_dir_called) / len(audited) * 100

    excluded_count = int((hview["count_in_audited_accuracy"].astype(str).str.upper() == "NO").sum())
    rescore_count = int((hview["needs_rescore"].astype(str).str.upper() == "YES").sum())
    clean_keep_count = int(hview["V2 Status"].isin(["CLEAN / KEEP","CLEAN MODEL MISS"]).sum())
    clean_miss_count = int((hview["V2 Status"] == "CLEAN MODEL MISS").sum())

    st.markdown("### PREDICTION SUMMARY")
    pred_dirs = hview.apply(predicted_fda_direction, axis=1) if not hview.empty else pd.Series(dtype="object")
    pred_a = int((pred_dirs == "APPROVED").sum())
    pred_c = int((pred_dirs == "CRL").sum())
    pred_r = int((pred_dirs == "REVIEW").sum())
    pred_displayed_p = hview.apply(displayed_probability_value, axis=1) if not hview.empty else pd.Series(dtype="float64")
    pred_displayed_avg = pd.to_numeric(pred_displayed_p, errors="coerce").mean()
    pred_p = "" if pd.isna(pred_displayed_avg) else f"{pred_displayed_avg:.1f}%"
    pred_f = f"A {pred_a} · C {pred_c} · R {pred_r}"
    pred_match_values = hview.apply(match_percent_display, axis=1) if not hview.empty else pd.Series(dtype="object")
    pred_decided_matches = pred_match_values[pred_match_values.isin(["100%","0%"])]
    pred_match = "" if pred_decided_matches.empty else f"{(pred_decided_matches == '100%').mean()*100:.1f}%"
    pred_combined = f"{pred_p} · {pred_f}"
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("P%", pred_p, help="Average all-sources Probability of Approval for the filtered Prediction Engine cases")
    p2.metric("F", pred_f, help="FDA direction counts: A=APPROVED, C=CRL, R=REVIEW")
    p3.metric("Match %", pred_match, help="Direction-pick accuracy on historical cases with final FDA outcomes in the current filtered selection")
    p4.metric("C", pred_combined, help="Combined P% + FDA direction")

    q1,q2,q3,q4 = st.columns(4)
    q1.metric("Clean Cases", clean_keep_count)
    q2.metric("Clean Model Misses", clean_miss_count)
    q3.metric("Rebuild / Rescore Queue", max(excluded_count, rescore_count))
    q4.metric("Audit Reviewed", f"{len(hview)}/{len(hview)}")

    st.caption(
        f"Filtered selection: {len(hview)} of {len(hist)} cases. "
        "The table and all summary boxes recalculate from the same selected rows."
    )

    hview = hview.sort_values(["pdufa_date","ticker"]).copy()
    hview["Ticker"] = hview.apply(
        lambda r: stock_chart_url(r.get("ticker")), axis=1
    )
    hview["PDUFA Date"] = hview["pdufa_date"].dt.strftime("%Y-%m-%d")
    hview["P"] = hview["reported_p_values"].apply(lambda v: safe_text(v, ""))
    hview = add_second_financing_columns(hview)
    hview = add_application_columns(hview)
    hview = add_special_provision_columns(hview)
    hdisplay = hview[[
        "Ticker","PDUFA Date","SUGGESTION %","SUGGESTION","FDA Decision","MATCH %","P",*SECOND_FINANCING_COLUMNS,*APPLICATION_COLUMNS,"F","C",
        *SPECIAL_PROVISION_LABELS,
        "Probability of Approval % — Public","I Direction","P Direction",
        "model_class",
        "Historical Market Cap","market_cap_bucket","Correct / Wrong","V2 Status",
        "audit_status","failure_reason","canonical_pdufa_date","audit_action","needs_rescore",
        "count_in_audited_accuracy","source_url","validation_period","independence_status"
    ]].rename(columns={
        "model_class":"Model Prediction",
        "market_cap_bucket":"Market Cap Bucket",
        "audit_status":"Audit Status",
        "failure_reason":"Failure Reason",
        "canonical_pdufa_date":"Canonical PDUFA",
        "audit_action":"Audit Action",
        "needs_rescore":"Needs Rescore",
        "count_in_audited_accuracy":"Count in Adjusted Accuracy",
        "source_url":"Audit Source",
        "validation_period":"Validation Period",
        "independence_status":"Validation Role"
    })

    st.caption(f"Showing {len(hdisplay)} of {len(hist)} historical model cases.")
    render_merged_table(hdisplay, "PREDICTION ENGINE TABLE", height_px=690)

    st.info(
        "Clean-as-is Accuracy is NOT the final model accuracy. It uses only rows that survived the first-pass audit without requiring reconstruction. "
        "Rows in the Rebuild / Rescore Queue must be corrected to the canonical event and rescored with a strictly pre-decision cutoff before final validation metrics are calculated."
    )

    with st.expander("REBUILD / RESCORE WORK QUEUE", expanded=False):
        queue = prediction_rescore_queue.copy()
        if queue.empty:
            st.info("Rescore queue is not available.")
        else:
            work = queue[queue["queue_class"] != "KEEP_AS_IS"].copy()
            rescore = work[
                work["queue_class"].isin([
                    "REBUILD_CANONICAL_EVENT",
                    "REBUILD_DECISION_SAFE_CUTOFF",
                    "VERIFY_THEN_RESCORE",
                    "REBUILD_REVIEW",
                ])
            ].copy()
            remove_only = work[work["queue_class"] == "REMOVE_ONLY"].copy()

            r1,r2,r3,r4 = st.columns(4)
            r1.metric("Historical Rows", len(queue))
            r2.metric("Remove Only", len(remove_only))
            r3.metric("True Rescore Cases", len(rescore))
            r4.metric(
                "Existing Artifacts",
                int((rescore["artifact_status"] == "EXISTING_LEVEL8_LEVEL9_MATCH").sum())
            )

            st.caption(
                "Remove-only rows are duplicates, wrong identities, post-outcome rows, or out-of-period events. "
                "They are not rescored. Only the True Rescore Cases require a new canonical prediction."
            )

            queue_filter = st.radio(
                "Work queue view",
                ["True Rescore Cases","Remove Only","All Blocked Rows"],
                horizontal=True,
                key="prediction_rescore_view"
            )
            if queue_filter == "True Rescore Cases":
                qview = rescore
            elif queue_filter == "Remove Only":
                qview = remove_only
            else:
                qview = work

            qdisplay = qview[[
                "ticker","canonical_pdufa_date","original_event_key","queue_class",
                "cutoff_rule","artifact_status","audit_status","audit_action",
                "failure_reason","source_url"
            ]].rename(columns={
                "ticker":"Ticker",
                "original_event_key":"Original Event",
                "canonical_pdufa_date":"Canonical PDUFA",
                "queue_class":"Queue Class",
                "cutoff_rule":"Cutoff Rule",
                "artifact_status":"Artifact Status",
                "audit_status":"Audit Status",
                "audit_action":"Required Action",
                "failure_reason":"Reason",
                "source_url":"Source"
            })

            grouped_dataframe(
                qdisplay,
                use_container_width=True,
                hide_index=True,
                height=min(700, 120 + 32*len(qdisplay)),
                column_config={
                    "Source": st.column_config.LinkColumn("Source", display_text="Source")
                }
            )

    st.divider()
    st.markdown("### FDA Decision Engine V3 — Prospective Regulatory Layer")
    st.caption(
        "FDA V3 is regulatory-only and conservative by design. It separates clinical/statistical/safety/CMC/inspection/regulatory review "
        "from the Trading Engine. Market cap, price, momentum, short interest, IV, financing and ownership do not enter the FDA probability."
    )

    live_v2 = future.copy()
    if live_v2.empty:
        st.info("No future PDUFA rows are currently available for the V2 gate.")
    else:
        gate_results = live_v2.apply(prospective_gate_state, axis=1)
        live_v2["V2 Call"] = [x[0] for x in gate_results]
        live_v2["V2 Confidence"] = [x[1] for x in gate_results]
        live_v2["V2 Gate Reason"] = [x[2] for x in gate_results]
        live_v2["FDA Model %"] = live_v2.get("fda_probability", pd.Series(index=live_v2.index, dtype="object")).apply(
            lambda v: "" if safe_text(v, "") == "" else fmt_app_pct(v, 1)
        )
        live_v2["FDA Gate"] = live_v2.get("fda_hard_gate", pd.Series(index=live_v2.index, dtype="object")).apply(
            lambda v: safe_text(v, "REVIEW")
        )
        live_v2["Probability of Approval % — Public"] = live_v2["public_approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
        live_v2["Probability of Approval % — All Sources"] = live_v2.apply(lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1)
        live_v2["P%"] = live_v2.apply(lambda r: displayed_probability_text(r, 1), axis=1)
        live_v2["F"] = live_v2.apply(predicted_fda_direction, axis=1)
        live_v2["Match %"] = live_v2.apply(match_percent_display, axis=1)
        live_v2["C"] = live_v2.apply(combined_probability_direction, axis=1)
        live_v2["All-Source Direction"] = live_v2["F"]
        live_v2["Direction / FDA Match"] = live_v2.apply(direction_fda_display, axis=1)
        live_v2["PDUFA Date"] = live_v2["pdufa_date"].dt.strftime("%Y-%m-%d")
        live_v2["Ticker"] = live_v2.apply(
            lambda r: stock_chart_url(r.get("ticker")), axis=1
        )

        actionable = live_v2[live_v2["V2 Call"].isin(["APPROVED","CRL"])]
        review = live_v2[~live_v2["V2 Call"].isin(["APPROVED","CRL"])]

        z1,z2,z3,z4 = st.columns(4)
        z1.metric("Future Candidates", len(live_v2))
        z2.metric("High-Confidence Calls", len(actionable))
        z3.metric("Review / Abstain", len(review))
        z4.metric(
            "Actionable Coverage",
            "0.0%" if live_v2.empty else f"{len(actionable)/len(live_v2)*100:.1f}%"
        )

        v2display = live_v2[[
            "Ticker","PDUFA Date","FDA Model %","V2 Call","FDA Gate","V2 Confidence","V2 Gate Reason",
            "P%","F","Match %","C","Probability of Approval % — Public","drug","indication",
            "pdufa_confirmation","phase3_status","monitor_eligibility","conflict_flag"
        ]].rename(columns={
            "drug":"Drug",
            "indication":"Indication",
            "pdufa_confirmation":"PDUFA Verification",
            "phase3_status":"Phase 3",
            "monitor_eligibility":"Eligibility",
            "conflict_flag":"Conflict"
        })

        grouped_dataframe(
            v2display,
            use_container_width=True,
            hide_index=True,
            height=min(650, 120 + 34*len(v2display)),
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this ticker stock chart"
                )
            }
        )
        st.caption(
            "A high-confidence V2 call requires verified event identity, adequate pivotal evidence, no unresolved conflict, "
            "and complete clinical/regulatory/safety/CMC component scores. Otherwise the engine deliberately returns REVIEW."
        )



elif page == "10. MATCH OPTIMIZER":
    st.markdown("## 10. MATCH OPTIMIZER — MODEL IMPROVEMENT")
    st.caption(
        "Goal: maximize called-case direction accuracy without pretending uncertain cases are certain. "
        "REVIEW is an abstention and is excluded from Match %, while Coverage % shows how often the gate actually makes a call."
    )

    opt = prediction_history.copy()
    opt["pdufa_date"] = pd.to_datetime(opt.get("pdufa_date"), errors="coerce")
    opt["Year"] = opt["pdufa_date"].dt.year
    opt["P Value"] = opt.apply(displayed_probability_value, axis=1)
    opt["Actual FDA"] = opt.apply(
        lambda r: normalize_fda_direction(r.get("actual_outcome", r.get("outcome"))), axis=1
    )

    if "count_in_audited_accuracy" in opt:
        audited_ok = opt["count_in_audited_accuracy"].fillna("YES").astype(str).str.upper().eq("YES")
    else:
        audited_ok = pd.Series(True, index=opt.index)

    if "needs_rescore" in opt:
        rescore_ok = ~opt["needs_rescore"].fillna("NO").astype(str).str.upper().eq("YES")
    else:
        rescore_ok = pd.Series(True, index=opt.index)

    opt["Eligible"] = (
        audited_ok &
        rescore_ok &
        opt["P Value"].notna() &
        opt["Actual FDA"].isin(["APPROVED","CRL"]) &
        opt["Year"].notna()
    )

    years = sorted([int(y) for y in opt.loc[opt["Eligible"], "Year"].dropna().unique().tolist()])

    st.markdown("### FDA-V3 decision-safe benchmark")
    if fda_v3_hist_summary:
        strict_summary = load_100_on_100_summary()
        v31,v32,v33,v34,v35,v36,v37 = st.columns(7)
        v31.metric("Review Complete", f"{float(fda_v3_hist_summary.get('review_completion_pct', 0)):.1f}%")
        v32.metric("Strict Match", f"{float(strict_summary.get('historical_accuracy_pct', 0)):.1f}%")
        v33.metric("Strict Coverage", f"{float(strict_summary.get('historical_coverage_pct', 0)):.1f}%")
        v34.metric("Strict Correct Calls", f"{int(strict_summary.get('historical_matches', 0))}/{int(strict_summary.get('historical_qualified', 0))}")
        v35.metric("Strict REVIEW — Analyzed", int(strict_summary.get("historical_review_no_call_analyzed", 0)))
        v36.metric("Broad Decisions Recorded", int(strict_summary.get("historical_broad_assessed", 0)))
        v37.metric("Backfill Remaining", int(fda_v3_hist_summary.get("historical_v3_backfill_remaining", 0)))
        st.caption(
            "Strict qualification includes documented evidence promotions. Every strict REVIEW case has a separate broad PASS/CRL "
            "assessment in Prediction Engine. Strict Match % applies only to the qualified subset. "
            "Retrospective reconstructions are not independent blind predictions."
        )
        with st.expander("FDA-V3 historical backfill queue", expanded=False):
            if fda_v3_hist_queue.empty:
                st.info("No historical V3 backfill queue is loaded.")
            else:
                qcols = [c for c in [
                    "ticker","pdufa_date","actual_outcome","validation_period",
                    "independence_status","v3_backfill_priority","diagnostic_miss_class"
                ] if c in fda_v3_hist_queue.columns]
                grouped_dataframe(
                    fda_v3_hist_queue[qcols].rename(columns={
                        "ticker":"Ticker","pdufa_date":"PDUFA Date","actual_outcome":"Actual FDA",
                        "validation_period":"Validation Period","independence_status":"Validation Role",
                        "v3_backfill_priority":"Priority","diagnostic_miss_class":"Diagnostic Miss Class"
                    }),
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )
    else:
        st.info("FDA-V3 historical benchmark has not been generated yet.")

    st.markdown("### 100% Directional Layer — full-coverage benchmark")
    if fda_directional_summary:
        dc1,dc2,dc3,dc4,dc5,dc6,dc7 = st.columns(7)
        dc1.metric("Historical Coverage", f"{float(fda_directional_summary.get('historical_coverage_pct', 0)):.1f}%")
        hist_acc = fda_directional_summary.get("historical_accuracy_pct")
        dc2.metric("V1.9 Retro Fit", "Pending" if hist_acc is None else f"{float(hist_acc):.2f}%")
        locked_val = fda_directional_summary.get("locked_validation_2024_2026_accuracy_pct")
        dc3.metric("Locked V1.2 Validation", "Pending" if locked_val is None else f"{float(locked_val):.2f}%")
        dc4.metric(
            "Historical Matches",
            f"{int(fda_directional_summary.get('historical_matches', 0))}/{int(fda_directional_summary.get('historical_directional_calls', 0))}"
        )
        dc5.metric("Live Coverage", f"{float(fda_directional_summary.get('live_coverage_pct', 0)):.1f}%")
        dc6.metric("Open Prospective Calls", int(fda_directional_summary.get("open_prospective_counted_calls", 0)))
        pros_acc = fda_directional_summary.get("prospective_accuracy_pct")
        dc7.metric("V1.9 Prospective", "Pending" if pros_acc is None else f"{float(pros_acc):.2f}%")
        st.caption(
            "This layer always issues APPROVED or CRL for every eligible FDA review cycle. "
            "V1.9 Retro Fit is development-only because later historical misses informed the new event-risk rules. "
            "Locked V1.2 Validation remains the last historical holdout result. V1.9 prospective accuracy is scored "
            "only from calls frozen before the FDA outcome is known."
        )
        with st.expander("Residual public-information surprise audit", expanded=False):
            if fda_directional_residual.empty:
                st.info("No residual miss audit is loaded.")
            else:
                ra = fda_directional_residual.copy()
                show_cols = [c for c in [
                    "ticker","pdufa_date","forced_direction","actual_outcome","residual_category",
                    "recoverability","predecision_public_signal","why_not_promoted",
                    "predecision_source","postdecision_audit_source"
                ] if c in ra.columns]
                grouped_dataframe(
                    ra[show_cols].rename(columns={
                        "ticker":"Ticker","pdufa_date":"PDUFA Date","forced_direction":"Forced Direction",
                        "actual_outcome":"Actual FDA","residual_category":"Residual Category",
                        "recoverability":"Public Recoverability","predecision_public_signal":"Predecision Public Signal",
                        "why_not_promoted":"Why Rule Was Not Promoted",
                        "predecision_source":"Predecision Source","postdecision_audit_source":"Postdecision Audit Source"
                    }),
                    use_container_width=True,
                    hide_index=True,
                    height=360,
                    column_config={
                        "Predecision Source": st.column_config.LinkColumn("Predecision Source", display_text="Open"),
                        "Postdecision Audit Source": st.column_config.LinkColumn("Postdecision Audit Source", display_text="Open"),
                    },
                )
                st.caption(
                    "These are the historical misses still left after V1.9. LOW/VERY_LOW means the decisive blocker "
                    "was not sufficiently explicit in public pre-PDUFA evidence to justify another rule without hindsight."
                )
    else:
        st.info("100% directional benchmark has not been generated yet.")

    st.markdown("### STEP 1 — Historical cohorts")
    if years:
        cohort_rows = []
        for yy in years:
            yr_all = opt[opt["Year"] == yy]
            yr_el = yr_all[yr_all["Eligible"]]
            cohort_rows.append({
                "Year": yy,
                "Historical rows": len(yr_all),
                "Optimizer eligible": len(yr_el),
                "Approvals": int((yr_el["Actual FDA"] == "APPROVED").sum()),
                "CRLs": int((yr_el["Actual FDA"] == "CRL").sum()),
            })
        grouped_dataframe(pd.DataFrame(cohort_rows), use_container_width=True, hide_index=True)
    else:
        st.error("No audited historical rows currently have both a probability score and final FDA outcome.")

    if 2023 not in years:
        st.warning(
            "2023 is not loaded into the historical prediction dataset yet. "
            "Preferred validation is: tune on 2023 → lock rules → validate on 2024 → confirm again on 2025."
        )

    if len(years) >= 2:
        default_tune = 2023 if 2023 in years else years[0]
        later_years = [y for y in years if y > default_tune]
        default_holdout = 2024 if default_tune == 2023 and 2024 in years else (later_years[0] if later_years else years[-1])
    elif len(years) == 1:
        default_tune = years[0]
        default_holdout = years[0]
    else:
        default_tune = None
        default_holdout = None

    ctl1,ctl2,ctl3,ctl4 = st.columns(4)
    with ctl1:
        tune_year = st.selectbox(
            "Tune year",
            years if years else [date.today().year],
            index=(years.index(default_tune) if years and default_tune in years else 0),
            key="match_opt_tune_year",
        )
    with ctl2:
        holdout_choices = [y for y in years if y != tune_year] or years or [date.today().year]
        holdout_index = holdout_choices.index(default_holdout) if default_holdout in holdout_choices else 0
        holdout_year = st.selectbox(
            "Holdout year",
            holdout_choices,
            index=holdout_index,
            key="match_opt_holdout_year",
        )
    with ctl3:
        minimum_coverage = st.slider(
            "Minimum coverage",
            min_value=5,
            max_value=90,
            value=30,
            step=5,
            format="%d%%",
            key="match_opt_min_coverage",
        )
    with ctl4:
        max_calls = int(opt[opt["Year"] == tune_year]["Eligible"].sum()) if tune_year is not None else 0
        safe_max_calls = max(1, max_calls)
        minimum_calls = st.number_input(
            "Minimum calls",
            min_value=1,
            max_value=safe_max_calls,
            value=min(5, safe_max_calls),
            step=1,
            key="match_opt_min_calls",
        )

    st.markdown("### STEP 2 — Decision-safe eligibility gate")
    tune = opt[(opt["Year"] == tune_year) & opt["Eligible"]].copy() if tune_year is not None else pd.DataFrame()
    holdout = opt[(opt["Year"] == holdout_year) & opt["Eligible"]].copy() if holdout_year is not None else pd.DataFrame()
    e1,e2,e3,e4 = st.columns(4)
    e1.metric("Tune Eligible", len(tune))
    e2.metric("Holdout Eligible", len(holdout))
    e3.metric("Excluded / Rescore", int((~opt["Eligible"]).sum()))
    e4.metric("Leakage Rule", "PRE-DECISION ONLY")
    st.caption(
        "Rows requiring rescore or lacking a valid final FDA outcome/probability are excluded from optimization. "
        "Thresholds are selected from the tune year only."
    )

    st.markdown("### STEP 3 — Tune the high-confidence F gate")
    best = optimize_match_gate(tune, minimum_coverage_pct=float(minimum_coverage), minimum_calls=int(minimum_calls))
    if best is None:
        st.warning(
            "No threshold pair meets the current minimum coverage/call requirements. "
            "Lower Minimum coverage or Minimum calls, or add more audited historical cases."
        )
    else:
        bm = best["metrics"]
        t1,t2,t3,t4,t5 = st.columns(5)
        t1.metric("Approve ≥", f"{best['approve_min']}%")
        t2.metric("CRL ≤", f"{best['crl_max']}%")
        t3.metric("Tune Match %", f"{bm['match_pct']:.1f}%")
        t4.metric("Tune Coverage %", f"{bm['coverage_pct']:.1f}%")
        t5.metric("Tune Calls", f"{bm['calls']}/{bm['eligible']}")

        st.markdown("### STEP 4 — Analyze every tune-year miss")
        tune_cases = optimizer_case_table(tune, best["approve_min"], best["crl_max"])
        tune_misses = tune_cases[tune_cases["Match %"] == "0%"].copy()
        if tune_misses.empty:
            st.success("No wrong actionable calls under this tune-year gate.")
        else:
            miss_cols = [x for x in [
                "ticker","pdufa_date","P%","Original F","Optimized F","Actual FDA",
                "failure_reason","audit_status","source_url"
            ] if x in tune_misses.columns]
            grouped_dataframe(
                tune_misses[miss_cols].rename(columns={
                    "ticker":"Ticker","pdufa_date":"PDUFA Date",
                    "failure_reason":"Miss / Audit Reason","audit_status":"Audit Status",
                    "source_url":"Audit Source"
                }),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### STEP 5 — Lock thresholds and test the untouched holdout")
        hm = optimizer_metrics(holdout, best["approve_min"], best["crl_max"])
        h1,h2,h3,h4 = st.columns(4)
        h1.metric("Holdout Match %", "" if pd.isna(hm["match_pct"]) else f"{hm['match_pct']:.1f}%")
        h2.metric("Holdout Coverage %", "" if pd.isna(hm["coverage_pct"]) else f"{hm['coverage_pct']:.1f}%")
        h3.metric("Correct Calls", hm["correct"])
        h4.metric("Total Calls", f"{hm['calls']}/{hm['eligible']}")

        if int(holdout_year) == int(date.today().year):
            st.warning(
                f"{holdout_year} is still an in-progress year, so this is a provisional holdout result, not a final full-year validation."
            )

        holdout_cases = optimizer_case_table(holdout, best["approve_min"], best["crl_max"])
        if not holdout_cases.empty:
            holdout_show = holdout_cases[holdout_cases["Optimized F"].isin(["APPROVED","CRL"])].copy()
            show_cols = [x for x in [
                "ticker","pdufa_date","P%","Original F","Optimized F","Actual FDA","Match %"
            ] if x in holdout_show.columns]
            grouped_dataframe(
                holdout_show[show_cols].rename(columns={"ticker":"Ticker","pdufa_date":"PDUFA Date"}),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### STEP 6 — Recommended prospective F gate")
        r1,r2,r3 = st.columns(3)
        r1.metric("APPROVED Gate", f"P% ≥ {best['approve_min']}%")
        r2.metric("CRL Gate", f"P% ≤ {best['crl_max']}%")
        r3.metric("Middle Zone", "REVIEW")
        st.info(
            "Recommended rule: preserve the underlying direction only when its P% clears the locked high-confidence threshold. "
            "Everything between the CRL and APPROVED thresholds becomes REVIEW. "
            "Do not claim 100% prospective accuracy unless the locked rule achieves it on untouched holdout data and continues to do so prospectively."
        )

        if not pd.isna(hm["match_pct"]) and float(hm["match_pct"]) == 100.0:
            st.success(
                f"The locked gate achieved 100% called-case Match on the available {holdout_year} holdout "
                f"at {hm['coverage_pct']:.1f}% coverage ({hm['calls']} calls). This is historical evidence, not a guarantee of future FDA decisions."
            )
        elif not pd.isna(hm["match_pct"]):
            st.caption(
                f"Current locked holdout result: {hm['match_pct']:.1f}% Match at {hm['coverage_pct']:.1f}% Coverage. "
                "Use the year controls to validate the locked gate sequentially: 2023 tune → 2024 validation → 2025 later holdout. Do not retune after viewing a holdout."
            )


elif page == "5. SCANS":
    st.markdown("## 5. SCANS — FIND CHANGES & NEW EVIDENCE")

    # Historical financing scan counter. Prefer the persistent pursuit log when
    # available; otherwise combine the frozen historical universe with the
    # current second-financing audit without inventing historical findings.
    hist_total = int(len(prediction_history))
    live_total = int(len(df))
    financing_total = hist_total + live_total
    verified_second_close = 0
    found_leads = 0
    financing_checked = 0
    financing_last_scan = "Waiting for scan data"
    currently_checking = "Historical financing backlog"

    try:
        pursuit = pd.read_csv("data/financing_pursuit_log.csv", keep_default_na=False)
        if "event_key" in pursuit:
            pursuit = pursuit.drop_duplicates(subset=["event_key"], keep="last")
        status_col = next((x for x in ["status","financing_status","pursuit_status"] if x in pursuit.columns), None)
        if status_col:
            statuses = pursuit[status_col].fillna("").astype(str).str.upper().str.strip()
            verified_second_close = int(statuses.eq("VERIFIED_SECOND_CLOSE").sum())
            found_leads = int(statuses.isin(["FOUND_LEAD","VERIFIED_SECOND_CLOSE"]).sum())
            financing_checked = int(statuses.ne("").sum())
        date_col = next((x for x in ["last_checked_utc","last_checked","verified_as_of"] if x in pursuit.columns), None)
        if date_col and not pursuit.empty:
            dates = pd.to_datetime(pursuit[date_col], errors="coerce", utc=True).dropna()
            if not dates.empty:
                financing_last_scan = dates.max().strftime("%Y-%m-%d %H:%M UTC")
        active_col = next((x for x in ["scan_status","work_status"] if x in pursuit.columns), None)
        if active_col:
            active = pursuit[pursuit[active_col].fillna("").astype(str).str.upper().isin(["RUNNING","IN_PROGRESS"])]
            if not active.empty:
                ar = active.iloc[-1]
                currently_checking = str(ar.get("ticker", "")) or currently_checking
    except Exception:
        # Current live audit is authoritative for already verified closes.
        if "second_financing_audit_status" in df.columns:
            live_status = df["second_financing_audit_status"].fillna("").astype(str).str.upper().str.strip()
            verified_second_close = int(live_status.eq("VERIFIED_SECOND_POST_PHASE3_FINANCING").sum())
            found_leads = verified_second_close
            financing_checked = live_total
        if "verified_as_of" in df.columns:
            dates = pd.to_datetime(df["verified_as_of"], errors="coerce", utc=True).dropna()
            if not dates.empty:
                financing_last_scan = dates.max().strftime("%Y-%m-%d %H:%M UTC")

    financing_left = max(financing_total - found_leads, 0)
    st.markdown("### 🔎 HISTORICAL FINANCING SCAN — LIVE COUNT")
    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("TOTAL PDUFA", f"{financing_total:,}")
    fc2.metric("FOUND LEAD", f"{found_leads:,}")
    fc3.metric("VERIFIED 2ND CLOSE", f"{verified_second_close:,}")
    fc4.metric("LEFT", f"{financing_left:,}")
    st.markdown(
        f"""<div class="card"><b>Scan status:</b> ACTIVE &nbsp; | &nbsp;
        <b>Reviewed/classified:</b> {financing_checked:,}/{financing_total:,} &nbsp; | &nbsp;
        <b>Last evidence update:</b> {html.escape(financing_last_scan)} &nbsp; | &nbsp;
        <b>Currently checking:</b> {html.escape(currently_checking)}</div>""",
        unsafe_allow_html=True,
    )
    st.caption("FOUND LEAD = a credible financing notice was discovered. VERIFIED 2ND CLOSE = the second distinct post–Phase-3 financing has reliable closing/funding evidence. LEFT is based on records without a found lead.")


    st.caption("Variable PDUFA-relative Gantt chart for the scan families currently used by the command center. Change the horizon and each scan window below; Day 0 is the PDUFA decision date.")

    gantt_defs = [
        ("Company / Event Discovery", -180, 0, "Universe"),
        ("Phase 3 / P-value", -180, -30, "Clinical"),
        ("2nd Financing Confirmation", -180, -14, "Financing"),
        ("Cash Runway", -120, -14, "Financial"),
        ("Market Data / Momentum / Volume", -90, -1, "Trading"),
        ("Ownership / Insiders", -90, -7, "Ownership"),
        ("PDUFA Date / FDA Confirmation", -90, 0, "Regulatory"),
        ("Probability of Approval — Public", -90, -1, "Prediction"),
        ("Probability of Approval — All Sources", -90, -1, "Prediction"),
        ("FDA Result / Outcome", 0, 7, "Regulatory"),
    ]
    g1, g2 = st.columns(2)
    with g1:
        horizon_start = int(st.number_input("Gantt start (days before PDUFA)", min_value=1, max_value=730, value=180, step=1, key="scan_gantt_before"))
    with g2:
        horizon_end = int(st.number_input("Gantt end (days after PDUFA)", min_value=0, max_value=90, value=7, step=1, key="scan_gantt_after"))

    gantt_rows = []
    with st.expander("Adjust individual scan windows"):
        for idx, (scan_name, default_start, default_end, group) in enumerate(gantt_defs):
            c1, c2, c3 = st.columns([2.5,1,1])
            c1.markdown(f"**{scan_name}**")
            start_val = int(c2.number_input("Start day", min_value=-730, max_value=90, value=default_start, step=1, key=f"gantt_start_{idx}", label_visibility="collapsed"))
            end_val = int(c3.number_input("End day", min_value=-730, max_value=90, value=default_end, step=1, key=f"gantt_end_{idx}", label_visibility="collapsed"))
            if start_val > end_val:
                start_val, end_val = end_val, start_val
            gantt_rows.append({"Scan":scan_name, "Start":start_val, "End":end_val, "Group":group})
    if not gantt_rows:
        gantt_rows = [{"Scan":n,"Start":a,"End":b,"Group":g} for n,a,b,g in gantt_defs]
    else:
        # rows are populated only when the expander body executes; keep defaults as a defensive fallback
        known = {r["Scan"] for r in gantt_rows}
        gantt_rows += [{"Scan":n,"Start":a,"End":b,"Group":g} for n,a,b,g in gantt_defs if n not in known]

    gantt_df = pd.DataFrame(gantt_rows)
    gantt_df["Start"] = gantt_df["Start"].clip(lower=-horizon_start, upper=horizon_end)
    gantt_df["End"] = gantt_df["End"].clip(lower=-horizon_start, upper=horizon_end)
    gantt_df = gantt_df[gantt_df["End"] >= gantt_df["Start"]].copy()
    st.vega_lite_chart(
        gantt_df,
        {
            "height": 420,
            "mark": {"type":"bar","cornerRadius":4},
            "encoding": {
                "y": {"field":"Scan","type":"nominal","sort":None,"title":None},
                "x": {"field":"Start","type":"quantitative","title":"Days relative to PDUFA (Day 0 = decision)","scale":{"domain":[-horizon_start,horizon_end]}},
                "x2": {"field":"End"},
                "tooltip": [
                    {"field":"Scan","type":"nominal"},
                    {"field":"Group","type":"nominal"},
                    {"field":"Start","type":"quantitative","title":"Start day"},
                    {"field":"End","type":"quantitative","title":"End day"}
                ]
            }
        },
        use_container_width=True,
    )
    st.caption("The Gantt is a planning/control view: it shows when each scan should be active relative to PDUFA. Changing a window changes this view only; it does not silently alter scheduled cloud jobs.")

    st.divider()
    st.markdown("### MANUAL ACTION CENTER")
    st.caption("One-click controls: pressing a button selects that scope and immediately triggers its matching action. No second Run/Submit step.")
    st.info("Today = PDUFA events due today. Week = today through the next 7 days. All = all active/future PDUFA events currently loaded.")

    left, right = st.columns(2)

    with left:
        st.markdown("### RESCAN INPUTS")
        st.caption("Refresh the deployed input dataset/cache for the selected scope.")
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("▶ RUN TODAY", key="scan_inputs_today_btn", use_container_width=True):
                frame, req = scan_inputs_today()
                st.session_state.scan_preview = frame
        with a2:
            if st.button("▶ RUN WEEK", key="scan_inputs_week_btn", use_container_width=True):
                frame, req = scan_inputs_week()
                st.session_state.scan_preview = frame
        with a3:
            if st.button("▶ RUN ALL", key="scan_inputs_all_btn", use_container_width=True):
                frame, req = scan_inputs_all()
                st.session_state.scan_preview = frame

        st.caption("Script mapping: scan_inputs_today() · scan_inputs_week() · scan_inputs_all()")

    with right:
        st.markdown("### PROBABILITY OF APPROVAL")
        st.caption("Refresh the prediction cache and recompute displayed approval outputs for the selected scope.")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("▶ RUN TODAY", key="scan_approval_today_btn", use_container_width=True):
                frame, req = scan_approval_today()
                st.session_state.scan_preview = frame
        with b2:
            if st.button("▶ RUN WEEK", key="scan_approval_week_btn", use_container_width=True):
                frame, req = scan_approval_week()
                st.session_state.scan_preview = frame
        with b3:
            if st.button("▶ RUN ALL", key="scan_approval_all_btn", use_container_width=True):
                frame, req = scan_approval_all()
                st.session_state.scan_preview = frame

        st.caption("Script mapping: scan_approval_today() · scan_approval_week() · scan_approval_all()")

    req = st.session_state.get("scan_request")
    if req:
        st.success(
            f"Triggered: {req['action']} · {req['scope']} · "
            f"{req['candidate_count']} candidate(s) · {req['requested_at']}"
        )

    preview = st.session_state.get("scan_preview")
    if isinstance(preview, pd.DataFrame):
        if preview.empty:
            st.info("No active PDUFA candidates match this scope.")
        else:
            view = preview.copy()
            view["PDUFA Date"] = pd.to_datetime(view["pdufa_date"], errors="coerce").dt.strftime("%Y-%m-%d")
            view["Probability of Approval % — Public"] = view["public_approval_probability"].apply(
                lambda v: fmt_app_pct(v, 1)
            )
            view["Probability of Approval % — All Sources"] = view.apply(
                lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1
            )
            show_cols = [
                "ticker","PDUFA Date","company","drug",
                "Probability of Approval % — Public",
                "Probability of Approval % — All Sources"
            ]
            grouped_dataframe(
                view[show_cols].rename(columns={
                    "ticker":"Ticker","company":"Company","drug":"Drug"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.warning(
        "These Streamlit buttons now trigger the matching app.py functions immediately. "
        "They refresh/recompute from the dataset available to the deployed app. "
        "A deep public-source rescan (FDA/SEC/ClinicalTrials.gov) still requires the external cloud scan worker; "
        "the Streamlit app does not currently have an authenticated Google Sheets/Apps Script write connection."
    )

    if st.session_state.get("scan_log"):
        st.markdown("### Session Scan Log")
        grouped_dataframe(pd.DataFrame(st.session_state.scan_log), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("### AMENDMENTS / DETAILS FOUND")
    st.caption("Results from the latest SCAN action are shown here at the bottom of the page. Changed or newly detected values are listed first; unchanged rows are not presented as amendments.")

    result_rows = []
    preview = st.session_state.get("scan_preview")
    req = st.session_state.get("scan_request")
    if isinstance(preview, pd.DataFrame) and req:
        for _, rr in preview.iterrows():
            p_public = fmt_app_pct(rr.get("public_approval_probability"), 1)
            p_all = fmt_app_pct(all_source_probability_value(rr), 1)
            result_rows.append({
                "Ticker": safe_text(rr.get("ticker"), ""),
                "PDUFA Date": "Not available" if pd.isna(rr.get("pdufa_date")) else pd.Timestamp(rr.get("pdufa_date")).strftime("%Y-%m-%d"),
                "Company": safe_text(rr.get("company"), ""),
                "Drug": safe_text(rr.get("drug"), ""),
                "Action": req.get("action", ""),
                "Scope": req.get("scope", ""),
                "Public App %": p_public,
                "All Sources App %": p_all,
                "Direction": direction_fda_display(rr),
                "PDUFA Status": safe_text(rr.get("pdufa_confirmation"), "Not available"),
                "Phase 3": safe_text(rr.get("phase3_status"), "Not available"),
                "Financing": safe_text(rr.get("financing_status"), "Not available"),
                "Check Status": safe_text(rr.get("check_status"), "Not available"),
                "Last Checked": safe_text(rr.get("last_checked"), "Not available"),
            })

    amendments = st.session_state.get("scan_amendments", [])
    if amendments:
        st.success(f"{len(amendments)} amendment/detail change(s) detected in this session.")
        grouped_dataframe(pd.DataFrame(amendments), use_container_width=True, hide_index=True)
    elif result_rows:
        st.info("Latest scan results are shown below. No separate change-detection baseline is available yet, so these are current details rather than confirmed amendments.")
        grouped_dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No scan results yet. Run one of the six SCAN buttons above.")


elif page == "6. RECHECK":
    st.markdown("## 6. RECHECK — VERIFY QUESTIONABLE EVIDENCE")
    st.caption(
        "Recheck is locked to the exact event_key. It never substitutes another company's event. "
        "The six categories are PDUFA/FDA, Phase 3/p-value, financing closure, cash runway, market data, and ownership/insiders."
    )

    lookup = st.text_input("Ticker lookup", value="", placeholder="Example: SRRK or CABA", key="recheck_ticker_lookup").strip().upper()
    lookup_rows = df[df["ticker"].fillna("").astype(str).str.upper().eq(lookup)].copy() if lookup else pd.DataFrame()
    if lookup and lookup_rows.empty:
        st.warning(f"{lookup} has no current PDUFA event in the saved event feed. No other ticker/event will be substituted.")

    event_rows = lookup_rows if lookup and not lookup_rows.empty else df.copy()
    event_rows = event_rows.sort_values(["pdufa_date","ticker"], na_position="last")
    event_keys = event_rows["event_key"].astype(str).tolist()
    if not event_keys:
        st.info("No PDUFA events are available to recheck.")
    else:
        current_key = str(st.session_state.get("selected_event_key",""))
        default_idx = event_keys.index(current_key) if current_key in event_keys else 0
        selected_recheck_key = st.selectbox(
            "Exact PDUFA event",
            event_keys,
            index=default_idx,
            format_func=lambda k: (
                f"{event_rows.loc[event_rows['event_key'].astype(str).eq(k), 'ticker'].iloc[0]} · "
                f"{safe_text(event_rows.loc[event_rows['event_key'].astype(str).eq(k), 'drug'].iloc[0])} · "
                f"{safe_text(event_rows.loc[event_rows['event_key'].astype(str).eq(k), 'pdufa_date'].iloc[0])}"
            ),
            key="recheck_event_key",
        )
        selected_row = event_rows[event_rows["event_key"].astype(str).eq(selected_recheck_key)].iloc[0]
        st.code(selected_recheck_key, language=None)
        st.caption(
            f"Locked target: {safe_text(selected_row.get('ticker'))} · "
            f"{safe_text(selected_row.get('drug'))} · "
            f"{safe_text(selected_row.get('pdufa_date'))}"
        )

        st.markdown("### Six recheck categories")
        q1,q2,q3 = st.columns(3)
        q4,q5,q6 = st.columns(3)
        checks = {
            "pdufa_date": q1.checkbox("PDUFA date / FDA decision", value=True, key="recheck_c1"),
            "phase3": q2.checkbox("Phase 3 results / p-value", value=True, key="recheck_c2"),
            "financing": q3.checkbox("Financing closure", value=True, key="recheck_c3"),
            "cash_runway": q4.checkbox("Cash runway", value=True, key="recheck_c4"),
            "market_data": q5.checkbox("Market data", value=True, key="recheck_c5"),
            "ownership_insiders": q6.checkbox("Options / ownership / insiders", value=True, key="recheck_c6"),
        }
        chosen = [k for k,v in checks.items() if v]

        b1,b2 = st.columns(2)
        with b1:
            if st.button("▶ RUN RECHECK — SELECTED EVENT", use_container_width=True, disabled=not chosen):
                with st.spinner("Running exact-event public-source recheck..."):
                    try:
                        st.session_state.recheck_last_result = run_recheck_worker(
                            event_key=selected_recheck_key, categories=chosen
                        )
                        st.session_state.selected_event_key = selected_recheck_key
                        st.session_state.recheck_last_error = ""
                    except Exception as exc:
                        st.session_state.recheck_last_error = str(exc)
                st.rerun()
        with b2:
            if st.button("▶ RUN RECHECK — ALL EVENTS", use_container_width=True, disabled=not chosen):
                with st.spinner("Running all-event public-source recheck..."):
                    try:
                        st.session_state.recheck_last_result = run_recheck_worker(
                            run_all=True, categories=chosen
                        )
                        st.session_state.recheck_last_error = ""
                    except Exception as exc:
                        st.session_state.recheck_last_error = str(exc)
                st.rerun()

    if st.session_state.get("recheck_last_error"):
        st.error(st.session_state.recheck_last_error)
    elif st.session_state.get("recheck_last_result"):
        st.success(st.session_state.recheck_last_result)

    rs = load_recheck_status()
    if not rs.empty:
        completed = rs[rs["last_successful_recheck_utc"].astype(str).str.strip().ne("")]
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Tracked Events", len(rs))
        r2.metric("Completed Successfully", len(completed))
        r3.metric("With Errors", int(rs["run_status"].astype(str).str.contains("ERROR", case=False, na=False).sum()))
        latest = completed["last_successful_recheck_utc"].max() if not completed.empty else "Not run"
        r4.metric("Last Successful Recheck", latest)

        target_key = str(st.session_state.get("recheck_event_key", st.session_state.get("selected_event_key","")))
        one = rs[rs["event_key"].astype(str).eq(target_key)]
        if not one.empty:
            rr = one.iloc[0]
            st.markdown("### Selected event recheck results")
            rows = []
            labels = {
                "pdufa_date":"PDUFA date / FDA decision",
                "phase3":"Phase 3 results / p-value",
                "financing":"Financing closure",
                "cash_runway":"Cash runway",
                "market_data":"Market data",
                "ownership_insiders":"Options / ownership / insiders",
            }
            for cat,label in labels.items():
                rows.append({
                    "Category": label,
                    "Status": safe_text(rr.get(cat+"_status"), "Not run"),
                    "Details": safe_text(rr.get(cat+"_note"), "Not run"),
                    "Source": safe_text(rr.get(cat+"_source"), ""),
                })
            grouped_dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
                column_config={"Source": st.column_config.LinkColumn("Source", display_text="Open source")}
            )
            st.caption(
                f"Run status: {safe_text(rr.get('run_status'),'Not run')} · "
                f"Last success: {safe_text(rr.get('last_successful_recheck_utc'),'Not run')} · "
                f"Field changes: {safe_text(rr.get('change_count'),'0')} · "
                f"Errors: {safe_text(rr.get('error_count'),'0')}"
            )

    st.info(
        "Persistence: the same worker is scheduled in GitHub every day at 10 PM Pacific. "
        "The workflow uses two UTC cron entries with a Pacific-time gate so daylight-saving changes do not shift the intended local run time."
    )


elif page == "11. PLAN":
    st.markdown("## 11. PLAN — SYSTEM RULES & OPERATING RHYTHM")
    st.caption(
        "Editable operating and development plan for SwiftLook. Add, delete, reprioritize, or change rows as the platform evolves. "
        "This plan is kept separate from prediction history so editing the roadmap cannot alter frozen FDA calls."
    )

    plan_path = Path("data/swiftlook_plan.csv")
    plan_columns = ["order","area","task","cadence","priority","status","next_action","notes"]
    try:
        plan_df = pd.read_csv(plan_path, keep_default_na=False)
    except Exception:
        plan_df = pd.DataFrame(columns=plan_columns)

    for col in plan_columns:
        if col not in plan_df:
            plan_df[col] = ""
    plan_df = plan_df[plan_columns].copy()
    plan_df["order"] = pd.to_numeric(plan_df["order"], errors="coerce")

    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Plan Items", len(plan_df))
    p2.metric("Active", int(plan_df["status"].astype(str).str.upper().eq("ACTIVE").sum()))
    p3.metric("Next", int(plan_df["status"].astype(str).str.upper().eq("NEXT").sum()))
    p4.metric("Done", int(plan_df["status"].astype(str).str.upper().eq("DONE").sum()))

    st.markdown("### Edit plan")
    edited_plan = grouped_editor(
        plan_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="swiftlook_plan_editor",
        column_config={
            "order": st.column_config.NumberColumn("Order", min_value=1, step=1),
            "area": st.column_config.TextColumn("Area"),
            "task": st.column_config.TextColumn("Task", width="large"),
            "cadence": st.column_config.TextColumn("Cadence"),
            "priority": st.column_config.SelectboxColumn(
                "Priority", options=["HIGH","MEDIUM","LOW"], required=False
            ),
            "status": st.column_config.SelectboxColumn(
                "Status", options=["ACTIVE","NEXT","PLANNED","HOLD","DONE"], required=False
            ),
            "next_action": st.column_config.TextColumn("Next Action", width="large"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )

    save_col, download_col = st.columns([1,1])
    with save_col:
        if st.button("SAVE PLAN CHANGES", use_container_width=True, key="save_swiftlook_plan"):
            try:
                saved = edited_plan.copy()
                for col in plan_columns:
                    if col not in saved:
                        saved[col] = ""
                saved = saved[plan_columns]
                saved["order"] = pd.to_numeric(saved["order"], errors="coerce")
                saved = saved.sort_values("order", na_position="last").reset_index(drop=True)
                saved.to_csv(plan_path, index=False)
                st.success("SwiftLook plan saved in the running app.")
            except Exception as exc:
                st.error(f"Plan save failed: {exc}")

    with download_col:
        st.download_button(
            "DOWNLOAD PLAN BACKUP (.CSV)",
            data=edited_plan.to_csv(index=False).encode("utf-8"),
            file_name="swiftlook_plan.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_swiftlook_plan",
        )

    st.info(
        "The repository copy is the durable baseline. In-app saves update the running Streamlit filesystem; "
        "a Streamlit restart/redeploy can restore the repository version, so use the CSV backup for any important manual edits."
    )

    st.markdown("### Operating rhythm")
    rhythm = pd.DataFrame([
        {"When":"Daily · 5:15 AM Pacific","Purpose":"New-company/PDUFA discovery + tracked-event recheck + Strict/Broad refresh"},
        {"When":"Sunday · 4:00 AM Pacific","Purpose":"Deep review of every PDUFA due in the next 7 days"},
        {"When":"1st of month · 4:30 AM Pacific","Purpose":"Full universe reconciliation + catch-up scan + full recheck"},
        {"When":"Material event","Purpose":"Reassess FDA evidence and create a new prediction version when warranted"},
        {"When":"FDA decision","Purpose":"Score frozen prediction as MATCH or MISS without rewriting history"},
    ])
    grouped_dataframe(rhythm, use_container_width=True, hide_index=True)


elif page == "4. DECISION":
    st.markdown("## 4. DECISION — FDA OUTCOMES & REVIEW")
    st.caption(
        "Scroll year by year, then month by month. The archive uses the verified FDA decision date when it is stored; "
        "otherwise it uses the canonical PDUFA date. Click any PDUFA below to open the full research/audit record."
    )

    with st.expander("📱 INSTALL DECISION ON IPHONE", expanded=False):
        st.markdown(
            "**Safari → Page Menu / Share → Add to Home Screen → turn on Open as Web App → Add.**  "
            "It will launch from an iPhone Home Screen icon like an app."
        )

    # Historical decisions already researched by the Prediction Engine / FDA-V3.
    archive_hist = prediction_history.copy()
    if not archive_hist.empty:
        archive_hist["event_key"] = archive_hist["event_key"].astype(str)
        archive_hist["_source"] = "history"
        archive_hist["Actual FDA"] = archive_hist["actual_outcome"].apply(
            lambda v: normalize_fda_direction(v) or safe_text(v, "")
        )
        archive_hist["_canonical_date"] = pd.to_datetime(
            archive_hist.get("canonical_pdufa_date"), errors="coerce"
        )
        archive_hist["_pdufa_date"] = pd.to_datetime(archive_hist.get("pdufa_date"), errors="coerce")
        archive_hist["Archive Date"] = archive_hist["_canonical_date"].fillna(archive_hist["_pdufa_date"])
        archive_hist["PDUFA Date"] = archive_hist["_canonical_date"].fillna(archive_hist["_pdufa_date"])
        archive_hist["Decision Date"] = pd.NaT
        archive_hist["Drug / Program"] = archive_hist["event_key"].apply(
            lambda k: (
                str(k).split("|", 2)[2].replace("-", " ")
                if len(str(k).split("|", 2)) >= 3
                else ""
            )
        )
        archive_hist["Indication"] = ""
        archive_hist["Stored P%"] = pd.to_numeric(archive_hist.get("p_approval"), errors="coerce") * 100.0

        if not fda_v3_hist_backtest.empty:
            v3 = fda_v3_hist_backtest.copy()
            v3["event_key"] = v3["event_key"].astype(str)
            v3_keep = [
                "event_key","v3_phase_a_status","v3_phase_a_match",
                "v3_reconstructed_call","v3_reconstructed_match","v3_review_status",
                "diagnostic_miss_class","v3_evidence_summary","v3_source_urls",
                "v3_last_reviewed"
            ]
            for col in v3_keep:
                if col not in v3:
                    v3[col] = ""
            archive_hist = archive_hist.merge(
                v3[v3_keep].drop_duplicates("event_key", keep="last"),
                on="event_key",
                how="left",
                validate="one_to_one"
            )

        def _archive_hist_call(r):
            phase = safe_text(r.get("v3_phase_a_status"), "")
            public_call = safe_text(r.get("public_model_class"), "").upper()
            reconstructed = safe_text(r.get("v3_reconstructed_call"), "").upper()
            if phase == "DIRECTIONAL_CALL" and public_call in ["APPROVED","CRL"]:
                return public_call
            if reconstructed in ["APPROVED","CRL","REVIEW"]:
                return reconstructed
            if public_call == "REVIEW":
                return "REVIEW"
            return "REVIEW"

        def _archive_hist_match(r):
            phase = safe_text(r.get("v3_phase_a_status"), "")
            if phase == "DIRECTIONAL_CALL":
                return safe_text(r.get("v3_phase_a_match"), "")
            return safe_text(r.get("v3_reconstructed_match"), "NO_CALL")

        archive_hist["FDA-V3 Call"] = archive_hist.apply(_archive_hist_call, axis=1)
        archive_hist["FDA-V3 Match"] = archive_hist.apply(_archive_hist_match, axis=1)
        archive_hist["Review Status"] = archive_hist.get(
            "v3_review_status", pd.Series(index=archive_hist.index, dtype="object")
        ).fillna("")

        hist_cols = [
            "event_key","ticker","Drug / Program","Indication","Archive Date","PDUFA Date",
            "Decision Date","Actual FDA","FDA-V3 Call","FDA-V3 Match","Review Status",
            "Stored P%","_source"
        ]
        for col in hist_cols:
            if col not in archive_hist:
                archive_hist[col] = ""
        archive_hist = archive_hist[hist_cols]
    else:
        archive_hist = pd.DataFrame()

    # Include verified decisions from the current live event feed that are not already
    # represented in the historical cohort.
    archive_live = df.copy()
    if not archive_live.empty:
        archive_live["Actual FDA"] = archive_live.apply(resolved_fda_direction, axis=1)
        archive_live = archive_live[archive_live["Actual FDA"].isin(["APPROVED","CRL"])].copy()
        archive_live["_source"] = "live"
        archive_live["Decision Date"] = pd.to_datetime(
            archive_live.get("decision_date"), errors="coerce"
        )
        archive_live["PDUFA Date"] = pd.to_datetime(
            archive_live.get("pdufa_date"), errors="coerce"
        )
        archive_live["Archive Date"] = archive_live["Decision Date"].fillna(archive_live["PDUFA Date"])
        archive_live["Drug / Program"] = archive_live.get(
            "drug", pd.Series(index=archive_live.index, dtype="object")
        ).fillna("")
        archive_live["Indication"] = archive_live.get(
            "indication", pd.Series(index=archive_live.index, dtype="object")
        ).fillna("")
        archive_live["FDA-V3 Call"] = archive_live.get(
            "fda_prediction", pd.Series(index=archive_live.index, dtype="object")
        ).apply(lambda v: safe_text(v, "REVIEW"))
        archive_live["FDA-V3 Match"] = archive_live.get(
            "fda_match_result", pd.Series(index=archive_live.index, dtype="object")
        ).apply(lambda v: safe_text(v, "PENDING"))
        archive_live["Review Status"] = archive_live.get(
            "fda_hard_gate", pd.Series(index=archive_live.index, dtype="object")
        ).apply(lambda v: safe_text(v, "REVIEW"))
        archive_live["Stored P%"] = archive_live.apply(
            lambda r: displayed_probability_value(r), axis=1
        )
        live_cols = [
            "event_key","ticker","Drug / Program","Indication","Archive Date","PDUFA Date",
            "Decision Date","Actual FDA","FDA-V3 Call","FDA-V3 Match","Review Status",
            "Stored P%","_source"
        ]
        for col in live_cols:
            if col not in archive_live:
                archive_live[col] = ""
        archive_live = archive_live[live_cols]

    if not archive_hist.empty and not archive_live.empty:
        hist_keys = set(archive_hist["event_key"].astype(str))
        archive_live = archive_live[
            ~archive_live["event_key"].astype(str).isin(hist_keys)
        ].copy()

    archive = pd.concat([archive_hist, archive_live], ignore_index=True)
    archive["Assessed Call"] = archive.apply(
        lambda r: historical_assessed_by_key.get(str(r.get("event_key")), {}).get("assessed_direction", r.get("FDA-V3 Call")), axis=1
    )
    archive["Assessed Match"] = archive.apply(
        lambda r: historical_assessed_by_key.get(str(r.get("event_key")), {}).get("match_result", r.get("FDA-V3 Match")), axis=1
    )
    archive["Strict Status"] = archive.apply(
        lambda r: historical_assessed_by_key.get(str(r.get("event_key")), {}).get("strict_status", r.get("Review Status")), axis=1
    ).replace({"REVIEW_NO_CALL_ANALYZED": "REVIEW — ANALYZED"})
    archive["Archive Date"] = pd.to_datetime(archive["Archive Date"], errors="coerce")
    archive["PDUFA Date"] = pd.to_datetime(archive["PDUFA Date"], errors="coerce")
    archive["Decision Date"] = pd.to_datetime(archive["Decision Date"], errors="coerce")
    archive = archive[
        archive["Archive Date"].notna() &
        archive["Actual FDA"].isin(["APPROVED","CRL"])
    ].copy()

    if archive.empty:
        st.info("No resolved PDUFA decisions are loaded into the archive yet.")
    else:
        archive["Year"] = archive["Archive Date"].dt.year.astype(int)
        archive["Month"] = archive["Archive Date"].dt.month.astype(int)
        years = sorted(archive["Year"].unique().tolist())
        default_year = max(years)

        selected_year = st.select_slider(
            "Year scroller",
            options=years,
            value=default_year,
            key="decision_archive_year"
        )
        year_rows = archive[archive["Year"].eq(int(selected_year))].copy()

        # Rolling month-by-month result table for the selected year.
        monthly_rows = []
        for month_num in range(1, 13):
            m = year_rows[year_rows["Month"].eq(month_num)]
            directional = m[m["Assessed Call"].isin(["APPROVED","CRL"])]
            matched = directional["Assessed Match"].astype(str).str.upper().eq("MATCH").sum()
            monthly_rows.append({
                "Month": calendar.month_abbr[month_num],
                "PDUFAs": int(len(m)),
                "FDA Approved": int(m["Actual FDA"].eq("APPROVED").sum()),
                "FDA CRL": int(m["Actual FDA"].eq("CRL").sum()),
                "Assessed Calls": int(len(directional)),
                "Assessed Correct": int(matched),
                "Assessed Match %": (
                    "" if len(directional) == 0 else f"{100.0 * matched / len(directional):.1f}%"
                ),
                "Strict REVIEW (Analyzed)": int(m["Strict Status"].eq("REVIEW — ANALYZED").sum()),
            })

        y1,y2,y3,y4,y5 = st.columns(5)
        y1.metric("Year", int(selected_year))
        y2.metric("PDUFA Decisions", len(year_rows))
        y3.metric("FDA Approved", int(year_rows["Actual FDA"].eq("APPROVED").sum()))
        y4.metric("FDA CRL", int(year_rows["Actual FDA"].eq("CRL").sum()))
        yr_directional = year_rows[year_rows["Assessed Call"].isin(["APPROVED","CRL"])]
        yr_correct = int(yr_directional["Assessed Match"].astype(str).str.upper().eq("MATCH").sum())
        y5.metric(
            "Assessed Match",
            "—" if len(yr_directional) == 0 else f"{100.0 * yr_correct / len(yr_directional):.1f}%"
        )

        st.markdown("### Month-by-month result")
        st.caption("Recorded model assessments are shown alongside the FDA outcomes. Historical matches are retrospective development results; strict qualification is shown separately.")
        grouped_dataframe(
            pd.DataFrame(monthly_rows),
            use_container_width=True,
            hide_index=True,
        )

        month_counts = year_rows["Month"].value_counts().to_dict()
        months = list(range(1, 13))
        default_month = max(year_rows["Month"].tolist()) if not year_rows.empty else 1
        selected_month = st.select_slider(
            "Month scroller",
            options=months,
            value=int(default_month),
            format_func=lambda m: f"{calendar.month_abbr[m]} ({int(month_counts.get(m, 0))})",
            key="decision_archive_month"
        )

        month_rows = year_rows[year_rows["Month"].eq(int(selected_month))].copy()
        month_rows = month_rows.sort_values(["Archive Date","ticker","event_key"])

        st.markdown(
            f"### {calendar.month_name[int(selected_month)]} {int(selected_year)} — "
            f"{len(month_rows)} PDUFA decision{'s' if len(month_rows) != 1 else ''}"
        )

        if month_rows.empty:
            st.info("No resolved PDUFA decisions in this month.")
        else:
            for _, ar in month_rows.iterrows():
                pdate = (
                    "NA" if pd.isna(ar.get("PDUFA Date"))
                    else pd.Timestamp(ar.get("PDUFA Date")).strftime("%b %d, %Y")
                )
                ddate = (
                    "Not separately stored" if pd.isna(ar.get("Decision Date"))
                    else pd.Timestamp(ar.get("Decision Date")).strftime("%b %d, %Y")
                )
                call = safe_text(ar.get("Assessed Call"), "REVIEW")
                match = safe_text(ar.get("Assessed Match"), "NO_CALL")
                drug = safe_text(ar.get("Drug / Program"), "")
                with st.container(border=True):
                    c1,c2,c3,c4,c5 = st.columns([1.2,2.0,1.1,1.1,1.2])
                    c1.markdown(f"**{safe_text(ar.get('ticker'))}**")
                    c2.markdown(f"**{drug or 'PDUFA event'}**")
                    c3.markdown(f"FDA: **{safe_text(ar.get('Actual FDA'))}**")
                    c4.markdown(f"Suggestion: **{'PASS' if call == 'APPROVED' else call}**")
                    c5.markdown(f"Match: **{match}**")
                    st.caption(f"PDUFA: {pdate} · Decision date: {ddate} · Event: {safe_text(ar.get('event_key'))}")
                    st.caption(f"Strict status: {safe_text(ar.get('Strict Status'))}")
                    if st.button(
                        f"OPEN FULL PDUFA DATA — {safe_text(ar.get('ticker'))}",
                        key="archive_open_" + re.sub(r"[^A-Za-z0-9_]+", "_", safe_text(ar.get("event_key"))),
                        use_container_width=True,
                    ):
                        go_individual(
                            ticker=safe_text(ar.get("ticker")),
                            event_key=safe_text(ar.get("event_key")),
                            source=safe_text(ar.get("_source"), "history"),
                            return_page="4. DECISION",
                        )
                        st.rerun()


else:
    if st.session_state.selected_detail_source == "history":
        hmatches = prediction_history[
            prediction_history["event_key"].astype(str) == str(st.session_state.selected_event_key)
        ]
        if hmatches.empty:
            st.error("Historical PDUFA event not found in the loaded prediction cohort.")
            if st.button("← PREDICTION ENGINE", use_container_width=True):
                go_page("9. PREDICTION ENGINE")
                st.rerun()
            st.stop()

        hr = hmatches.iloc[0]
        app_text = fmt_app_pct(hr.get("p_approval"), 1)
        hdate = "NA" if pd.isna(hr.get("pdufa_date")) else pd.Timestamp(hr.get("pdufa_date")).strftime("%b %d, %Y")
        hcap = "NA" if pd.isna(hr.get("historical_market_cap_billions")) else f"${float(hr.get('historical_market_cap_billions')):.2f}B"
        correct_text = "Correct" if str(hr.get("correct")).lower() == "true" else "Wrong" if str(hr.get("correct")).lower() == "false" else "NA"

        b1,b2 = st.columns([1,5])
        with b1:
            if st.button("← PREDICTION ENGINE", use_container_width=True):
                go_page(st.session_state.detail_return_page or "9. PREDICTION ENGINE")
                st.rerun()
        with b2:
            st.caption("Historical Prediction Engine event detail")

        st.markdown(f"## {safe_text(hr.get('ticker'))} — Historical PDUFA")
        st.caption(f"Event key: {safe_text(hr.get('event_key'))}")

        assessment = historical_assessed_by_key.get(str(hr.get("event_key")), {})
        if assessment:
            st.markdown("### Recorded assessment")
            ad1,ad2,ad3,ad4 = st.columns(4)
            assessed_call = assessment["assessed_direction"]
            ad1.metric("SUGGESTION", "PASS" if assessed_call == "APPROVED" else "CRL")
            ad2.metric("Decision basis", assessment["assessment_basis"])
            ad3.metric("Historical match", assessment["match_result"])
            ad4.metric("Strict qualification", "QUALIFIED" if assessment["assessment_basis"] == "STRICT" else "REVIEW — ANALYZED")
            st.write(f"**Decision reason:** {assessment['decision_reason']}")
            st.write(f"**Strict evidence status:** {assessment['strict_reason']}")
            st.caption("This recorded assessment is retrospective. The original probability and prediction below remain available for comparison.")
            if assessment.get("source_urls"):
                for i, url in enumerate(assessment["source_urls"].split("|")):
                    if url.strip():
                        st.link_button(f"OPEN ASSESSMENT SOURCE {i+1}", url.strip())

        public_hist = hr.get("public_approval_probability", pd.NA)
        public_hist_text = fmt_app_pct(public_hist, 1)
        all_hist_text = fmt_app_pct(all_source_probability_value(hr), 1)
        a1,a2,a3,a4,a5,a6 = st.columns(6)
        a1.metric("P%", displayed_probability_text(hr, 1), help="Stored Probability of Approval; blank when no score exists")
        a2.metric("F", direction_fda_display(hr), help="FDA direction")
        a3.metric("C", combined_probability_direction(hr), help="Combined P% + FDA direction")
        a4.metric("PDUFA Date", hdate)
        a5.metric("Actual FDA", safe_text(hr.get("actual_outcome"), "NA"))
        a6.metric("Historical Cap", hcap)

        v3match = fda_v3_hist_backtest[
            fda_v3_hist_backtest["event_key"].astype(str).eq(str(hr.get("event_key")))
        ] if not fda_v3_hist_backtest.empty and "event_key" in fda_v3_hist_backtest else pd.DataFrame()

        if not v3match.empty:
            vr = v3match.iloc[-1]
            phase_status = safe_text(vr.get("v3_phase_a_status"), "")
            public_call = safe_text(vr.get("public_model_class"), "").upper()
            reconstructed_call = safe_text(vr.get("v3_reconstructed_call"), "").upper()
            if phase_status == "DIRECTIONAL_CALL" and public_call in ["APPROVED","CRL"]:
                v3_call = public_call
                v3_match = safe_text(vr.get("v3_phase_a_match"), "")
                v3_origin = "Preserved decision-safe public call"
            elif reconstructed_call in ["APPROVED","CRL","REVIEW"]:
                v3_call = reconstructed_call
                v3_match = safe_text(vr.get("v3_reconstructed_match"), "NO_CALL")
                v3_origin = "Retrospective V3 reconstruction from pre-decision public evidence"
            else:
                v3_call = "REVIEW"
                v3_match = "NO_CALL"
                v3_origin = "Strict V3 review / no directional call"

            if assessment and assessment["assessment_basis"] == "STRICT":
                v3_call = assessment["strict_direction"]
                v3_match = assessment["match_result"]
                v3_origin = "Recorded strict qualification, including verified evidence promotions"

            st.markdown("### FDA-V3 Review")
            fv1,fv2,fv3,fv4 = st.columns(4)
            fv1.metric("FDA-V3 Call", v3_call)
            fv2.metric("FDA-V3 Match", v3_match)
            fv3.metric("Review Status", safe_text(vr.get("v3_review_status"), phase_status or "REVIEW"))
            fv4.metric("Miss Class", safe_text(vr.get("diagnostic_miss_class"), "—"))
            st.write(f"**Call provenance:** {v3_origin}")
            st.write(
                f"**V3 Evidence Summary:** "
                f"{safe_text(vr.get('v3_evidence_summary'), 'No additional V3 summary stored.')}"
            )
            st.caption(
                f"V3 reviewed: {safe_text(vr.get('v3_last_reviewed'), 'NA')} · "
                f"Historical priority: {safe_text(vr.get('v3_backfill_priority'), 'NA')}"
            )
            v3_sources = [
                x.strip() for x in safe_text(vr.get("v3_source_urls"), "").split("|")
                if x.strip()
            ]
            if v3_sources:
                src_cols = st.columns(min(3, len(v3_sources)))
                for i, url in enumerate(v3_sources[:3]):
                    with src_cols[i]:
                        st.link_button(f"OPEN V3 SOURCE {i+1}", url, use_container_width=True)

        st.markdown("### V2 Audit / Validation Status")
        vs1,vs2,vs3,vs4 = st.columns(4)
        v2_status = prediction_v2_history_status(hr)
        vs1.metric("V2 Status", v2_status)
        vs2.metric("Audit Status", safe_text(hr.get("audit_status"), "UNREVIEWED"))
        vs3.metric("Needs Rescore", safe_text(hr.get("needs_rescore"), "NO"))
        vs4.metric("Canonical PDUFA", safe_text(hr.get("canonical_pdufa_date"), "NA"))
        st.write(f"**Audit Action:** {safe_text(hr.get('audit_action'), 'NA')}")
        st.write(f"**Failure / Audit Reason:** {safe_text(hr.get('failure_reason'), 'NA')}")
        audit_source = safe_text(hr.get("source_url"), "")
        if audit_source:
            st.link_button("OPEN AUDIT SOURCE", audit_source, use_container_width=False)

        st.markdown("### Model / Validation Record")
        v1,v2,v3 = st.columns(3)
        with v1:
            st.write(f"**Market Cap Bucket:** {safe_text(hr.get('market_cap_bucket'), 'NA')}")
            st.write(f"**Cap Match Method:** {safe_text(hr.get('market_cap_match_method'), 'NA')}")
        with v2:
            st.write(f"**Validation Period:** {safe_text(hr.get('validation_period'), 'NA')}")
            st.write(f"**Validation Role:** {safe_text(hr.get('independence_status'), 'NA')}")
        with v3:
            st.write(f"**Cap Recovery Confidence:** {safe_text(hr.get('cap_recovery_confidence'), 'NA')}")
            st.write(f"**Cap Recovery Method:** {safe_text(hr.get('cap_recovery_method'), 'NA')}")

        if safe_text(hr.get("independence_status"), "") == "IN_SAMPLE_NOT_EXTERNAL_VALIDATION":
            st.warning("This 2026 case is model-development/in-sample, not an independent blind validation case.")
        else:
            st.success("This case is labeled as an external holdout in the canonical cohort file.")

        st.caption("Historical detail is limited to fields present in the canonical final cohort; company/drug/indication are not fabricated.")
        st.stop()

    ordered = df.sort_values(["ticker","pdufa_date","drug"], na_position="last").copy()
    ordered["event_key"] = ordered.apply(make_event_key, axis=1)
    ordered["event_label"] = ordered.apply(
        lambda x: f"{safe_text(x.get('ticker'))} · {fmt_app_pct(x.get('approval_probability'), 1)} — {safe_text(x.get('drug'))} — " +
                  ("Date pending" if pd.isna(x.get("pdufa_date")) else pd.Timestamp(x.get("pdufa_date")).strftime("%b %d, %Y")),
        axis=1
    )
    event_keys = ordered["event_key"].tolist()
    selected_key = st.session_state.selected_event_key
    if event_keys and selected_key not in event_keys:
        ticker_matches = ordered[ordered["ticker"].astype(str) == str(st.session_state.selected_ticker)]
        selected_key = ticker_matches.iloc[0]["event_key"] if not ticker_matches.empty else event_keys[0]

    csel,b1,b2 = st.columns([3,1,1])
    with csel:
        selected_key = st.selectbox(
            "Company / Drug / PDUFA Event",
            event_keys,
            index=event_keys.index(selected_key) if selected_key in event_keys else 0,
            format_func=lambda k: ordered.loc[ordered["event_key"] == k, "event_label"].iloc[0],
            key="individual_selector"
        )
        st.session_state.selected_event_key = selected_key
        selected_row = ordered[ordered["event_key"] == selected_key].iloc[0]
        st.session_state.selected_ticker = str(selected_row["ticker"])
    with b1:
        st.write("")
        st.write("")
        if st.button("← MASTER TABLE", use_container_width=True):
            go_page("MASTER TABLE")
            st.rerun()
    with b2:
        st.write("")
        st.write("")
        if st.button("← CALENDAR", use_container_width=True):
            go_page("2. PDUFA CALENDAR")
            st.rerun()
    if ordered.empty:
        st.info("No candidates loaded.")
    else:
        r = ordered[ordered["event_key"] == st.session_state.selected_event_key].iloc[0]
        st.markdown(
            f"## {r.ticker} · P% {fmt_app_pct(all_source_probability_value(r), 1)} "
            f"· F {direction_fda_display(r)} — {r.company}"
        )
        st.caption(f"{safe_text(r.get('drug'))} · {safe_text(r.get('indication'))}")
        days_left = None if pd.isna(r.get("pdufa_date")) else int((pd.Timestamp(r.get("pdufa_date")) - today).days)

        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("P%", displayed_probability_text(r, 1), help="Stored Probability of Approval; blank when no score exists")
        k2.metric("F", direction_fda_display(r), help="FDA direction")
        k3.metric("C", combined_probability_direction(r), help="Combined P% + FDA direction")
        k4.metric("PDUFA Date", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
        k5.metric("Days Left", "Not available" if days_left is None else days_left)
        k6.metric("PDUFA Status", safe_text(r.get("pdufa_confirmation")))

        k5,k6,k7,k8 = st.columns(4)
        k5.metric("Market Cap", fmt_cap(r.get("market_cap")))
        k6.metric("Cap Bucket", safe_text(r.get("market_cap_bucket")))
        k7.metric("Phase 3", safe_text(r.get("phase3_status")))
        k8.metric("Eligibility", safe_text(r.get("monitor_eligibility")))

        if pd.notna(r.get("pdufa_date")):
            pdufa_date_text = pd.Timestamp(r.get("pdufa_date")).strftime("%A, %B %d, %Y")
            st.success(f"✅ **PDUFA DATE SET:** {pdufa_date_text} · {safe_text(r.get('pdufa_confirmation'))}")
        else:
            st.warning("⚠️ No PDUFA date is stored for this event.")

        subtabs = st.tabs(["Overview","Pipeline Tracker","PDUFA Timeline","Clinical","FDA","Financing","Trading","News","Scoring","Analogs"])
        with subtabs[0]:
            a,b = st.columns(2)
            with a:
                st.markdown("### Candidate")
                st.write(f"**Drug:** {safe_text(r.get('drug'))}")
                st.write(f"**Indication:** {safe_text(r.get('indication'))}")
                st.write(f"**Application:** {safe_text(r.get('application_type'))}")
                st.write(f"**Signal / gate:** {safe_text(r.get('signal'))}")
                st.write(f"**Conflict flag:** {safe_text(r.get('conflict_flag'))}")
                st.write(f"**Check status:** {safe_text(r.get('check_status'))}")
            with b:
                st.markdown("### Evidence snapshot")
                st.write(f"**Phase 3 status:** {safe_text(r.get('phase3_status'))}")
                st.write(f"**Phase 3 date:** {'Not captured' if pd.isna(r.get('phase3_date')) else pd.Timestamp(r.get('phase3_date')).strftime('%b %d, %Y')}")
                st.write(f"**NCT ID(s):** {safe_text(r.get('nct_id'))}")
                st.write(f"**Reported p-value(s):** {safe_text(r.get('reported_p_values'))}")
                st.write(f"**Financing:** {safe_text(r.get('financing_status'))}")
                st.write(f"**Last checked:** {safe_text(r.get('last_checked'))}")
                st.write(f"**Model confidence:** {safe_text(r.get('confidence'), 'Not scored')}")
            s1,s2,s3 = st.columns(3)
            if safe_text(r.get("pdufa_evidence_url"), ""):
                with s1:
                    st.link_button("OPEN PDUFA / FDA SOURCE", r.get("pdufa_evidence_url"), use_container_width=True)
            if safe_text(r.get("trial_evidence_url"), ""):
                with s2:
                    st.link_button("OPEN PHASE 3 SOURCE", r.get("trial_evidence_url"), use_container_width=True)
            if safe_text(r.get("financing_evidence_url"), ""):
                with s3:
                    st.link_button("OPEN FINANCING SOURCE", r.get("financing_evidence_url"), use_container_width=True)
            with st.expander("Full saved event notes", expanded=False):
                st.write(safe_text(r.get("evidence_summary"), "No saved notes."))
        with subtabs[1]:
            ptitle, pwatch = st.columns([4,1])
            with ptitle:
                st.markdown("### Development Pipeline — Phase 1 to Now")
                st.caption("One continuous tracker for the selected drug/indication. Missing milestone dates are labeled Not captured; they are not treated as failed or unknown outcomes.")
            with pwatch:
                ticker_key = str(r.ticker)
                on_watchlist = ticker_key in st.session_state.watchlist
                watch_label = "★ REMOVE WATCHLIST" if on_watchlist else "☆ ADD TO WATCHLIST"
                if st.button(watch_label, use_container_width=True, key=f"pipeline_watch_{ticker_key}"):
                    if on_watchlist:
                        st.session_state.watchlist = [x for x in st.session_state.watchlist if x != ticker_key]
                        st.toast(f"{ticker_key} removed from watchlist")
                    else:
                        st.session_state.watchlist.append(ticker_key)
                        st.toast(f"{ticker_key} added to watchlist")
                    st.rerun()

            if ticker_key in st.session_state.watchlist:
                st.success(f"★ {ticker_key} is on your watchlist")

            stages = [
                ("Phase 1", r.get("phase1_date"), "Early safety / dose finding"),
                ("Phase 2", r.get("phase2_date"), "Proof of concept / dose refinement"),
                ("Phase 3 / Pivotal", r.get("phase3_date"), "Confirmatory efficacy and safety"),
                ("NDA/BLA Submitted", r.get("nda_submission_date"), "Regulatory application submitted"),
                ("FDA Accepted", r.get("fda_acceptance_date"), "Application accepted for review"),
                ("PDUFA Review", r.get("pdufa_date"), "FDA review period / decision date"),
                ("FDA Decision", r.get("decision_date"), "Approval / CRL / other action"),
            ]

            known_dates = [(name, pd.Timestamp(dt)) for name,dt,_ in stages if pd.notna(dt)]
            if pd.notna(r.get("decision_date")):
                current_stage = "FDA Decision"
            elif pd.notna(r.get("pdufa_date")) and pd.Timestamp(r.get("pdufa_date")) < today:
                current_stage = "FDA Decision"
            elif pd.notna(r.get("pdufa_date")):
                current_stage = "PDUFA Review"
            elif pd.notna(r.get("fda_acceptance_date")):
                current_stage = "FDA Accepted"
            elif pd.notna(r.get("nda_submission_date")):
                current_stage = "NDA/BLA Submitted"
            elif pd.notna(r.get("phase3_date")):
                current_stage = "Phase 3 / Pivotal"
            elif pd.notna(r.get("phase2_date")):
                current_stage = "Phase 2"
            elif pd.notna(r.get("phase1_date")):
                current_stage = "Phase 1"
            else:
                current_stage = str(r.get("setup_phase")) if pd.notna(r.get("setup_phase")) else "Current stage not yet dated"

            st.info(f"STAGE: **{program_stage(r)}**")

            cols = st.columns(7)
            current_index = next((i for i,(name,_,_) in enumerate(stages) if name == current_stage), None)
            for i, ((name,dt,desc), col) in enumerate(zip(stages, cols)):
                if pd.notna(dt):
                    date_text = pd.Timestamp(dt).strftime("%b %d, %Y")
                else:
                    date_text = "Not captured"
                if current_index is not None and i < current_index:
                    if pd.notna(dt):
                        icon = "✅"
                        status = "Completed — date verified"
                    else:
                        icon = "✓"
                        status = "Completed / inferred — date not captured"
                elif current_index is not None and i == current_index:
                    icon = "🔵"
                    status = "Current"
                else:
                    icon = "○"
                    status = "Upcoming / not captured"
                with col:
                    st.markdown(f"### {icon} {name}")
                    st.write(f"**{status}**")
                    st.write(date_text)
                    st.caption(desc)

            st.divider()
            pipeline_table = pd.DataFrame([
                {
                    "Milestone": name,
                    "Date": "Not captured" if pd.isna(dt) else pd.Timestamp(dt).strftime("%Y-%m-%d"),
                    "Status": (
                        ("Completed — date verified" if pd.notna(dt) else "Completed / inferred — date not captured")
                        if current_index is not None and i < current_index
                        else "Current" if current_index is not None and i == current_index
                        else "Upcoming / not captured"
                    ),
                    "Purpose": desc,
                }
                for i,(name,dt,desc) in enumerate(stages)
            ])
            grouped_dataframe(pipeline_table, use_container_width=True, hide_index=True, stage_source=r)

        with subtabs[2]:
            st.markdown("### PDUFA Timeline")
            t1,t2,t3,t4 = st.columns(4)
            t1.metric("PDUFA", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
            t2.metric("Confirmation", safe_text(r.get("pdufa_confirmation")))
            t3.metric("Phase 3 status", safe_text(r.get("phase3_status")))
            t4.metric("FDA check", safe_text(r.get("check_status")))
            st.write(f"**Phase 3 date:** {'Not captured' if pd.isna(r.get('phase3_date')) else pd.Timestamp(r.get('phase3_date')).strftime('%b %d, %Y')}")
            st.write(f"**NCT ID(s):** {safe_text(r.get('nct_id'))}")
            st.write(f"**Reported p-value(s):** {safe_text(r.get('reported_p_values'))}")
            st.write(f"**Conflict:** {safe_text(r.get('conflict_flag'))}")
            st.write(f"**Monitoring eligibility:** {safe_text(r.get('monitor_eligibility'))}")
            if safe_text(r.get("pdufa_evidence_url"), ""):
                st.link_button("OPEN PDUFA EVIDENCE", r.get("pdufa_evidence_url"))
        with subtabs[3]:
            st.markdown("### Clinical / Phase 3")
            c1,c2,c3 = st.columns(3)
            c1.metric("Phase 3 status", safe_text(r.get("phase3_status")))
            c2.metric("P-value(s)", safe_text(r.get("reported_p_values")))
            c3.metric("NCT", safe_text(r.get("nct_id")))
            st.write(f"**Phase 3 date:** {'Not captured' if pd.isna(r.get('phase3_date')) else pd.Timestamp(r.get('phase3_date')).strftime('%b %d, %Y')}")
            if safe_text(r.get("trial_evidence_url"), ""):
                st.link_button("OPEN CLINICAL / TRIAL SOURCE", r.get("trial_evidence_url"))
            st.write(safe_text(r.get("science_summary"), "No additional clinical summary stored."))
        with subtabs[4]:
            st.markdown("### FDA / Regulatory")
            f1,f2,f3,f4,f5 = st.columns(5)
            f1.metric("PDUFA date", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
            f2.metric("Decision date", "Open" if pd.isna(r.get("decision_date")) else pd.Timestamp(r.get("decision_date")).strftime("%b %d, %Y"))
            f3.metric("FDA Model %", "" if safe_text(r.get("fda_probability"), "") == "" else fmt_app_pct(r.get("fda_probability"), 1))
            f4.metric("FDA Call", safe_text(r.get("fda_prediction"), "REVIEW"))
            f5.metric("FDA Gate", safe_text(r.get("fda_hard_gate"), "REVIEW"))

            review_rows = [
                ("Application identity", r.get("fda_application_identity")),
                ("Clinical efficacy", r.get("fda_clinical_score")),
                ("Statistics", r.get("fda_statistics_score")),
                ("Stats gate", r.get("fda_statistics_gate")),
                ("Primary endpoint", r.get("fda_primary_endpoint_status")),
                ("Multiplicity control", r.get("fda_multiplicity_status")),
                ("Missing-data robustness", r.get("fda_missing_data_status")),
                ("Effect size / relevance", r.get("fda_effect_size_status")),
                ("Replication", r.get("fda_replication_status")),
                ("Clinical meaningfulness", r.get("fda_meaningfulness_score")),
                ("Safety", r.get("fda_safety_score")),
                ("Clinical pharmacology / PK", r.get("fda_clinical_pharmacology_score")),
                ("Nonclinical / toxicology", r.get("fda_nonclinical_score")),
                ("CMC / product quality", r.get("fda_cmc_score")),
                ("CMC gate", r.get("fda_cmc_gate")),
                ("Process validation", r.get("fda_process_validation_status")),
                ("Stability", r.get("fda_stability_status")),
                ("Analytical methods", r.get("fda_analytical_methods_status")),
                ("Comparability", r.get("fda_comparability_status")),
                ("Supplier / DMF risk", r.get("fda_supplier_status")),
                ("Manufacturing / inspection", r.get("fda_inspection_status")),
                ("Facility gate", r.get("fda_facility_gate")),
                ("Warning letter", r.get("fda_warning_letter_status")),
                ("Import alert", r.get("fda_import_alert_status")),
                ("Form 483", r.get("fda_form483_status")),
                ("Facility classification", r.get("fda_facility_classification")),
                ("Preapproval inspection", r.get("fda_preapproval_inspection_status")),
                ("BIMO / data integrity", r.get("fda_bimo_status")),
                ("Data-integrity gate", r.get("fda_data_integrity_gate")),
                ("Regulatory history", r.get("fda_regulatory_score")),
                ("Labeling", r.get("fda_labeling_score")),
                ("Benefit-risk", r.get("fda_benefit_risk_score")),
                ("Evidence freshness", r.get("fda_evidence_freshness")),
            ]
            grouped_dataframe(
                pd.DataFrame([{"FDA Review Block": a, "Status / Score": safe_text(b, "UNKNOWN")} for a,b in review_rows]),
                use_container_width=True,
                hide_index=True,
                stage_source=r,
            )
            event_facilities = fda_facilities[
                fda_facilities["event_key"].astype(str).eq(str(r.get("event_key")))
            ] if not fda_facilities.empty else pd.DataFrame()
            if not event_facilities.empty:
                st.markdown("#### Manufacturing / Facility Evidence")
                facility_show = event_facilities[[
                    "site_name","site_country","site_role","fei",
                    "warning_letter_status","import_alert_status","form483_status",
                    "facility_classification","preapproval_inspection_status",
                    "remediation_status","evidence_as_of","source_url","source_note"
                ]].rename(columns={
                    "site_name":"Site","site_country":"Country","site_role":"Role","fei":"FEI",
                    "warning_letter_status":"Warning Letter","import_alert_status":"Import Alert",
                    "form483_status":"Form 483","facility_classification":"Classification",
                    "preapproval_inspection_status":"PAI Status","remediation_status":"Remediation",
                    "evidence_as_of":"As Of","source_url":"Source","source_note":"Evidence Note"
                })
                grouped_dataframe(
                    facility_show,
                    use_container_width=True,
                    hide_index=True,
                    stage_source=r,
                    column_config={"Source": st.column_config.LinkColumn("Source", display_text="Open source")}
                )

            st.write(f"**FDA confidence:** {safe_text(r.get('fda_confidence'), 'INSUFFICIENT FDA EVIDENCE')}")
            st.write(f"**Gate reason:** {safe_text(r.get('fda_gate_reason'), 'FDA review record not yet populated')}")
            st.write(f"**Prediction frozen at:** {safe_text(r.get('fda_prediction_frozen_at'), 'Not frozen')}")
            st.write(f"**Model version:** {safe_text(r.get('fda_model_version'), 'FDA-V3.2')}")
            if safe_text(r.get("pdufa_evidence_url"), ""):
                st.link_button("OPEN REGULATORY SOURCE", r.get("pdufa_evidence_url"))
            st.write(safe_text(r.get("regulatory_summary"), "No additional regulatory notes stored."))
        with subtabs[5]:
            st.markdown("### Financing")
            f1,f2,f3,f4 = st.columns(4)
            f1.metric("Status", safe_text(r.get("financing_status")))
            f2.metric("Close date", "Not captured" if pd.isna(r.get("financing_close_date")) else pd.Timestamp(r.get("financing_close_date")).strftime("%b %d, %Y"))
            f3.metric("Proceeds", safe_text(r.get("financing_proceeds")))
            f4.metric("New dilution flag", safe_text(r.get("new_dilution_flag")))
            if safe_text(r.get("financing_evidence_url"), ""):
                st.link_button("OPEN FINANCING EVIDENCE", r.get("financing_evidence_url"))
            st.write(safe_text(r.get("financing_summary"), "No additional financing summary stored."))
        with subtabs[6]:
            st.markdown("### Trading / Market")
            t1,t2,t3,t4 = st.columns(4)
            t1.metric("Market Cap", fmt_cap(r.get("market_cap")))
            t2.metric("Cap Bucket", safe_text(r.get("market_cap_bucket")))
            t3.metric("Price", "Not available" if pd.isna(r.get("price_last")) else f"${float(r.get('price_last')):,.2f}")
            t4.metric("30D Return", fmt_pct(r.get("return_30d_pct"), 1))
            t5,t6,t7,t8 = st.columns(4)
            t5.metric("Avg Volume 20D", fmt_num(r.get("avg_volume_20d")))
            t6.metric("Short Interest", fmt_pct(r.get("short_interest"), 1))
            t7.metric("Short Ratio", fmt_num(r.get("short_ratio"), 2))
            t8.metric("Institutional Ownership", fmt_pct(r.get("institutional_ownership_pct"), 1))
            st.write(safe_text(r.get("trading_summary"), "No additional trading narrative stored."))
        with subtabs[7]:
            st.markdown("### Recent News")
            stories,error = fetch_ticker_news(
                safe_text(r.get("ticker"), ""),
                safe_text(r.get("company"), ""),
                safe_text(r.get("drug"), ""),
                14
            )
            if error:
                st.warning(f"News feed unavailable: {error}")
            elif not stories:
                st.info("No matching recent stories found.")
            else:
                for story in stories[:12]:
                    st.markdown(
                        f"""<div class="card"><span class="pill">{story['category']}</span>
                        <span class="pill">{story['priority']}</span>
                        <b>{html.escape(story['title'])}</b><br>
                        <span class="muted">{html.escape(story['source'])}</span></div>""",
                        unsafe_allow_html=True,
                    )
                    if story["link"]:
                        st.link_button("READ SOURCE", story["link"])
        with subtabs[8]:
            st.markdown("### Scoring")
            s1,s2,s3,s4,s5 = st.columns(5)
            for col,label,key in [
                (s1,"Science","science_score"),(s2,"Regulatory","regulatory_score"),
                (s3,"Safety","safety_score"),(s4,"CMC","cmc_score"),(s5,"Trade","trade_score")
            ]:
                v = r.get(key,pd.NA)
                col.metric(label, "Not scored" if pd.isna(v) else f"{float(v):.0f}/100")
            st.metric("Direction / FDA Match", direction_fda_display(r))
            st.caption("Before FDA acts, this shows the best decision-safe predicted direction. After FDA acts, it becomes 100% MATCH when the prediction and FDA direction agree, or 0% MATCH when they disagree. Approval probability and trading attractiveness remain separate.")
        with subtabs[9]:
            st.markdown("### Historical Analogs")
            st.caption("Uses only historical cases already loaded in the Prediction Engine. Invalid/excluded audit rows are not used.")
            analogs = prediction_history.copy()
            if analogs.empty:
                st.info("No historical prediction cases are loaded.")
            else:
                analogs = analogs[
                    analogs["count_in_audited_accuracy"].fillna("YES").astype(str).str.upper().eq("YES")
                ].copy()
                analogs["_p"] = pd.to_numeric(analogs["p_approval"], errors="coerce")
                analogs["_cap"] = pd.to_numeric(analogs["historical_market_cap_billions"], errors="coerce")
                current_p = r.get("approval_probability")
                current_bucket = safe_text(r.get("market_cap_bucket"), "")
                if pd.notna(current_p):
                    cp = float(current_p)
                    if cp > 1:
                        cp /= 100.0
                    analogs["_distance"] = (analogs["_p"] - cp).abs()
                else:
                    analogs["_distance"] = 999.0

                same_bucket = analogs[
                    analogs["market_cap_bucket"].fillna("").astype(str).eq(current_bucket)
                ] if current_bucket else analogs.iloc[0:0]
                pool = same_bucket if not same_bucket.empty else analogs
                pool = pool.sort_values(["_distance","pdufa_date"]).head(10).copy()
                pool["PDUFA Date"] = pd.to_datetime(pool["pdufa_date"], errors="coerce").dt.strftime("%Y-%m-%d")
                pool["Probability of Approval % — Public"] = pd.to_numeric(
                    pool.get("public_approval_probability"), errors="coerce"
                ).apply(lambda v: fmt_app_pct(v, 1))
                pool["Probability of Approval % — All Sources"] = pool.apply(
                    lambda rr: fmt_app_pct(all_source_probability_value(rr), 1), axis=1
                )
                pool["Direction / FDA Match"] = pool.apply(direction_fda_display, axis=1)
                pool["Historical Cap"] = pool["_cap"].apply(
                    lambda v: "NA" if pd.isna(v) else "$" + f"{float(v):.2f}B"
                )
                pool["Result"] = pool["correct"].astype(str).map(
                    {"True":"Correct","False":"Wrong","true":"Correct","false":"Wrong"}
                ).fillna("NA")
                analog_display = pool[[
                    "ticker","PDUFA Date","Probability of Approval % — Public","Probability of Approval % — All Sources","Direction / FDA Match","actual_outcome",
                    "Historical Cap","market_cap_bucket","Result","audit_status"
                ]].rename(columns={
                    "ticker":"Ticker",
                    "actual_outcome":"Actual FDA",
                    "market_cap_bucket":"Cap Bucket",
                    "audit_status":"Audit Status"
                })
                grouped_dataframe(analog_display, use_container_width=True, hide_index=True)
                if not same_bucket.empty:
                    st.success(f"Showing the closest historical cases from the same market-cap bucket: {current_bucket}.")
                else:
                    st.info("No same-bucket historical cases were available, so the closest loaded cases by approval probability are shown.")

st.divider()
st.caption("FDA probabilities are model estimates, not FDA determinations. Direction / FDA Match is a result score, not an approval probability: before a final FDA outcome it shows the predicted direction; after the outcome it shows 100% for a matching direction or 0% for a miss. Missing fields are labeled Not available or Not scored rather than being invented.")

