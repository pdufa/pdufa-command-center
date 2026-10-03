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
[data-testid="stMetric"]{background:#0d1d2d;border:1px solid #21394f;border-radius:14px;padding:12px}
.card{background:#0d1d2d;border:1px solid #21394f;border-radius:16px;padding:18px;margin:10px 0}
.hero{background:linear-gradient(120deg,#0d1d2d,#103149);border:1px solid #31516d;border-radius:18px;padding:20px}
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
future = df[df.pdufa_date >= today].copy()
future["days"] = (future.pdufa_date - today).dt.days
future = future.sort_values("pdufa_date")

st.title("PDUFA COMMAND CENTER")
st.caption("FDA decision calendar • Science & efficacy • Regulatory • Safety • CMC • Trading intelligence • Live news")
tabs = st.tabs(
    [
        "OVERVIEW",
        "PDUFA CALENDAR",
        "CANDIDATE INTELLIGENCE",
        "ALL CANDIDATES",
        "NEWS CENTER",
        "SYSTEM",
    ]
)

with tabs[0]:
    a, b, c, d, e = st.columns(5)
    a.metric("Saved PDUFA Events", len(df))
    b.metric("Next 30 Days", int((future.days <= 30).sum()))
    c.metric("Next 90 Days", int((future.days <= 90).sum()))
    d.metric("Model Scored", int(df.approval_probability.notna().sum()))
    e.metric("Data As Of", "Oct 2, 2026")
    st.markdown("### Next FDA action dates")
    if future.empty:
        st.info("No future saved PDUFA events in the current feed.")
    else:
        for _, r in future.head(8).iterrows():
            prob = (
                f"{r.approval_probability:.0f}%"
                if pd.notna(r.approval_probability)
                else "PENDING"
            )
            st.markdown(
                f"""<div class="hero"><span class="pill">{int(r.days)} DAYS</span><span class="pill">{r.signal}</span>
                <h2>{r.ticker} · {r.company}</h2><div class="muted">{r.drug} · {r.indication}</div>
                <h3 class="amber">{prob} FDA approval estimate</h3>
                <b>PDUFA:</b> {r.pdufa_date.strftime('%b %d, %Y')}</div>""",
                unsafe_allow_html=True,
            )
    st.warning(
        "Calendar records are real saved records from your Google Sheet snapshot. "
        "Unscored records remain PENDING until the validated research/model feed supplies a probability."
    )

with tabs[1]:
    st.markdown("### Graphical PDUFA Calendar")
    months = sorted({(d.year, d.month) for d in future.pdufa_date.dropna()})
    opts = [
        f"{calendar.month_name[m]} {y}" for y, m in months
    ] or [date.today().strftime("%B %Y")]
    choice = st.selectbox("Month", opts)
    mi = opts.index(choice)
    if months:
        y, m = months[mi]
    else:
        y, m = date.today().year, date.today().month
    hdr = st.columns(7)
    for col, n in zip(hdr, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        col.markdown(f"**{n}**")
    for week in calendar.Calendar().monthdatescalendar(y, m):
        cols = st.columns(7)
        for col, day in zip(cols, week):
            with col:
                st.markdown(
                    f"**{day.day}**"
                    if day.month == m
                    else f"<span class='muted'>{day.day}</span>",
                    unsafe_allow_html=True,
                )
                hits = df[df.pdufa_date.dt.date == day]
                for _, r in hits.iterrows():
                    score_text = (
                        "Score pending"
                        if pd.isna(r.approval_probability)
                        else f"{r.approval_probability:.0f}%"
                    )
                    st.markdown(
                        f"<div class='card small'><b>{r.ticker}</b><br>{r.company[:22]}<br>"
                        f"<span class='amber'>{score_text}</span></div>",
                        unsafe_allow_html=True,
                    )

with tabs[2]:
    ordered = df.sort_values("pdufa_date")
    labels = [
        f"{r.ticker} — {r.company} — "
        f"{r.pdufa_date.strftime('%b %d, %Y') if pd.notna(r.pdufa_date) else 'Date unknown'}"
        for _, r in ordered.iterrows()
    ]
    pick = st.selectbox("Open candidate", labels)
    r = ordered.iloc[labels.index(pick)]
    prob = (
        f"{r.approval_probability:.0f}%"
        if pd.notna(r.approval_probability)
        else "PENDING"
    )
    st.markdown(f"## {r.ticker} · {r.company}")
    st.markdown(
        f"<span class='pill'>{r.get('application_type','FDA')}</span>"
        f"<span class='pill'>{r.signal}</span>"
        f"<span class='pill'>{r.confidence} CONFIDENCE</span>",
        unsafe_allow_html=True,
    )
    p1, p2, p3 = st.columns(3)
    p1.metric("FDA Approval Probability", prob)
    p2.metric("PDUFA", r.pdufa_date.strftime("%b %d, %Y"))
    p3.metric("Evidence Cutoff", str(r.evidence_cutoff))
    if pd.notna(r.approval_probability):
        st.progress(float(r.approval_probability) / 100)
    else:
        st.info(
            "Validated model score has not been loaded for this candidate; "
            "no probability is being invented."
        )
    s1, s2, s3, s4 = st.columns(4)
    for col, title, key in [
        (s1, "Science", "science_score"),
        (s2, "Regulatory", "regulatory_score"),
        (s3, "Safety", "safety_score"),
        (s4, "CMC", "cmc_score"),
    ]:
        v = r.get(key)
        col.metric(title, "Pending" if pd.isna(v) else f"{v:.0f}/100")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Science & Efficacy")
        st.write(r.get("science_summary") or "Research feed pending.")
        st.markdown("### FDA / Regulatory")
        st.write(r.get("regulatory_summary") or "Research feed pending.")
    with c2:
        st.markdown("### Safety / CMC")
        st.write(r.get("safety_summary", "Research feed pending.") or "Research feed pending.")
        st.write(r.get("cmc_summary", "Research feed pending.") or "Research feed pending.")
        st.markdown("### Trading Intelligence")
        st.write(r.get("trading_summary") or "Market feed pending.")
    st.markdown("### Evidence & Traceability")
    st.write(r.get("evidence_summary") or "Evidence feed pending.")

with tabs[3]:
    show = df.sort_values("pdufa_date").copy()
    show["PDUFA"] = show.pdufa_date.dt.strftime("%Y-%m-%d")
    show["FDA %"] = show.approval_probability
    st.dataframe(
        show[
            ["ticker", "company", "PDUFA", "signal", "FDA %", "confidence"]
        ].rename(
            columns={
                "ticker": "Ticker",
                "company": "Company",
                "signal": "Status",
                "confidence": "Confidence",
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=650,
    )

with tabs[4]:
    st.markdown("### PDUFA News Center")
    st.caption(
        "Live company-specific headlines for the PDUFA names you trade. "
        "Stories are automatically tagged by topic and urgency; classification is a screening aid, not an FDA determination."
    )

    ticker_rows = (
        df.sort_values("pdufa_date")
        .drop_duplicates("ticker")
        .set_index("ticker", drop=False)
    )
    ticker_options = sorted(ticker_rows.index.dropna().astype(str).unique().tolist())

    if "my_trades" not in st.session_state:
        st.session_state["my_trades"] = []

    st.multiselect(
        "MY TRADES — choose the PDUFA stocks you are actively trading",
        ticker_options,
        key="my_trades",
        help="Your selection stays active for this browser session.",
    )

    c_scope, c_days, c_refresh = st.columns([2, 1, 1])
    with c_scope:
        scope = st.radio(
            "News scope",
            ["MY TRADES", "NEXT 90 DAYS", "SINGLE TICKER"],
            horizontal=True,
        )
    with c_days:
        days = st.selectbox("Lookback", [1, 3, 7, 14, 30], index=2)
    with c_refresh:
        st.write("")
        st.write("")
        if st.button("↻ REFRESH NEWS", use_container_width=True):
            fetch_ticker_news.clear()
            st.rerun()

    if scope == "MY TRADES":
        scope_tickers = list(st.session_state["my_trades"])
        if not scope_tickers:
            st.info("Select one or more tickers in MY TRADES to build your trading-news feed.")
    elif scope == "NEXT 90 DAYS":
        scope_tickers = (
            future[future["days"].between(0, 90)]["ticker"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .head(15)
            .tolist()
        )
        if len(scope_tickers) == 15:
            st.caption("Live feed is limited to the first 15 upcoming PDUFA tickers to keep the page fast.")
    else:
        single = st.selectbox("Ticker", ticker_options, key="news_single_ticker")
        scope_tickers = [single]

    categories = [
        "FDA / REGULATORY",
        "CLINICAL",
        "FINANCING / SEC",
        "TRADING",
        "COMPANY",
    ]
    priorities = ["CRITICAL", "IMPORTANT", "ROUTINE"]

    f1, f2 = st.columns(2)
    with f1:
        category_filter = st.multiselect(
            "Categories",
            categories,
            default=categories,
        )
    with f2:
        priority_filter = st.multiselect(
            "Priority",
            priorities,
            default=priorities,
        )

    all_stories = []
    errors = []

    if scope_tickers:
        with st.spinner("Loading live PDUFA news..."):
            for ticker in scope_tickers:
                if ticker not in ticker_rows.index:
                    continue
                row = ticker_rows.loc[ticker]
                company = str(row.get("company", "") or "")
                drug = str(row.get("drug", "") or "")
                stories, error = fetch_ticker_news(
                    ticker=ticker,
                    company=company,
                    drug=drug,
                    days=days,
                )
                all_stories.extend(stories)
                if error:
                    errors.append((ticker, error))

    all_stories.sort(key=lambda s: _story_timestamp(s.get("published")), reverse=True)
    filtered = [
        s
        for s in all_stories
        if s["category"] in category_filter and s["priority"] in priority_filter
    ]

    n_critical = sum(1 for s in filtered if s["priority"] == "CRITICAL")
    n_reg = sum(1 for s in filtered if s["category"] == "FDA / REGULATORY")
    n_fin = sum(1 for s in filtered if s["category"] == "FINANCING / SEC")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stories", len(filtered))
    m2.metric("Critical", n_critical)
    m3.metric("FDA / Regulatory", n_reg)
    m4.metric("Financing / SEC", n_fin)

    if errors:
        with st.expander(f"Feed warnings ({len(errors)})"):
            for ticker, error in errors:
                st.write(f"{ticker}: {error}")

    if scope_tickers and not filtered and not errors:
        st.info("No matching stories were found for the current tickers, filters and lookback window.")

    for story in filtered[:75]:
        priority = story["priority"]
        css = {
            "CRITICAL": "news-critical",
            "IMPORTANT": "news-important",
            "ROUTINE": "news-routine",
        }[priority]
        pclass = {
            "CRITICAL": "red",
            "IMPORTANT": "amber",
            "ROUTINE": "green",
        }[priority]

        published_text = "Time unavailable"
        if story.get("published"):
            try:
                ts = pd.Timestamp(story["published"])
                published_text = ts.strftime("%b %d, %Y • %I:%M %p %Z")
            except Exception:
                pass

        safe_title = html.escape(story["title"])
        safe_ticker = html.escape(story["ticker"])
        safe_source = html.escape(story["source"])
        safe_category = html.escape(story["category"])

        st.markdown(
            f"""<div class="card {css}">
            <span class="pill">{safe_ticker}</span>
            <span class="pill">{safe_category}</span>
            <span class="pill {pclass}">{priority}</span>
            <h3>{safe_title}</h3>
            <div class="muted small">{safe_source} · {published_text}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        if story.get("link"):
            st.link_button("READ SOURCE", story["link"])

with tabs[5]:
    st.markdown("### System status")
    st.success("WEB APP: DEPLOYED")
    st.success(f"CALENDAR FEED: {len(df)} saved PDUFA event records loaded")
    st.success("NEWS CENTER: live ticker-specific RSS/news feed enabled with 15-minute cache")
    st.info(
        "MODEL/DEEP-RESEARCH FEED: awaiting automated export from the Colab/Drive Level-17 system"
    )
    st.markdown(
        """<div class="card"><b>Data integrity rule</b><br>
        The web layer does not write into historical research files. Calendar, science,
        regulatory, CMC, safety and trading outputs are presentation copies. Missing model
        outputs display as PENDING rather than fabricated values. News classification is
        automated and should be verified against the linked source before acting.</div>""",
        unsafe_allow_html=True,
    )

st.divider()
st.caption(
    "FDA probabilities are model estimates, not FDA determinations. "
    "Regulatory probability and trading attractiveness are kept separate."
)
