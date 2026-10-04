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
        "approval_probability","science_score","regulatory_score","safety_score",
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
    return x


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
    if pd.isna(v):
        return "NA"
    x = float(v)
    if 0 <= x <= 1:
        x *= 100
    return f"{x:.{decimals}f}%"

def fmt_num(v, decimals=0):
    if pd.isna(v):
        return "Not available"
    return f"{float(v):,.{decimals}f}"

def safe_text(v, default="Not available"):
    if v is None or pd.isna(v):
        return default
    s = str(v).strip()
    return default if not s or s.lower() in ["nan", "none", "<na>"] else s

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

def event_detail_url(row):
    return APP_BASE_URL + "?" + urllib.parse.urlencode({
        "page": "detail",
        "event": make_event_key(row),
        "ticker": safe_text(row.get("ticker"), ""),
    })

df["event_key"] = df.apply(make_event_key, axis=1)

def go_page(page_name):
    # Store destination before touching query params so a query-param rerun
    # cannot lose the requested navigation target.
    st.session_state._pending_nav = page_name
    if len(st.query_params):
        st.query_params.clear()

def go_individual(ticker=None, event_key=None):
    if ticker is not None:
        st.session_state.selected_ticker = str(ticker)
    if event_key is not None:
        st.session_state.selected_event_key = str(event_key)
    go_page("4. INDIVIDUAL COMPANY")

def table_view(frame):
    out = frame.copy()

    # Guarantee every master-table column exists even if the source feed is incomplete.
    defaults = {
        "ticker":"", "company":"Not available", "drug":"Not available", "indication":"Not available",
        "pdufa_date":pd.NaT, "market_cap":pd.NA, "market_cap_bucket":"Not available",
        "approval_probability":pd.NA, "trade_score":pd.NA, "financing_status":"Not available",
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
    out["Ticker Link"] = out.apply(event_detail_url, axis=1)
    out["Market Cap"] = out["market_cap"].map(fmt_cap)
    out["Cap Bucket"] = out["market_cap_bucket"].fillna("Not available").astype(str)
    out["PoA"] = out["approval_probability"].apply(lambda v: fmt_app_pct(v, 1))
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

    for c in ["ticker","company","drug","indication"]:
        out[c] = out[c].fillna("Not available").astype(str)

    return out.rename(columns={
        "company":"Company","drug":"Drug","indication":"Indication",
        "PoA":"App %","Ticker Link":"Ticker"
    })[[
        "Ticker","App %","Company","Drug","Indication","PDUFA Date","Days Left","Market Cap",
        "Cap Bucket","Trade Score","Outcome","Signal","Confidence","Application",
        "Financing","Phase","Short %","IV (30d)"
    ]]

query_event = st.query_params.get("event")
query_ticker = st.query_params.get("ticker")
query_page = st.query_params.get("page")

# Deep links are consumed once. Clear them immediately after copying the
# destination into session state so stale ?page=detail parameters cannot trap
# the user on the Individual Company page or break return navigation.
if query_page == "detail" and query_event:
    st.session_state.selected_event_key = str(query_event)
    if query_ticker:
        st.session_state.selected_ticker = str(query_ticker)
    st.session_state._pending_nav = "4. INDIVIDUAL COMPANY"
    st.query_params.clear()

if "nav" not in st.session_state:
    st.session_state.nav = "1. ALL PDUFA"
if "selected_ticker" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_ticker = str(base.iloc[0]["ticker"]) if not base.empty else ""
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "selected_event_key" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_event_key = make_event_key(base.iloc[0]) if not base.empty else ""

st.title("🧬 BIO PDUFA COMMAND CENTER")
st.caption("ALL → MARKET CAP GROUPS → INDIVIDUAL, with direct ALL → INDIVIDUAL navigation and a rolling 4-week PDUFA calendar")

# Apply deferred navigation before creating the bound radio widget.
if "_pending_nav" in st.session_state:
    st.session_state.nav = st.session_state.pop("_pending_nav")

nav_options = ["1. ALL PDUFA","2. MARKET CAP GROUPS","3. CALENDAR","4. INDIVIDUAL COMPANY"]
st.radio("Navigation", nav_options, horizontal=True, key="nav", label_visibility="collapsed")
page = st.session_state.nav
if page != "4. INDIVIDUAL COMPANY" and len(st.query_params):
    st.query_params.clear()

if page == "1. ALL PDUFA":
    st.markdown("## 1. MASTER PDUFA SPREADSHEET — Past + Present + Future")
    st.caption("One sortable master list for every PDUFA case in the saved system. Use the controls above the table to narrow the universe without losing the direct path to the Individual Company page.")

    master = df.copy()
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
        min_poa = st.slider("Minimum Approval Probability", 0, 100, 0)

    with row2c:
        min_trade = st.slider("Minimum Trade Score", 0, 100, 0)

    with row2d:
        financing_values = sorted(master["financing_display"].dropna().astype(str).unique().tolist())
        financing_filter = st.multiselect("Financing", financing_values, default=[])

    with row2e:
        sort_choice = st.selectbox(
            "Sort",
            ["PDUFA date ↑","PDUFA date ↓","Market cap ↓","Approval probability ↓","Trade score ↓","Ticker A–Z"]
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
    elif sort_choice == "Approval probability ↓":
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

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("All PDUFA Records", len(master))
    m2.metric("Past", past_n)
    m3.metric("Present / Active", active_n)
    m4.metric("Today", today_n)
    m5.metric("Future", future_n)
    m6.metric("Next 4 Weeks", next_4w_n)

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
        display = table_view(view)
        display.insert(5, "Time", view["time_status"].fillna("Unknown").astype(str).values)

        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=650,
            column_config={
                "Ticker": st.column_config.LinkColumn(
                    "Ticker",
                    display_text=r"ticker=([^&]+)",
                    help="Open this exact PDUFA detail page",
                )
            },
            on_select="rerun",
            selection_mode="single-row",
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = view.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row))
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
                go_individual(quick_row.get("ticker"), quick)
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
        display = table_view(cap_data)
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
                )
            },
            on_select="rerun",
            selection_mode="single-row",
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = cap_data.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row))
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
                go_individual(quick_row.get("ticker"), quick)
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
        display = table_view(whits)
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
                )
            },
            on_select="rerun",
            selection_mode="single-row",
            key=f"calendar_week_table_{st.session_state.calendar_offset_weeks}_{wi}"
        )
        if event.selection.rows:
            ridx = event.selection.rows[0]
            selected_row = whits.iloc[ridx]
            go_individual(selected_row.get("ticker"), make_event_key(selected_row))
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
                    st.link_button(
                        f"{r.ticker} · {fmt_app_pct(r.get('approval_probability'), 1)} · {pd.Timestamp(r.get('pdufa_date')).strftime('%b %d')}",
                        event_detail_url(r),
                        use_container_width=True,
                        help="Open this exact PDUFA detail page"
                    )

else:
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
        st.markdown(f"## {r.ticker} · {fmt_app_pct(r.get('approval_probability'), 1)} — {r.company}")
        st.caption(f"{safe_text(r.get('drug'))} · {safe_text(r.get('indication'))}")
        days_left = None if pd.isna(r.get("pdufa_date")) else int((pd.Timestamp(r.get("pdufa_date")) - today).days)

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("PDUFA Date", "Not available" if pd.isna(r.get("pdufa_date")) else pd.Timestamp(r.get("pdufa_date")).strftime("%b %d, %Y"))
        k2.metric("Days Left", "Not available" if days_left is None else days_left)
        k3.metric("App %", fmt_app_pct(r.get("approval_probability"), 1))
        k4.metric("PDUFA Status", safe_text(r.get("pdufa_confirmation")))

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
            st.write("Validated analog comparisons will appear here when the analog feed is connected. No result is fabricated.")

st.divider()
st.caption("FDA probabilities are model estimates, not FDA determinations. Missing fields are labeled Not available or Not scored rather than being invented.")
