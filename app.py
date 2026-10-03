import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar

st.set_page_config(page_title="PDUFA Command Center", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp{background:#06101d;color:#edf4fb}.block-container{padding-top:1.2rem;max-width:1500px}
[data-testid="stMetric"]{background:#0c1b2b;border:1px solid #20364c;border-radius:14px;padding:12px}
.card{background:#0c1b2b;border:1px solid #20364c;border-radius:16px;padding:18px;margin:8px 0}
.hero{background:linear-gradient(120deg,#0c1b2b,#102a3e);border:1px solid #28435c;border-radius:18px;padding:20px}
.muted{color:#91a7bb}.green{color:#32d583}.amber{color:#fdb022}.red{color:#f97066}
.pill{display:inline-block;padding:4px 9px;border:1px solid #34506a;border-radius:99px;margin-right:6px;font-size:.8rem}
h1,h2,h3{letter-spacing:-.02em}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    df=pd.read_csv("data/pdufa_candidates.csv")
    df["pdufa_date"]=pd.to_datetime(df["pdufa_date"],errors="coerce")
    return df

try: df=load_data()
except Exception: df=pd.DataFrame()

today=pd.Timestamp(date.today())
st.title("PDUFA COMMAND CENTER")
st.caption("FDA decision intelligence • Science & Efficacy • Regulatory • Safety • CMC • Trading")

tabs=st.tabs(["COMMAND CENTER","CALENDAR","CANDIDATE INTELLIGENCE","RESEARCH STATUS"])

with tabs[0]:
    m1,m2,m3,m4,m5=st.columns(5)
    m1.metric("Tracked",len(df))
    upcoming=df[df.pdufa_date>=today] if len(df) else df
    m2.metric("Next 7 Days",int(((upcoming.pdufa_date-today).dt.days<=7).sum()) if len(upcoming) else 0)
    m3.metric("Next 30 Days",int(((upcoming.pdufa_date-today).dt.days<=30).sum()) if len(upcoming) else 0)
    m4.metric("Passing",int((df.signal=="PASSING").sum()) if len(df) else 0)
    m5.metric("High Confidence",int((df.confidence.str.upper()=="HIGH").sum()) if len(df) else 0)

    st.divider()
    left,right=st.columns([1,3])
    with left:
        st.subheader("Filters")
        horizon=st.radio("Horizon",["7 Days","30 Days","60 Days","90 Days","All"],index=4)
        q=st.text_input("Search",placeholder="Ticker, drug, company, indication")
        statuses=st.multiselect("Signal",["PASSING","REJECTING","REVIEW"],default=["PASSING","REJECTING","REVIEW"])
    with right:
        st.subheader("Upcoming FDA Decisions")
        view=df.copy()
        if len(view):
            if horizon!="All":
                days=int(horizon.split()[0]); delta=(view.pdufa_date-today).dt.days
                view=view[(delta>=0)&(delta<=days)]
            if q: view=view[view.astype(str).apply(lambda x:x.str.contains(q,case=False,na=False)).any(axis=1)]
            view=view[view.signal.isin(statuses)].sort_values("pdufa_date")
            if view.empty: st.info("No candidates match the current filters.")
            for _,r in view.iterrows():
                cls={"PASSING":"green","REJECTING":"red"}.get(r.signal,"amber")
                st.markdown(f"""<div class="hero"><span class="pill">{r.get('application_type','FDA')}</span>
                <span class="pill">{r.get('confidence','—')} CONFIDENCE</span>
                <h2>{r.ticker} · {r.drug}</h2><div class="muted">{r.company} · {r.indication}</div>
                <h1 class="{cls}">{r.signal} — {r.approval_probability}%</h1>
                <b>PDUFA:</b> {r.pdufa_date.strftime('%b %d, %Y') if pd.notna(r.pdufa_date) else 'Unknown'}
                &nbsp; • &nbsp; <b>Evidence cutoff:</b> {r.get('evidence_cutoff','Not connected')}</div>""",unsafe_allow_html=True)
                a,b,c,d=st.columns(4)
                a.metric("Science & Efficacy",f"{r.get('science_score','—')}/100")
                b.metric("FDA / Regulatory",f"{r.get('regulatory_score','—')}/100")
                c.metric("Safety",f"{r.get('safety_score','—')}/100")
                d.metric("CMC",f"{r.get('cmc_score','—')}/100")

with tabs[1]:
    st.subheader("PDUFA Calendar")
    st.caption("Calendar entries are populated from the candidate data feed; dates should be source-verified before being treated as confirmed.")
    month=st.date_input("Month",value=date.today().replace(day=1))
    y,m=month.year,month.month
    cal=calendar.Calendar(firstweekday=0).monthdatescalendar(y,m)
    st.markdown(f"### {calendar.month_name[m]} {y}")
    hdr=st.columns(7)
    for col,name in zip(hdr,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): col.markdown(f"**{name}**")
    for week in cal:
        cols=st.columns(7)
        for col,day in zip(cols,week):
            with col:
                st.markdown(f"**{day.day}**" if day.month==m else f"<span class='muted'>{day.day}</span>",unsafe_allow_html=True)
                if len(df):
                    hits=df[df.pdufa_date.dt.date==day]
                    for _,r in hits.iterrows():
                        st.caption(f"{r.ticker} · {r.drug} · {r.approval_probability}%")

with tabs[2]:
    st.subheader("Candidate Intelligence")
    if len(df):
        labels=[f"{r.ticker} — {r.drug}" for _,r in df.sort_values("pdufa_date").iterrows()]
        pick=st.selectbox("Candidate",labels)
        r=df.sort_values("pdufa_date").iloc[labels.index(pick)]
        st.markdown(f"## {r.ticker} · {r.drug}")
        st.write(f"**{r.company}** — {r.indication}")
        p1,p2,p3=st.columns(3)
        p1.metric("FDA Approval Probability",f"{r.approval_probability}%")
        p2.metric("Signal",r.signal)
        p3.metric("Confidence",r.confidence)
        st.progress(min(max(float(r.approval_probability)/100,0),1))
        st.markdown("### Science & Efficacy")
        st.write(r.get("science_summary","Awaiting research feed."))
        st.markdown("### FDA / Regulatory")
        st.write(r.get("regulatory_summary","Awaiting research feed."))
        st.markdown("### Safety & CMC")
        st.write(r.get("safety_summary","Awaiting research feed."))
        st.write(r.get("cmc_summary","Awaiting research feed."))
        st.markdown("### Trading Intelligence — Separate from FDA Probability")
        st.write(r.get("trading_summary","Awaiting market feed."))
        st.markdown("### Evidence & Traceability")
        st.write(f"Evidence cutoff: **{r.get('evidence_cutoff','Not connected')}**")
        st.write(r.get("evidence_summary","Source-level evidence links will appear here when the research feed is connected."))

with tabs[3]:
    st.subheader("Research Pipeline Status")
    st.markdown("""<div class="card"><h3>Presentation layer: LIVE</h3>
    <p>The Streamlit front end is deployed from GitHub.</p></div>""",unsafe_allow_html=True)
    st.markdown("""<div class="card"><h3>Research feed: NOT YET CONNECTED</h3>
    <p>The dashboard currently reads the repository CSV. The next integration is a machine-readable export from the Google Drive / Colab research system.</p></div>""",unsafe_allow_html=True)
    st.markdown("""<div class="card"><h3>Guardrail</h3>
    <p>Historical research files remain untouched. Demo data is visibly non-production and must not be interpreted as a real FDA forecast.</p></div>""",unsafe_allow_html=True)

st.divider()
st.caption("FDA probability is an evidence-based estimate, not an FDA determination. Trading attractiveness is modeled separately from regulatory probability.")
