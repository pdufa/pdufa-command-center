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
.stApp{background:#dff5e1;color:#17301d}.block-container{padding-top:1rem;max-width:1550px}
[data-testid="stMetric"]{background:#ffffff;border:2px solid #000000;border-radius:14px;padding:12px;color:#111111}[data-testid="stMetric"] *{color:#111111 !important}
.card{background:#ffffff;border:2px solid #000000;border-radius:16px;padding:18px;margin:10px 0;color:#111111}
.hero{background:#ffffff;border:2px solid #000000;border-radius:18px;padding:20px;color:#111111}
.news-critical{border-left:4px solid #f97066}.news-important{border-left:4px solid #fdb022}.news-routine{border-left:4px solid #32d583}
.muted{color:#94a9bc}.green{color:#32d583}.amber{color:#fdb022}.red{color:#f97066}
.pill{display:inline-block;padding:4px 9px;border:1px solid #34516b;border-radius:99px;margin:0 6px 6px 0;font-size:.78rem}
.small{font-size:.86rem}.section{border-left:3px solid #34516b;padding-left:12px}
a, a:link, a:visited{color:#ffffff !important;text-decoration:none}
a:hover{color:#ffffff !important;text-decoration:underline}
a:active, a:focus{color:#ff8a00 !important}
.stLinkButton a, [data-testid="stLinkButton"] a{color:#ffffff !important}
.stLinkButton a:active, [data-testid="stLinkButton"] a:active{color:#ff8a00 !important}
</style>""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=120)
def load_data():
    x = pd.read_csv("data/pdufa_candidates.csv")
    x["pdufa_date"] = pd.to_datetime(x["pdufa_date"], errors="coerce")
    x["approval_probability"] = pd.to_numeric(x["approval_probability"], errors="coerce")
    for c in ["science_score", "regulatory_score", "safety_score", "cmc_score"]:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
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
        return "Pending"
    v = float(v)
    if v >= 1_000_000_000:
        return "$" + f"{v/1_000_000_000:.1f}B"
    return "$" + f"{v/1_000_000:.0f}M"

def fmt_pct(v):
    return "Pending" if pd.isna(v) else f"{float(v):.0f}%"

def go_individual(ticker):
    st.session_state.selected_ticker = str(ticker)
    st.session_state.nav = "4. INDIVIDUAL COMPANY"

def table_view(frame):
    out = frame.copy()
    out["PDUFA Date"] = out["pdufa_date"].dt.strftime("%Y-%m-%d")
    out["Days Left"] = (out["pdufa_date"] - today).dt.days
    out["Market Cap"] = out["market_cap"].map(fmt_cap)
    out["PoA"] = out["approval_probability"].map(fmt_pct)
    out["Trade Score"] = out["trade_score"].apply(lambda v: "Pending" if pd.isna(v) else f"{float(v):.0f}")
    out["Financing"] = out["financing_status"].fillna("Pending")
    out["Phase"] = out["setup_phase"].fillna("Pending")
    for c in ["ticker","company","drug","indication"]:
        if c not in out:
            out[c] = ""
    return out.rename(columns={
        "ticker":"Ticker","company":"Company","drug":"Drug","indication":"Indication",
        "short_interest":"Short %","iv_30d":"IV (30d)"
    })[["Ticker","Company","Drug","Indication","PDUFA Date","Days Left","Market Cap",
        "PoA","Trade Score","Financing","Phase","Short %","IV (30d)"]]

if "nav" not in st.session_state:
    st.session_state.nav = "1. ALL PDUFA"
if "selected_ticker" not in st.session_state:
    base = future if not future.empty else df
    st.session_state.selected_ticker = str(base.iloc[0]["ticker"]) if not base.empty else ""
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

st.title("🧬 BIO PDUFA COMMAND CENTER")
st.caption("ALL → MARKET CAP GROUPS → INDIVIDUAL, with direct ALL → INDIVIDUAL navigation and a rolling 4-week PDUFA calendar")

nav_options = ["1. ALL PDUFA","2. MARKET CAP GROUPS","3. CALENDAR","4. INDIVIDUAL COMPANY"]
st.radio("Navigation", nav_options, horizontal=True, key="nav", label_visibility="collapsed")
page = st.session_state.nav

if page == "1. ALL PDUFA":
    st.markdown("## 1. MASTER PDUFA SPREADSHEET — Past + Present + Future")
    st.caption("One sortable master list for every PDUFA case in the saved system. Use the controls above the table to narrow the universe without losing the direct path to the Individual Company page.")

    master = df.copy()
    master["time_status"] = master["pdufa_date"].apply(
        lambda d: "Unknown" if pd.isna(d) else ("Past" if d.date() < date.today() else ("Today" if d.date() == date.today() else "Future"))
    )
    master["year"] = master["pdufa_date"].dt.year
    master["days_from_today"] = (master["pdufa_date"] - today).dt.days

    top1, top2, top3, top4, top5 = st.columns([1.25,1.25,1.25,1.25,2.2])

    with top1:
        status_filter = st.multiselect(
            "Past / Present / Future",
            ["Past","Today","Future","Unknown"],
            default=["Past","Today","Future"]
        )

    with top2:
        years = sorted([int(x) for x in master["year"].dropna().unique()])
        year_filter = st.multiselect("PDUFA Year", years, default=years)

    with top3:
        outcome_values = sorted([str(x) for x in master["outcome"].dropna().unique() if str(x).strip()])
        outcome_filter = st.multiselect(
            "FDA Outcome",
            outcome_values if outcome_values else ["Approved","CRL","Withdrawn","Pending"],
            default=[]
        )

    with top4:
        signal_values = sorted([str(x) for x in master["signal"].dropna().unique()])
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
        financing_values = sorted([str(x) for x in master["financing_status"].dropna().unique()])
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
    if status_filter:
        view = view[view["time_status"].isin(status_filter)]
    if year_filter:
        view = view[view["year"].isin(year_filter)]
    if outcome_filter:
        view = view[view["outcome"].astype(str).isin(outcome_filter)]
    if signal_filter:
        view = view[view["signal"].astype(str).isin(signal_filter)]
    if financing_filter:
        view = view[view["financing_status"].astype(str).isin(financing_filter)]
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
    next_4w_n = int(((master["days_from_today"] >= 0) & (master["days_from_today"] <= 27)).sum())

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("All PDUFA Records", len(master))
    m2.metric("Past", past_n)
    m3.metric("Today", today_n)
    m4.metric("Future", future_n)
    m5.metric("Next 4 Weeks", next_4w_n)

    st.caption(f"Showing {len(view)} of {len(master)} records. Select a row to open its Individual Company page.")

    if view.empty:
        st.info("No PDUFA records match the current filters.")
    else:
        display = table_view(view)
        display.insert(5, "Time", view["time_status"].values)
        if "outcome" in view:
            display.insert(6, "Outcome", view["outcome"].fillna("Pending").astype(str).values)

        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=650,
            on_select="rerun",
            selection_mode="single-row",
        )
        if event.selection.rows:
            go_individual(display.iloc[event.selection.rows[0]]["Ticker"])
            st.rerun()

        open1,open2 = st.columns([3,1])
        with open1:
            quick = st.selectbox("Open a specific company", view["ticker"].astype(str).tolist(), key="master_quick")
        with open2:
            st.write("")
            st.write("")
            if st.button("VIEW INDIVIDUAL →", use_container_width=True, key="master_open"):
                go_individual(quick)
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
    selected_cap = st.radio("Market-cap band", labels, horizontal=True)
    low,high = next((lo,hi) for label,lo,hi in cap_ranges if label == selected_cap)
    cap_data = future[
        future["market_cap"].notna() &
        (future["market_cap"] >= low) &
        (future["market_cap"] < high)
    ].copy()

    st.markdown(f"### {selected_cap} Market Cap ({len(cap_data)} companies)")
    if future["market_cap"].isna().all():
        st.warning("Market-cap data is not yet present in the saved feed. This view will populate automatically when market_cap is supplied.")
    elif cap_data.empty:
        st.info("No future PDUFA candidates currently fall in this band.")
    else:
        display = table_view(cap_data)
        event = st.dataframe(display, use_container_width=True, hide_index=True, height=560,
                             on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            go_individual(display.iloc[event.selection.rows[0]]["Ticker"])
            st.rerun()
        c1,c2 = st.columns([3,1])
        with c1:
            quick = st.selectbox("Open company from this group", cap_data["ticker"].astype(str).tolist(), key="cap_quick")
        with c2:
            st.write("")
            st.write("")
            if st.button("VIEW INDIVIDUAL →", use_container_width=True, key="cap_open"):
                go_individual(quick)
                st.rerun()

elif page == "3. CALENDAR":
    st.markdown("## 3. PDUFA CALENDAR")
    week_sets = []
    for i in range(4):
        start = today + pd.Timedelta(days=7*i)
        end = start + pd.Timedelta(days=6)
        hits = future[(future["pdufa_date"] >= start) & (future["pdufa_date"] <= end)].copy()
        week_sets.append((start,end,hits))

    st.metric("NEXT 4 WEEKS — PDUFA DECISIONS", sum(len(x[2]) for x in week_sets))
    cols = st.columns(4)
    for i,(start,end,hits) in enumerate(week_sets):
        with cols[i]:
            st.metric(f"Week {i+1}: {start.strftime('%b %d')}–{end.strftime('%b %d')}", len(hits))

    week_pick = st.radio("Drill into week", ["Week 1","Week 2","Week 3","Week 4"], horizontal=True)
    wi = int(week_pick[-1]) - 1
    wstart,wend,whits = week_sets[wi]
    st.markdown(f"### {week_pick}: {wstart.strftime('%b %d, %Y')} – {wend.strftime('%b %d, %Y')}")
    if whits.empty:
        st.info("No saved PDUFA events in this week.")
    else:
        display = table_view(whits)
        event = st.dataframe(display, use_container_width=True, hide_index=True,
                             on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            go_individual(display.iloc[event.selection.rows[0]]["Ticker"])
            st.rerun()

    st.divider()
    st.markdown("### Month Calendar")
    months = sorted({(d.year,d.month) for d in future["pdufa_date"].dropna()})
    opts = [f"{calendar.month_name[m]} {y}" for y,m in months] or [date.today().strftime("%B %Y")]
    choice = st.selectbox("Month", opts)
    mi = opts.index(choice)
    y,m = months[mi] if months else (date.today().year,date.today().month)

    hdr = st.columns(7)
    for col,n in zip(hdr,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
        col.markdown(f"**{n}**")
    for week in calendar.Calendar().monthdatescalendar(y,m):
        cols = st.columns(7)
        for col,day in zip(cols,week):
            with col:
                st.markdown(f"**{day.day}**" if day.month == m else f"<span class='muted'>{day.day}</span>", unsafe_allow_html=True)
                hits = df[df["pdufa_date"].dt.date == day]
                for _,r in hits.iterrows():
                    if st.button(f"{r.ticker} · {fmt_pct(r.approval_probability)}",
                                 key=f"cal_{day}_{r.ticker}", use_container_width=True):
                        go_individual(r.ticker)
                        st.rerun()

else:
    ordered = df.sort_values("pdufa_date")
    tickers = ordered["ticker"].dropna().astype(str).drop_duplicates().tolist()
    selected = st.session_state.selected_ticker
    if tickers and selected not in tickers:
        selected = tickers[0]

    csel,b1,b2 = st.columns([3,1,1])
    with csel:
        selected = st.selectbox("Company", tickers, index=tickers.index(selected) if selected in tickers else 0,
                                key="individual_selector")
        st.session_state.selected_ticker = selected
    with b1:
        st.write("")
        st.write("")
        if st.button("← ALL PDUFA", use_container_width=True):
            st.session_state.nav = "1. ALL PDUFA"
            st.rerun()
    with b2:
        st.write("")
        st.write("")
        if st.button("← MARKET CAP", use_container_width=True):
            st.session_state.nav = "2. MARKET CAP GROUPS"
            st.rerun()

    if not tickers:
        st.info("No candidates loaded.")
    else:
        r = ordered[ordered["ticker"].astype(str) == selected].iloc[0]
        st.markdown(f"## {r.ticker} — {r.company}")
        st.caption(f"{r.get('drug','')} · {r.get('indication','')}")
        days_left = None if pd.isna(r.pdufa_date) else int((r.pdufa_date - today).days)

        k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
        k1.metric("Market Cap", fmt_cap(r.market_cap))
        k2.metric("PDUFA Date", "Pending" if pd.isna(r.pdufa_date) else r.pdufa_date.strftime("%b %d, %Y"))
        k3.metric("Days Left", "Pending" if days_left is None else days_left)
        k4.metric("Approval Probability", fmt_pct(r.approval_probability))
        k5.metric("Trade Score", "Pending" if pd.isna(r.trade_score) else f"{float(r.trade_score):.0f}/100")
        k6.metric("Short Interest", fmt_pct(r.short_interest))
        k7.metric("IV (30d)", fmt_pct(r.iv_30d))

        subtabs = st.tabs(["Overview","Pipeline Tracker","PDUFA Timeline","Clinical","FDA","Financing","Trading","News","Scoring","Analogs"])
        with subtabs[0]:
            a,b = st.columns(2)
            with a:
                st.markdown("### Candidate")
                st.write(f"**Drug:** {r.get('drug','Pending')}")
                st.write(f"**Indication:** {r.get('indication','Pending')}")
                st.write(f"**Application:** {r.get('application_type','Pending')}")
                st.write(f"**Setup Phase:** {r.get('setup_phase','Pending')}")
                st.write(f"**Financing:** {r.get('financing_status','Pending')}")
            with b:
                st.markdown("### Evidence")
                st.write(f"**Signal:** {r.get('signal','Pending')}")
                st.write(f"**Confidence:** {r.get('confidence','Pending')}")
                st.write(f"**Evidence cutoff:** {r.get('evidence_cutoff','Pending')}")
                st.write(r.get("evidence_summary") or "Evidence feed pending.")
        with subtabs[1]:
            ptitle, pwatch = st.columns([4,1])
            with ptitle:
                st.markdown("### Development Pipeline — Phase 1 to Now")
                st.caption("One continuous tracker for the selected drug/indication. Exact milestone dates appear when present in the validated feed; unknown dates remain Pending.")
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
                    date_text = "Pending"
                if current_index is not None and i < current_index:
                    icon = "✅"
                    status = "Completed"
                elif current_index is not None and i == current_index:
                    icon = "🔵"
                    status = "Current"
                else:
                    icon = "○"
                    status = "Upcoming / Pending"
                with col:
                    st.markdown(f"### {icon} {name}")
                    st.write(f"**{status}**")
                    st.write(date_text)
                    st.caption(desc)

            st.divider()
            pipeline_table = pd.DataFrame([
                {
                    "Stage": name,
                    "Date": "Pending" if pd.isna(dt) else pd.Timestamp(dt).strftime("%Y-%m-%d"),
                    "Status": (
                        "Completed" if current_index is not None and i < current_index
                        else "Current" if current_index is not None and i == current_index
                        else "Upcoming / Pending"
                    ),
                    "Purpose": desc,
                }
                for i,(name,dt,desc) in enumerate(stages)
            ])
            st.dataframe(pipeline_table, use_container_width=True, hide_index=True)

        with subtabs[2]:
            st.markdown("### PDUFA Timeline")
            st.write("✅ Phase 3 / pivotal evidence")
            st.write("✅ NDA/BLA submission and acceptance when captured")
            st.write("🔵 Current PDUFA window")
            st.write(f"🎯 **PDUFA:** {'Pending' if pd.isna(r.pdufa_date) else r.pdufa_date.strftime('%b %d, %Y')}")
        with subtabs[3]:
            st.markdown("### Clinical")
            st.write(r.get("science_summary") or "Clinical research feed pending.")
            v = r.get("science_score")
            st.metric("Science Score", "Pending" if pd.isna(v) else f"{float(v):.0f}/100")
        with subtabs[4]:
            st.markdown("### FDA / Regulatory")
            st.write(r.get("regulatory_summary") or "Regulatory research feed pending.")
            v = r.get("regulatory_score")
            st.metric("Regulatory Score", "Pending" if pd.isna(v) else f"{float(v):.0f}/100")
        with subtabs[5]:
            st.markdown("### Financing")
            st.metric("Financing Status", str(r.get("financing_status") or "Pending"))
            st.write(r.get("financing_summary") or "Financing detail feed pending.")
        with subtabs[6]:
            st.markdown("### Trading")
            st.write(r.get("trading_summary") or "Trading intelligence feed pending.")
            t1,t2,t3 = st.columns(3)
            t1.metric("Trade Score", "Pending" if pd.isna(r.trade_score) else f"{float(r.trade_score):.0f}/100")
            t2.metric("Short Interest", fmt_pct(r.short_interest))
            t3.metric("IV (30d)", fmt_pct(r.iv_30d))
        with subtabs[7]:
            st.markdown("### Recent News")
            stories,error = fetch_ticker_news(str(r.ticker), str(r.company), str(r.get("drug","")), 14)
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
                col.metric(label, "Pending" if pd.isna(v) else f"{float(v):.0f}/100")
            st.caption("Approval probability and trading attractiveness remain separate.")
        with subtabs[9]:
            st.markdown("### Historical Analogs")
            st.write("Validated analog comparisons will appear here when the analog feed is connected. No result is fabricated.")

st.divider()
st.caption("FDA probabilities are model estimates, not FDA determinations. Missing values remain Pending rather than being invented.")
