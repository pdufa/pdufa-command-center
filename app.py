import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="PDUFA Command Center", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp {background:#07111f;color:#eaf1f8}
.block-container{padding-top:1.4rem;max-width:1500px}
[data-testid="stMetric"]{background:#0d1b2a;border:1px solid #21354b;border-radius:14px;padding:14px}
.card{background:#0d1b2a;border:1px solid #21354b;border-radius:16px;padding:18px;margin:8px 0}
.muted{color:#91a4b7}.green{color:#31d07f}.amber{color:#ffbd59}.red{color:#ff6b6b}
h1,h2,h3{letter-spacing:-.02em}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    try:
        df=pd.read_csv("data/pdufa_candidates.csv")
        df["pdufa_date"]=pd.to_datetime(df["pdufa_date"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

df=load_data()

st.title("PDUFA COMMAND CENTER")
st.caption("FDA decision intelligence • Science • Regulatory • Safety • CMC • Trading")

c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Candidates", len(df))
if len(df):
    upcoming=df[df["pdufa_date"]>=pd.Timestamp(date.today())].sort_values("pdufa_date")
    c2.metric("Next 7 Days", int(((upcoming["pdufa_date"]-pd.Timestamp(date.today())).dt.days<=7).sum()))
    c3.metric("Next 30 Days", int(((upcoming["pdufa_date"]-pd.Timestamp(date.today())).dt.days<=30).sum()))
    c4.metric("Avg Approval %", f'{df["approval_probability"].mean():.0f}%')
    c5.metric("High Confidence", int((df["confidence"].str.upper()=="HIGH").sum()))
else:
    for c,label in zip([c2,c3,c4,c5],["Next 7 Days","Next 30 Days","Avg Approval %","High Confidence"]): c.metric(label,"—")

st.divider()
left,right=st.columns([1,3])
with left:
    st.subheader("Filters")
    horizon=st.radio("Horizon",["7 Days","30 Days","60 Days","90 Days","All"],index=1)
    q=st.text_input("Search",placeholder="Ticker, drug, company, indication")
    status=st.multiselect("Decision signal",["PASSING","REJECTING","REVIEW"],default=["PASSING","REJECTING","REVIEW"])
with right:
    st.subheader("Upcoming FDA Decisions")
    view=df.copy()
    if len(view):
        if horizon!="All":
            days=int(horizon.split()[0])
            delta=(view["pdufa_date"]-pd.Timestamp(date.today())).dt.days
            view=view[(delta>=0)&(delta<=days)]
        if q:
            mask=view.astype(str).apply(lambda x:x.str.contains(q,case=False,na=False)).any(axis=1)
            view=view[mask]
        if "signal" in view: view=view[view["signal"].isin(status)]
        view=view.sort_values("pdufa_date")
        for _,r in view.iterrows():
            signal=r.get("signal","REVIEW")
            cls="green" if signal=="PASSING" else ("red" if signal=="REJECTING" else "amber")
            st.markdown(f"""<div class="card">
            <h3>{r.get('ticker','')} · {r.get('drug','')}</h3>
            <div class="muted">{r.get('company','')} · {r.get('indication','')}</div>
            <h2 class="{cls}">{signal} — {r.get('approval_probability','—')}%</h2>
            <b>PDUFA:</b> {r['pdufa_date'].strftime('%b %d, %Y') if pd.notna(r['pdufa_date']) else 'Unknown'} &nbsp; • &nbsp;
            <b>Confidence:</b> {r.get('confidence','—')}
            </div>""",unsafe_allow_html=True)
            a,b,c,d=st.columns(4)
            a.metric("Science & Efficacy",f"{r.get('science_score','—')}/100")
            b.metric("Regulatory",f"{r.get('regulatory_score','—')}/100")
            c.metric("Safety",f"{r.get('safety_score','—')}/100")
            d.metric("CMC",f"{r.get('cmc_score','—')}/100")
            with st.expander("Full candidate intelligence"):
                st.markdown("#### Science & Efficacy")
                st.write(r.get("science_summary","Awaiting research feed."))
                st.markdown("#### FDA / Regulatory")
                st.write(r.get("regulatory_summary","Awaiting research feed."))
                st.markdown("#### Trading Intelligence")
                st.write(r.get("trading_summary","Awaiting market feed."))
    else:
        st.info("Dashboard shell is ready. Connect the research export to populate live candidates.")

st.divider()
st.caption("Approval probability and trading attractiveness are intentionally separate. Evidence timestamps and source traceability will be added from the research pipeline.")
