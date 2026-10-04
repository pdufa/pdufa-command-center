import streamlit as st
import pandas as pd
from datetime import date
import calendar
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

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
</style>""",
    unsafe_allow_html=True,
)


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
        "financing_evidence_url","new_dilution_flag","financing_proceeds"
    ]
    optional_numeric = [
        "approval_probability","public_approval_probability","biopharmawatch_probability","science_score","regulatory_score","safety_score",
        "cmc_score","market_cap","trade_score","short_interest","iv_30d",
        "price_last","return_30d_pct","avg_volume_20d","short_ratio","shares_float",
        "institutional_ownership_pct","cash"
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
    x["biopharmawatch_probability"] = x["biopharmawatch_probability"].apply(
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
    for col in ["cap_recovery_confidence","cap_recovery_method","public_approval_probability","biopharmawatch_probability","public_model_class","public_evidence_note","internal_direction_class","internal_direction_note"]:
        if col not in x:
            x[col] = pd.NA
    x["public_approval_probability"] = pd.to_numeric(x["public_approval_probability"], errors="coerce")
    x["biopharmawatch_probability"] = pd.to_numeric(x["biopharmawatch_probability"], errors="coerce")
    x["biopharmawatch_probability"] = x["biopharmawatch_probability"].apply(
        lambda v: v * 100 if pd.notna(v) and 0 <= float(v) <= 1 else v
    )
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


df = load_data()
prediction_history = load_prediction_history()
prediction_rescore_queue = load_prediction_rescore_queue()

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

today = pd.Timestamp(date.today())
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

# Refresh normalized values into future.
future = df[df["pdufa_date"].notna() & (df["pdufa_date"] >= today)].copy()
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
    """Conservative V2 decision layer for live/future PDUFA rows."""
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


def all_source_probability_value(row):
    """All-source PoA: equal-weight I App, P App, and actual BiopharmaWatch PoA.
    Requires all three inputs so the displayed score really is an all-source score.
    """
    vals = []
    for field in ["approval_probability", "public_approval_probability", "biopharmawatch_probability"]:
        v = row.get(field, row.get("p_approval") if field == "approval_probability" else pd.NA)
        if v is None or pd.isna(v):
            return pd.NA
        v = float(v)
        if 0 <= v <= 1:
            v *= 100
        vals.append(v)
    return sum(vals) / 3.0


def all_source_direction_state(row):
    """Direction from the all-source probability, gated by I/P disagreement."""
    score = all_source_probability_value(row)
    if score is None or pd.isna(score):
        return "REVIEW"
    if internal_direction_state(row) != public_direction_state(row):
        return "REVIEW"
    return "APPROVED" if float(score) >= 50 else "CRL"

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

def event_detail_url(row, source="live", return_page="1. ALL PDUFA"):
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
    if len(st.query_params):
        st.query_params.clear()

def go_individual(ticker=None, event_key=None, source="live", return_page=None):
    if ticker is not None:
        st.session_state.selected_ticker = str(ticker)
    if event_key is not None:
        st.session_state.selected_event_key = str(event_key)
    st.session_state.selected_detail_source = source
    st.session_state.detail_return_page = return_page or st.session_state.get("nav", "1. ALL PDUFA")
    st.session_state.detail_open = True
    if len(st.query_params):
        st.query_params.clear()

def table_view(frame, return_page="1. ALL PDUFA"):
    out = frame.copy()

    # Guarantee every master-table column exists even if the source feed is incomplete.
    defaults = {
        "ticker":"", "company":"Not available", "drug":"Not available", "indication":"Not available",
        "pdufa_date":pd.NaT, "market_cap":pd.NA, "market_cap_bucket":"Not available",
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

    for c in ["ticker","company","drug","indication"]:
        out[c] = out[c].fillna("Not available").astype(str)

    return out.rename(columns={
        "company":"Company","drug":"Drug","indication":"Indication","Ticker Link":"Ticker"
    })[[
        "Ticker","Probability of Approval % — Public","Probability of Approval % — All Sources","I Direction","P Direction","All-Source Direction","Company","Drug","Indication","PDUFA Date","Days Left","Market Cap",
        "Cap Bucket","Trade Score","Outcome","Signal","Confidence","Application",
        "Financing","Phase","Short %","IV (30d)","Record Source"
    ]]

query_event = st.query_params.get("event")
query_ticker = st.query_params.get("ticker")
query_page = st.query_params.get("page")
query_source = st.query_params.get("source") or "live"
query_return = st.query_params.get("return") or "1. ALL PDUFA"

if query_page == "detail" and query_event:
    st.session_state.selected_event_key = str(query_event)
    if query_ticker:
        st.session_state.selected_ticker = str(query_ticker)
    st.session_state.selected_detail_source = str(query_source)
    st.session_state.detail_return_page = str(query_return)
    st.session_state.detail_open = True
    st.query_params.clear()

if "nav" not in st.session_state:
    st.session_state.nav = "1. ALL PDUFA"
if "detail_open" not in st.session_state:
    st.session_state.detail_open = False
if "selected_detail_source" not in st.session_state:
    st.session_state.selected_detail_source = "live"
if "detail_return_page" not in st.session_state:
    st.session_state.detail_return_page = "1. ALL PDUFA"
if "selected_ticker" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_ticker = str(base.iloc[0]["ticker"]) if not base.empty else ""
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "selected_event_key" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_event_key = make_event_key(base.iloc[0]) if not base.empty else ""

st.title("🧬 BIO PDUFA COMMAND CENTER")
st.caption("BUILD 2026-10-04 · I/P APP SPLIT ACTIVE")
st.caption("ALL PDUFA → MARKET CAP GROUPS → CALENDAR → PREDICTION ENGINE. Company/PDUFA detail opens only when an event is clicked.")
st.caption("Two visible approval scores: Public = public-only evidence. All Sources = combined internal + public + BiopharmaWatch inputs when available.")

if "_pending_nav" in st.session_state:
    st.session_state.nav = st.session_state.pop("_pending_nav")
    st.session_state.detail_open = False

nav_options = ["1. ALL PDUFA","2. MARKET CAP GROUPS","3. CALENDAR","4. PREDICTION ENGINE"]
if st.session_state.detail_open:
    page = "__DETAIL__"
else:
    if st.session_state.nav not in nav_options:
        st.session_state.nav = "1. ALL PDUFA"
    st.radio("Navigation", nav_options, horizontal=True, key="nav", label_visibility="collapsed")
    page = st.session_state.nav
    if len(st.query_params):
        st.query_params.clear()

if page == "1. ALL PDUFA":
    st.markdown("## 1. ALL PDUFA — SAVED EVENT FEED")
    st.caption("Sortable saved PDUFA events currently loaded into Streamlit. This live feed is event-level and preserves multi-event tickers. Historical validation cohorts are not silently counted unless they are actually loaded here.")

    live_master = df.copy()
    live_master["_detail_source"] = "live"

    # Include historical PDUFA cases already researched by the Prediction Engine.
    hist = prediction_history.copy()
    if not hist.empty:
        keep_hist = hist["count_in_audited_accuracy"].fillna("YES").astype(str).str.upper().eq("YES")
        hist = hist[keep_hist].copy()
        hist["_canonical_date"] = pd.to_datetime(hist.get("canonical_pdufa_date"), errors="coerce")
        hist["_original_date"] = pd.to_datetime(hist.get("pdufa_date"), errors="coerce")
        hist["pdufa_date"] = hist["_canonical_date"].fillna(hist["_original_date"])
        hist["company"] = "Historical validation record"
        hist["drug"] = "Not captured in validation file"
        hist["indication"] = "Not captured in validation file"
        hist["approval_probability"] = pd.to_numeric(hist.get("p_approval"), errors="coerce")
        hist["public_approval_probability"] = pd.NA
        hist["market_cap"] = pd.to_numeric(hist.get("historical_market_cap_billions"), errors="coerce") * 1_000_000_000
        hist["trade_score"] = pd.NA
        hist["financing_status"] = "Historical"
        hist["setup_phase"] = "Historical PDUFA"
        hist["short_interest"] = pd.NA
        hist["iv_30d"] = pd.NA
        hist["signal"] = hist.get("model_class", pd.Series(index=hist.index, dtype="object"))
        hist["confidence"] = hist.get("audit_status", pd.Series(index=hist.index, dtype="object")).fillna("Historical")
        hist["outcome"] = hist.get("actual_outcome", pd.Series(index=hist.index, dtype="object"))
        hist["application_type"] = "Historical validation"
        hist["_detail_source"] = "history"

        for col in live_master.columns:
            if col not in hist:
                hist[col] = pd.NA
        hist = hist[live_master.columns]
        live_keys = set(live_master["event_key"].astype(str))
        hist = hist[~hist["event_key"].astype(str).isin(live_keys)]
        master = pd.concat([live_master, hist], ignore_index=True, sort=False)
    else:
        master = live_master

    master["time_status"] = master["pdufa_date"].apply(
        lambda d: "Unknown" if pd.isna(d) else (
            "Past" if pd.Timestamp(d).date() < date.today()
            else ("Today" if pd.Timestamp(d).date() == date.today() else "Future")
        )
    )
    master["active_status"] = master["time_status"].apply(
        lambda s: "Present / Active" if s in ["Today","Future"] else s
    )
    master["year"] = master["pdufa_date"].dt.year
    master["days_from_today"] = (master["pdufa_date"] - today).dt.days
    master["outcome_display"] = master["outcome"].apply(lambda v: safe_text(v, "Pending"))
    master["signal_display"] = master["signal"].apply(lambda v: safe_text(v, "Pending"))
    master["financing_display"] = master["financing_status"].apply(lambda v: safe_text(v, "Pending"))

    top1, top2, top3, top4, top5 = st.columns([1.25,1.25,1.25,1.25,2.2])

    with top1:
        time_view = st.selectbox(
            "Past / Present / Future",
            ["All","Past","Present / Active","Today","Future","Unknown"],
            index=0,
            help="Present / Active includes today and all upcoming PDUFA dates."
        )

    with top2:
        year_mode = st.selectbox("PDUFA Year", ["All years","Specific year","Year range"])
        year_filter = None
        year_start = None
        year_end = None
        if year_mode == "Specific year":
            year_filter = int(st.number_input(
                "Enter year",
                min_value=1990,
                max_value=2100,
                value=int(date.today().year),
                step=1,
                key="specific_pdufa_year"
            ))
        elif year_mode == "Year range":
            yr1, yr2 = st.columns(2)
            with yr1:
                year_start = int(st.number_input(
                    "From",
                    min_value=1990,
                    max_value=2100,
                    value=2020,
                    step=1,
                    key="pdufa_year_from"
                ))
            with yr2:
                year_end = int(st.number_input(
                    "To",
                    min_value=1990,
                    max_value=2100,
                    value=int(date.today().year + 1),
                    step=1,
                    key="pdufa_year_to"
                ))

    with top3:
        outcome_values = sorted(master["outcome_display"].dropna().astype(str).unique().tolist())
        outcome_filter = st.multiselect(
            "FDA Outcome",
            outcome_values,
            default=[]
        )

    with top4:
        signal_values = sorted(master["signal_display"].dropna().astype(str).unique().tolist())
        signal_filter = st.multiselect("Status / Signal", signal_values, default=[])

    with top5:
        search = st.text_input("Search ticker, company, drug, indication")

    row2a, row2b, row2c, row2d, row2e = st.columns([1.4,1.4,1.4,1.4,1.8])

    known_caps = master["market_cap"].dropna()
    cap_min_default = 300_000_000
    cap_max_default = 10_000_000_000
    if not known_caps.empty:
        cap_min_default = int(max(0, known_caps.min()))
        cap_max_default = int(max(known_caps.max(), cap_min_default + 1))

    with row2a:
        cap_presets = st.selectbox(
            "Market Cap",
            ["All","$300M–$500M","$500M–$750M","$750M–$1B","$1B–$2B","$2B–$3B","$3B–$5B","$5B–$7.5B","$7.5B–$10B","Custom"]
        )

    with row2b:
        min_poa = st.slider("Minimum I App %", 0, 100, 0)

    with row2c:
        min_trade = st.slider("Minimum Trade Score", 0, 100, 0)

    with row2d:
        financing_values = sorted(master["financing_display"].dropna().astype(str).unique().tolist())
        financing_filter = st.multiselect("Financing", financing_values, default=[])

    with row2e:
        sort_choice = st.selectbox(
            "Sort",
            ["PDUFA date ↑","PDUFA date ↓","Market cap ↓","I App % ↓","Trade score ↓","Ticker A–Z"]
        )

    if cap_presets == "Custom":
        cmin,cmax = st.slider(
            "Custom market-cap range",
            min_value=0,
            max_value=max(cap_max_default,10_000_000_000),
            value=(min(cap_min_default,300_000_000), min(max(cap_max_default,10_000_000_000),10_000_000_000)),
            step=50_000_000,
            format="$%d"
        )
    else:
        cap_map = {
            "$300M–$500M":(300_000_000,500_000_000),
            "$500M–$750M":(500_000_000,750_000_000),
            "$750M–$1B":(750_000_000,1_000_000_000),
            "$1B–$2B":(1_000_000_000,2_000_000_000),
            "$2B–$3B":(2_000_000_000,3_000_000_000),
            "$3B–$5B":(3_000_000_000,5_000_000_000),
            "$5B–$7.5B":(5_000_000_000,7_500_000_000),
            "$7.5B–$10B":(7_500_000_000,10_000_000_001),
        }
        cmin,cmax = cap_map.get(cap_presets,(None,None))

    view = master.copy()
    if time_view == "Past":
        view = view[view["time_status"] == "Past"]
    elif time_view == "Present / Active":
        view = view[view["time_status"].isin(["Today","Future"])]
    elif time_view == "Today":
        view = view[view["time_status"] == "Today"]
    elif time_view == "Future":
        view = view[view["time_status"] == "Future"]
    elif time_view == "Unknown":
        view = view[view["time_status"] == "Unknown"]
    if year_mode == "Specific year" and year_filter is not None:
        view = view[view["year"] == year_filter]
    elif year_mode == "Year range" and year_start is not None and year_end is not None:
        lo_year = min(year_start, year_end)
        hi_year = max(year_start, year_end)
        view = view[view["year"].between(lo_year, hi_year)]
    if outcome_filter:
        view = view[view["outcome_display"].isin(outcome_filter)]
    if signal_filter:
        view = view[view["signal_display"].isin(signal_filter)]
    if financing_filter:
        view = view[view["financing_display"].isin(financing_filter)]
    view = view[view["approval_probability"].fillna(0) >= min_poa]
    view = view[view["trade_score"].fillna(0) >= min_trade]

    if cmin is not None:
        # Keep unknown-cap rows visible only when "All" is selected.
        view = view[view["market_cap"].notna() & (view["market_cap"] >= cmin) & (view["market_cap"] < cmax)]

    if search:
        q = search.lower()
        view = view[
            view["ticker"].astype(str).str.lower().str.contains(q, na=False) |
            view["company"].astype(str).str.lower().str.contains(q, na=False) |
            view["drug"].astype(str).str.lower().str.contains(q, na=False) |
            view["indication"].astype(str).str.lower().str.contains(q, na=False)
        ]

    if sort_choice == "PDUFA date ↑":
        view = view.sort_values(["pdufa_date","ticker"], ascending=[True,True], na_position="last")
    elif sort_choice == "PDUFA date ↓":
        view = view.sort_values(["pdufa_date","ticker"], ascending=[False,True], na_position="last")
    elif sort_choice == "Market cap ↓":
        view = view.sort_values(["market_cap","pdufa_date"], ascending=[False,True], na_position="last")
    elif sort_choice == "I App % ↓":
        view = view.sort_values(["approval_probability","pdufa_date"], ascending=[False,True], na_position="last")
    elif sort_choice == "Trade score ↓":
        view = view.sort_values(["trade_score","pdufa_date"], ascending=[False,True], na_position="last")
    else:
        view = view.sort_values("ticker")

    past_n = int((master["time_status"] == "Past").sum())
    today_n = int((master["time_status"] == "Today").sum())
    future_n = int((master["time_status"] == "Future").sum())
    active_n = int(master["time_status"].isin(["Today","Future"]).sum())
    next_4w_n = int(((master["days_from_today"] >= 0) & (master["days_from_today"] <= 27)).sum())

    avg_i_app = pd.to_numeric(view.get("approval_probability"), errors="coerce").mean()
    avg_p_app = pd.to_numeric(view.get("public_approval_probability"), errors="coerce").mean()
    avg_bpw = pd.to_numeric(view.get("biopharmawatch_probability"), errors="coerce").mean()
    all_source_series = view.apply(all_source_probability_value, axis=1)
    avg_all_source = pd.to_numeric(all_source_series, errors="coerce").mean()

    st.markdown("### APPROVAL PROBABILITY")
    m1,m2,m3,m4 = st.columns(4)
    with m1:
        st.markdown("#### PUBLIC")
        st.metric("Probability of Approval % — Public", "Not scored" if pd.isna(avg_p_app) else f"{float(avg_p_app):.1f}%")
    with m2:
        st.markdown("#### ALL SOURCES")
        st.metric("Probability of Approval % — All Sources", "Not scored" if pd.isna(avg_all_source) else f"{float(avg_all_source):.1f}%")
    m3.metric("Saved PDUFA Events", len(master))
    m4.metric("Present / Active", active_n)

    m5,m6,m7,m8 = st.columns(4)
    m5.metric("Past", past_n)
    m6.metric("Today", today_n)
    m7.metric("Future", future_n)
    m8.metric("Next 4 Weeks", next_4w_n)

    st.caption("I App % = internal/private model. P App % = public-only model. BPW % = actual BiopharmaWatch probability when available. Probability of Approval % = equal-weight all-source composite of I + P + BPW and is shown only when all three inputs exist. I+P Consensus remains a separate two-model comparison.")

    st.caption(f"Showing {len(view)} of {len(master)} records. Select a row to open its Individual Company page.")

    valid_dates = int(master["pdufa_date"].notna().sum())
    unique_events = int(master["event_key"].nunique())
    unique_tickers = int(master["ticker"].astype(str).nunique())
    with st.expander("DATA INTEGRITY CHECK", expanded=False):
        q1,q2,q3,q4 = st.columns(4)
        q1.metric("Parsed Rows", len(master))
        q2.metric("Valid PDUFA Dates", valid_dates)
        q3.metric("Unique Events", unique_events)
        q4.metric("Unique Tickers", unique_tickers)
        if len(master) <= 1:
            st.error("DATA ERROR: master feed collapsed to one row.")
        elif valid_dates != len(master):
            st.warning(f"{len(master)-valid_dates} row(s) have missing/invalid PDUFA dates.")
        else:
            st.success("Row parsing and PDUFA date parsing passed.")

    if view.empty:
        st.info("No PDUFA records match the current filters.")
    else:
        display = table_view(view, return_page="1. ALL PDUFA")
        display.insert(5, "Time", view["time_status"].fillna("Unknown").astype(str).values)

        st.markdown("### MASTER PDUFA TABLE")
        st.caption("LEADING COLUMNS: Ticker | Probability of Approval % — Public | Probability of Approval % — All Sources")
        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=650,
            column_order=list(display.columns),
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this exact PDUFA detail page",
                ),
                "Probability of Approval % — Public": st.column_config.TextColumn(
                    "Probability of Approval % — Public",
                    help="Approval probability calculated from public evidence only",
                    width="medium",
                ),
                "Probability of Approval % — All Sources": st.column_config.TextColumn(
                    "Probability of Approval % — All Sources",
                    help="All-source composite using internal, public, and BiopharmaWatch inputs when available",
                    width="medium",
                ),
                "I+P Consensus": st.column_config.TextColumn(
                    "I+P Consensus",
                    help="50/50 consensus of I App and P App when both are scored",
                    width="small",
                ),
            },
            on_select="rerun",
            selection_mode="single-row",
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = view.iloc[ridx]
            detail_source = safe_text(selected_row.get("_detail_source"), "live")
            detail_key = safe_text(selected_row.get("event_key"), "") if detail_source == "history" else make_event_key(selected_row)
            go_individual(selected_row.get("ticker"), detail_key, source=detail_source, return_page=page)
            st.rerun()

        open1,open2 = st.columns([3,1])
        quick_view = view.copy()
        quick_view["event_key_ui"] = quick_view.apply(make_event_key, axis=1)
        quick_view["event_label_ui"] = quick_view.apply(
            lambda x: f"{safe_text(x.get('ticker'))} · {fmt_app_pct(x.get('approval_probability'), 1)} — {safe_text(x.get('drug'))} — " +
                      ("Date unavailable" if pd.isna(x.get("pdufa_date")) else pd.Timestamp(x.get("pdufa_date")).strftime("%b %d, %Y")),
            axis=1
        )
        with open1:
            quick = st.selectbox(
                "Open a specific PDUFA event",
                quick_view["event_key_ui"].tolist(),
                format_func=lambda k: quick_view.loc[quick_view["event_key_ui"] == k, "event_label_ui"].iloc[0],
                key="master_quick"
            )
        with open2:
            st.write("")
            st.write("")
            if st.button("VIEW INDIVIDUAL →", use_container_width=True, key="master_open"):
                quick_row = quick_view[quick_view["event_key_ui"] == quick].iloc[0]
                detail_source = safe_text(quick_row.get("_detail_source"), "live")
                detail_key = safe_text(quick_row.get("event_key"), "") if detail_source == "history" else quick
                go_individual(quick_row.get("ticker"), detail_key, source=detail_source, return_page=page)
                st.rerun()

        csv_bytes = display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "DOWNLOAD CURRENT MASTER VIEW (.CSV)",
            data=csv_bytes,
            file_name="pdufa_master_filtered.csv",
            mime="text/csv",
        )

    if master["market_cap"].isna().all():
        st.info("Market-cap filtering is ready, but the current saved feed does not yet contain market-cap values. Rows remain visible under Market Cap = All until that field is populated.")
    if master["outcome"].isna().all():
        st.info("FDA outcome filtering is ready. Historical rows will become much more useful once APPROVED / CRL / other final outcomes are added to the master feed.")

elif page == "2. MARKET CAP GROUPS":
    st.markdown("## 2. MARKET CAP GROUPS — Select a Range")
    st.caption("Exact bands require an exact saved market cap. Validated bucket views also include events whose exact market cap has not yet been captured.")

    group_mode = st.radio(
        "Grouping method",
        ["Validated buckets","Exact market-cap bands"],
        horizontal=True,
        key="cap_group_mode"
    )

    if group_mode == "Validated buckets":
        bucket_labels = ["$300M–$1B","$1B–$3B","$3B–$10B"]
        selected_cap = st.radio("Market-cap bucket", bucket_labels, horizontal=True, key="cap_bucket_radio")
        cap_data = future[
            future["market_cap_bucket"].fillna("").astype(str).eq(selected_cap)
        ].copy()

        # If an exact cap is present but bucket text is missing, derive only the
        # broad validated bucket; never guess a finer band.
        if selected_cap == "$300M–$1B":
            exact_fallback = future[
                future["market_cap"].notna() &
                (future["market_cap"] >= 300_000_000) &
                (future["market_cap"] < 1_000_000_000) &
                ~future.index.isin(cap_data.index)
            ]
        elif selected_cap == "$1B–$3B":
            exact_fallback = future[
                future["market_cap"].notna() &
                (future["market_cap"] >= 1_000_000_000) &
                (future["market_cap"] < 3_000_000_000) &
                ~future.index.isin(cap_data.index)
            ]
        else:
            exact_fallback = future[
                future["market_cap"].notna() &
                (future["market_cap"] >= 3_000_000_000) &
                (future["market_cap"] <= 10_000_000_000) &
                ~future.index.isin(cap_data.index)
            ]
        cap_data = pd.concat([cap_data, exact_fallback]).sort_values(["pdufa_date","ticker"])
        st.markdown(f"### {selected_cap} ({len(cap_data)} PDUFA events)")
    else:
        cap_ranges = [
            ("$300M–$500M",300_000_000,500_000_000),
            ("$500M–$750M",500_000_000,750_000_000),
            ("$750M–$1B",750_000_000,1_000_000_000),
            ("$1B–$2B",1_000_000_000,2_000_000_000),
            ("$2B–$3B",2_000_000_000,3_000_000_000),
            ("$3B–$5B",3_000_000_000,5_000_000_000),
            ("$5B–$7.5B",5_000_000_000,7_500_000_000),
            ("$7.5B–$10B",7_500_000_000,10_000_000_001),
        ]
        labels = [x[0] for x in cap_ranges]
        selected_cap = st.radio("Exact market-cap band", labels, horizontal=True, key="cap_exact_radio")
        low,high = next((lo,hi) for label,lo,hi in cap_ranges if label == selected_cap)
        cap_data = future[
            future["market_cap"].notna() &
            (future["market_cap"] >= low) &
            (future["market_cap"] < high)
        ].copy()
        st.markdown(f"### {selected_cap} exact-cap view ({len(cap_data)} PDUFA events)")

    if cap_data.empty:
        if group_mode == "Exact market-cap bands":
            st.info("No future PDUFA events with an exact saved market cap currently fall in this band. Try Validated buckets for events with bucket-only market-cap data.")
        else:
            st.info("No future PDUFA events currently fall in this validated market-cap bucket.")
    else:
        display = table_view(cap_data, return_page="2. MARKET CAP GROUPS")
        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=560,
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this exact PDUFA detail page",
                ),
                "Probability of Approval % — Public": st.column_config.TextColumn("Probability of Approval % — Public", help="Public-only approval probability", width="medium"),
                "Probability of Approval % — All Sources": st.column_config.TextColumn("Probability of Approval % — All Sources", help="All-source approval probability", width="medium"),
            },
            on_select="rerun",
            selection_mode="single-row",
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = cap_data.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row), source="live", return_page=page)
            st.rerun()
        c1,c2 = st.columns([3,1])
        cap_open = cap_data.copy()
        cap_open["event_key_ui"] = cap_open.apply(make_event_key, axis=1)
        cap_open["event_label_ui"] = cap_open.apply(
            lambda x: f"{safe_text(x.get('ticker'))} · {fmt_app_pct(x.get('approval_probability'), 1)} — {safe_text(x.get('drug'))} — " +
                      ("Date unavailable" if pd.isna(x.get("pdufa_date")) else pd.Timestamp(x.get("pdufa_date")).strftime("%b %d, %Y")),
            axis=1
        )
        with c1:
            quick = st.selectbox(
                "Open PDUFA event from this group",
                cap_open["event_key_ui"].tolist(),
                format_func=lambda k: cap_open.loc[cap_open["event_key_ui"] == k, "event_label_ui"].iloc[0],
                key="cap_quick"
            )
        with c2:
            st.write("")
            st.write("")
            if st.button("VIEW INDIVIDUAL →", use_container_width=True, key="cap_open"):
                quick_row = cap_open[cap_open["event_key_ui"] == quick].iloc[0]
                go_individual(quick_row.get("ticker"), quick, source="live", return_page=page)
                st.rerun()

elif page == "3. CALENDAR":
    st.markdown("## 3. PDUFA CALENDAR")
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
        display = table_view(whits, return_page="3. CALENDAR")
        event = st.dataframe(
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
                "I App %": st.column_config.TextColumn("I App %", help="Internal/model approval probability", width="small"),
                "P App %": st.column_config.TextColumn("P App %", help="Public-evidence-only approval probability", width="small"),
            },
            on_select="rerun",
            selection_mode="single-row",
            key=f"calendar_week_table_{st.session_state.calendar_offset_weeks}_{wi}"
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = whits.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row), source="live", return_page="3. CALENDAR")
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
                        f"{pd.Timestamp(r.get('pdufa_date')).strftime('%b %d')}"
                    )
                    calendar_url = html.escape(
                        event_detail_url(r, source="live", return_page="3. CALENDAR"),
                        quote=True
                    )
                    st.markdown(
                        f'<a class="calendar-event-link" href="{calendar_url}" target="_self">{calendar_label}</a>',
                        unsafe_allow_html=True
                    )

elif page == "4. PREDICTION ENGINE":
    st.markdown("## 4. PREDICTION ENGINE — JAN 2025 TO SEP 2026")
    st.caption("Canonical $300M–$10B final historical cohort. 2025 is external/blind holdout; Jan–Sep 2026 is model-development/in-sample and must not be interpreted as independent blind accuracy.")

    hist = prediction_history.copy()
    hist = hist[
        hist["pdufa_date"].notna() &
        (hist["pdufa_date"] >= pd.Timestamp("2025-01-01")) &
        (hist["pdufa_date"] <= pd.Timestamp("2026-09-30"))
    ].copy()
    if "public_approval_probability" not in hist:
        hist["public_approval_probability"] = pd.NA
    hist["Probability of Approval % — Public"] = hist["public_approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
    hist["Probability of Approval % — All Sources"] = hist.apply(lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1)
    hist["I Direction"] = hist.apply(internal_direction_state, axis=1)
    hist["P Direction"] = hist.apply(public_direction_state, axis=1)
    hist["I+P Direction"] = hist.apply(ip_consensus_direction, axis=1)
    hist["All-Source Direction"] = hist.apply(all_source_direction_state, axis=1)
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
        year_pick = st.selectbox("Year", ["All",2025,2026], key="pred_year")
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

    st.markdown("### SCORING COVERAGE")
    c1,c2,c3 = st.columns(3)
    c1.metric("I App Coverage", f"{i_coverage:.1f}%")
    c2.metric("P App Coverage", f"{p_coverage:.1f}%")
    c3.metric("Selected Cases", len(hview))

    st.markdown("### AVERAGE APPROVAL PROBABILITY")
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Avg I App %", "NA" if pd.isna(filtered_avg_i) else f"{filtered_avg_i:.1f}%")
    p2.metric("Avg P App %", "Not scored" if pd.isna(filtered_avg_p) else f"{filtered_avg_p:.1f}%")
    p3.metric("Raw Accuracy", "NA" if hview.empty else f"{filtered_correct.mean()*100:.1f}%")
    p4.metric("Clean-as-is Accuracy", "NA" if audited.empty else f"{audited_correct.mean()*100:.1f}%")
    st.caption("Coverage is completion. Avg I/P App % are probability averages and are not supposed to equal 100%.")

    st.markdown("### DIRECTION ACCURACY")
    audited["I+P Direction"] = audited.apply(ip_consensus_direction, axis=1)
    bpw_dir_called = audited[audited["I+P Direction"].isin(["APPROVED","CRL"])].copy()
    bpw_dir_correct = bpw_dir_called["I+P Direction"].eq(bpw_dir_called["actual_outcome"].astype(str).str.upper())
    bpw_direction_accuracy = float("nan") if bpw_dir_called.empty else bpw_dir_correct.mean() * 100
    bpw_direction_coverage = 0.0 if audited.empty else len(bpw_dir_called) / len(audited) * 100

    d1,d2,d3,d4,d5,d6 = st.columns(6)
    d1.metric("I Direction Accuracy", "NA" if pd.isna(i_direction_accuracy) else f"{i_direction_accuracy:.1f}%")
    d2.metric("I Coverage", f"{i_direction_coverage:.1f}%")
    d3.metric("P Direction Accuracy", "NA" if pd.isna(p_direction_accuracy) else f"{p_direction_accuracy:.1f}%")
    d4.metric("P Coverage", f"{p_direction_coverage:.1f}%")
    d5.metric("I+P Direction Accuracy", "NA" if pd.isna(bpw_direction_accuracy) else f"{bpw_direction_accuracy:.1f}%")
    d6.metric("I+P Coverage", f"{bpw_direction_coverage:.1f}%")
    st.caption("Direction accuracy measures APPROVED vs CRL correctness only on cases actually called. I Direction may use decision-safe internal research and model evidence. P Direction is PUBLIC-ONLY: no I App %, no internal scores, no internal audit labels, and no hidden/internal references may influence it. REVIEW/ABSTAIN is excluded from accuracy and counted against coverage.")

    st.markdown("### 100% HISTORICAL PRECISION MODES")
    z1,z2,z3,z4,z5,z6 = st.columns(6)
    z1.metric("I Correct Accuracy", "NA" if pd.isna(precision_accuracy) else f"{precision_accuracy:.1f}%")
    z2.metric("I Actionable Coverage", f"{precision_coverage:.1f}%")
    z3.metric("I Called Cases", f"{len(precision_called)}/{len(audited)}")
    z4.metric("P Correct Accuracy", "NA" if pd.isna(public_precision_accuracy) else f"{public_precision_accuracy:.1f}%")
    z5.metric("P Actionable Coverage", f"{public_precision_coverage:.1f}%")
    z6.metric("P Called Cases", f"{len(public_called)}/{len(audited)}")
    st.caption(
        "I precision rule: APPROVED only at I App >=95%; otherwise REVIEW/ABSTAIN. "
        "P precision rule: APPROVED at P App >=90%, CRL at P App <=10%, otherwise REVIEW/ABSTAIN. "
        "Both are historical backtests on the clean cohort, not guarantees of future 100% accuracy."
    )

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
        lambda r: event_detail_url(r, source="history", return_page="4. PREDICTION ENGINE"), axis=1
    )
    hview["PDUFA Date"] = hview["pdufa_date"].dt.strftime("%Y-%m-%d")
    hdisplay = hview[[
        "Ticker","Probability of Approval % — Public","Probability of Approval % — All Sources","I Direction","P Direction","All-Source Direction","PDUFA Date","model_class","actual_outcome",
        "Historical Market Cap","market_cap_bucket","Correct / Wrong","V2 Status",
        "audit_status","failure_reason","canonical_pdufa_date","audit_action","needs_rescore",
        "count_in_audited_accuracy","source_url","validation_period","independence_status"
    ]].rename(columns={
        "model_class":"Model Prediction",
        "actual_outcome":"Actual FDA Outcome",
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
    st.caption("FIRST THREE COLUMNS: Ticker | I App % | P App %")
    st.dataframe(
        hdisplay,
        use_container_width=True,
        hide_index=True,
        height=690,
        column_config={
            "Ticker": st.column_config.LinkColumn(
                "Ticker",
                display_text=r"ticker=([^&]+)",
                help="Open this historical PDUFA model case"
            ),
            "Audit Source": st.column_config.LinkColumn(
                "Audit Source",
                display_text="Source",
                help="Primary source used for audited failure classification"
            )
        }
    )

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
                "ticker","original_event_key","canonical_pdufa_date","queue_class",
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

            st.dataframe(
                qdisplay,
                use_container_width=True,
                hide_index=True,
                height=min(700, 120 + 32*len(qdisplay)),
                column_config={
                    "Source": st.column_config.LinkColumn("Source", display_text="Source")
                }
            )

    st.divider()
    st.markdown("### Prediction Engine V2 — Prospective Decision Layer")
    st.caption(
        "V2 is conservative by design: it refuses weak-data calls. It does not rewrite frozen Q4 predictions "
        "or retroactively tune historical probabilities."
    )

    live_v2 = future.copy()
    if live_v2.empty:
        st.info("No future PDUFA rows are currently available for the V2 gate.")
    else:
        gate_results = live_v2.apply(prospective_gate_state, axis=1)
        live_v2["V2 Call"] = [x[0] for x in gate_results]
        live_v2["V2 Confidence"] = [x[1] for x in gate_results]
        live_v2["V2 Gate Reason"] = [x[2] for x in gate_results]
        live_v2["Probability of Approval % — Public"] = live_v2["public_approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
        live_v2["Probability of Approval % — All Sources"] = live_v2.apply(lambda r: fmt_app_pct(all_source_probability_value(r), 1), axis=1)
        live_v2["All-Source Direction"] = live_v2.apply(all_source_direction_state, axis=1)
        live_v2["PDUFA Date"] = live_v2["pdufa_date"].dt.strftime("%Y-%m-%d")
        live_v2["Ticker"] = live_v2.apply(
            lambda r: event_detail_url(r, source="live", return_page="4. PREDICTION ENGINE"), axis=1
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
            "Ticker","Probability of Approval % — Public","Probability of Approval % — All Sources","All-Source Direction","PDUFA Date","drug","indication",
            "V2 Call","V2 Confidence","V2 Gate Reason",
            "pdufa_confirmation","phase3_status","monitor_eligibility","conflict_flag"
        ]].rename(columns={
            "drug":"Drug",
            "indication":"Indication",
            "pdufa_confirmation":"PDUFA Verification",
            "phase3_status":"Phase 3",
            "monitor_eligibility":"Eligibility",
            "conflict_flag":"Conflict"
        })

        st.dataframe(
            v2display,
            use_container_width=True,
            hide_index=True,
            height=min(650, 120 + 34*len(v2display)),
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this future PDUFA detail page"
                )
            }
        )
        st.caption(
            "A high-confidence V2 call requires verified event identity, adequate pivotal evidence, no unresolved conflict, "
            "and complete clinical/regulatory/safety/CMC component scores. Otherwise the engine deliberately returns REVIEW."
        )

else:
    if st.session_state.selected_detail_source == "history":
        hmatches = prediction_history[
            prediction_history["event_key"].astype(str) == str(st.session_state.selected_event_key)
        ]
        if hmatches.empty:
            st.error("Historical PDUFA event not found in the loaded prediction cohort.")
            if st.button("← PREDICTION ENGINE", use_container_width=True):
                go_page("4. PREDICTION ENGINE")
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
                go_page(st.session_state.detail_return_page or "4. PREDICTION ENGINE")
                st.rerun()
        with b2:
            st.caption("Historical Prediction Engine event detail")

        st.markdown(f"## {safe_text(hr.get('ticker'))} · {app_text} — Historical PDUFA")
        st.caption(f"Event key: {safe_text(hr.get('event_key'))}")

        public_hist = hr.get("public_approval_probability", pd.NA)
        public_hist_text = fmt_app_pct(public_hist, 1)
        ip_hist_text = fmt_app_pct(ip_consensus_value(hr), 1)
        bpw_hist_text = fmt_app_pct(hr.get("biopharmawatch_probability"), 1)
        all_hist_text = fmt_app_pct(all_source_probability_value(hr), 1)
        a1,a2,a3,a4,a5,a6,a7,a8,a9,a10 = st.columns(10)
        a1.metric("PDUFA Date", hdate)
        a2.metric("I App %", app_text)
        a3.metric("P App %", public_hist_text)
        a4.metric("BPW %", bpw_hist_text)
        a5.metric("Probability of Approval %", all_hist_text)
        a6.metric("I+P Consensus", ip_hist_text)
        a7.metric("Prediction", safe_text(hr.get("model_class"), "NA"))
        a8.metric("Actual FDA", safe_text(hr.get("actual_outcome"), "NA"))
        a9.metric("Result", correct_text)
        a10.metric("Historical Cap", hcap)

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

    csel,b1,b2,b3 = st.columns([3,1,1,1])
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
        if st.button("← ALL PDUFA", use_container_width=True):
            go_page("1. ALL PDUFA")
            st.rerun()
    with b2:
        st.write("")
        st.write("")
        if st.button("← CALENDAR", use_container_width=True):
            go_page("3. CALENDAR")
            st.rerun()
    with b3:
        st.write("")
        st.write("")
        if st.button("← MARKET CAP", use_container_width=True):
            go_page("2. MARKET CAP GROUPS")
            st.rerun()

    if ordered.empty:
        st.info("No candidates loaded.")
    else:
        r = ordered[ordered["event_key"] == st.session_state.selected_event_key].iloc[0]
        st.markdown(
            f"## {r.ticker} · Public {fmt_app_pct(r.get('public_approval_probability'), 1)} "
            f"· All Sources {fmt_app_pct(all_source_probability_value(r), 1)} — {r.company}"
        )
        st.caption(f"{safe_text(r.get('drug'))} · {safe_text(r.get('indication'))}")
        days_left = None if pd.isna(r.get("pdufa_date")) else int((pd.Timestamp(r.get("pdufa_date")) - today).days)

        k1,k2,k3,k4,k5 = st.columns(5)
        k1.metric("PDUFA Date", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
        k2.metric("Days Left", "Not available" if days_left is None else days_left)
        k3.metric("Probability of Approval % — Public", fmt_app_pct(r.get("public_approval_probability"), 1))
        k4.metric("Probability of Approval % — All Sources", fmt_app_pct(all_source_probability_value(r), 1))
        k5.metric("PDUFA Status", safe_text(r.get("pdufa_confirmation")))

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

            st.info(f"Current tracked stage: **{current_stage}**")

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
                    "Stage": name,
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
            st.dataframe(pipeline_table, use_container_width=True, hide_index=True)

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
            f1,f2,f3 = st.columns(3)
            f1.metric("PDUFA date", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
            f2.metric("Confirmation", safe_text(r.get("pdufa_confirmation")))
            f3.metric("Check status", safe_text(r.get("check_status")))
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
            st.caption("Approval probability and trading attractiveness remain separate.")
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
                pool["I App %"] = pool["_p"].apply(lambda v: fmt_app_pct(v, 1))
                pool["P App %"] = pd.to_numeric(pool.get("public_approval_probability"), errors="coerce").apply(lambda v: fmt_app_pct(v, 1))
                pool["BPW %"] = pd.to_numeric(pool.get("biopharmawatch_probability"), errors="coerce").apply(lambda v: fmt_app_pct(v, 1))
                pool["Probability of Approval %"] = pool.apply(lambda rr: fmt_app_pct(all_source_probability_value(rr), 1), axis=1)
                pool["I+P Consensus"] = pool.apply(lambda rr: fmt_app_pct(ip_consensus_value(rr), 1), axis=1)
                pool["Historical Cap"] = pool["_cap"].apply(
                    lambda v: "NA" if pd.isna(v) else "$" + f"{float(v):.2f}B"
                )
                pool["Result"] = pool["correct"].astype(str).map(
                    {"True":"Correct","False":"Wrong","true":"Correct","false":"Wrong"}
                ).fillna("NA")
                analog_display = pool[[
                    "ticker","PDUFA Date","I App %","P App %","BPW %","Probability of Approval %","I+P Consensus","model_class","actual_outcome",
                    "Historical Cap","market_cap_bucket","Result","audit_status"
                ]].rename(columns={
                    "ticker":"Ticker",
                    "model_class":"Prediction",
                    "actual_outcome":"Actual FDA",
                    "market_cap_bucket":"Cap Bucket",
                    "audit_status":"Audit Status"
                })
                st.dataframe(analog_display, use_container_width=True, hide_index=True)
                if not same_bucket.empty:
                    st.success(f"Showing the closest historical cases from the same market-cap bucket: {current_bucket}.")
                else:
                    st.info("No same-bucket historical cases were available, so the closest loaded cases by approval probability are shown.")

st.divider()
st.caption("FDA probabilities are model estimates, not FDA determinations. Missing fields are labeled Not available or Not scored rather than being invented.")
