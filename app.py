import streamlit as st
import pandas as pd
from datetime import date
import calendar

st.set_page_config(page_title="PDUFA Command Center",page_icon="🧬",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp{background:#07111e;color:#eef5fb}.block-container{padding-top:1rem;max-width:1550px}
[data-testid="stMetric"]{background:#0d1d2d;border:1px solid #21394f;border-radius:14px;padding:12px}
.card{background:#0d1d2d;border:1px solid #21394f;border-radius:16px;padding:18px;margin:10px 0}
.hero{background:linear-gradient(120deg,#0d1d2d,#103149);border:1px solid #31516d;border-radius:18px;padding:20px}
.muted{color:#94a9bc}.green{color:#32d583}.amber{color:#fdb022}.red{color:#f97066}
.pill{display:inline-block;padding:4px 9px;border:1px solid #34516b;border-radius:99px;margin:0 6px 6px 0;font-size:.78rem}
.small{font-size:.86rem}.section{border-left:3px solid #34516b;padding-left:12px}
a, a:link, a:visited{color:#ffffff !important;text-decoration:none}
a:hover{color:#ffffff !important;text-decoration:underline}
a:active, a:focus{color:#ff8a00 !important}
.stLinkButton a, [data-testid="stLinkButton"] a{color:#ffffff !important}
.stLinkButton a:active, [data-testid="stLinkButton"] a:active{color:#ff8a00 !important}
</style>""",unsafe_allow_html=True)

@st.cache_data(ttl=120)
def load_data():
    x=pd.read_csv("data/pdufa_candidates.csv")
    x["pdufa_date"]=pd.to_datetime(x["pdufa_date"],errors="coerce")
    x["approval_probability"]=pd.to_numeric(x["approval_probability"],errors="coerce")
    for c in ["science_score","regulatory_score","safety_score","cmc_score"]:
        if c in x: x[c]=pd.to_numeric(x[c],errors="coerce")
    return x

df=load_data()
today=pd.Timestamp(date.today())
future=df[df.pdufa_date>=today].copy()
future["days"]=(future.pdufa_date-today).dt.days
future=future.sort_values("pdufa_date")

st.title("PDUFA COMMAND CENTER")
st.caption("FDA decision calendar • Science & efficacy • Regulatory • Safety • CMC • Trading intelligence")
tabs=st.tabs(["OVERVIEW","PDUFA CALENDAR","CANDIDATE INTELLIGENCE","ALL CANDIDATES","SYSTEM"])

with tabs[0]:
    a,b,c,d,e=st.columns(5)
    a.metric("Saved PDUFA Events",len(df))
    b.metric("Next 30 Days",int((future.days<=30).sum()))
    c.metric("Next 90 Days",int((future.days<=90).sum()))
    d.metric("Model Scored",int(df.approval_probability.notna().sum()))
    e.metric("Data As Of","Oct 2, 2026")
    st.markdown("### Next FDA action dates")
    if future.empty: st.info("No future saved PDUFA events in the current feed.")
    else:
        for _,r in future.head(8).iterrows():
            prob=f"{r.approval_probability:.0f}%" if pd.notna(r.approval_probability) else "PENDING"
            st.markdown(f"""<div class="hero"><span class="pill">{int(r.days)} DAYS</span><span class="pill">{r.signal}</span>
            <h2>{r.ticker} · {r.company}</h2><div class="muted">{r.drug} · {r.indication}</div>
            <h3 class="amber">{prob} FDA approval estimate</h3>
            <b>PDUFA:</b> {r.pdufa_date.strftime('%b %d, %Y')}</div>""",unsafe_allow_html=True)
    st.warning("Calendar records are real saved records from your Google Sheet snapshot. Unscored records remain PENDING until the validated research/model feed supplies a probability.")

with tabs[1]:
    st.markdown("### Graphical PDUFA Calendar")
    months=sorted({(d.year,d.month) for d in future.pdufa_date.dropna()})
    opts=[f"{calendar.month_name[m]} {y}" for y,m in months] or [date.today().strftime("%B %Y")]
    choice=st.selectbox("Month",opts)
    mi=opts.index(choice)
    if months: y,m=months[mi]
    else: y,m=date.today().year,date.today().month
    hdr=st.columns(7)
    for col,n in zip(hdr,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): col.markdown(f"**{n}**")
    for week in calendar.Calendar().monthdatescalendar(y,m):
        cols=st.columns(7)
        for col,day in zip(cols,week):
            with col:
                st.markdown(f"**{day.day}**" if day.month==m else f"<span class='muted'>{day.day}</span>",unsafe_allow_html=True)
                hits=df[df.pdufa_date.dt.date==day]
                for _,r in hits.iterrows():
                    st.markdown(f"<div class='card small'><b>{r.ticker}</b><br>{r.company[:22]}<br><span class='amber'>{'Score pending' if pd.isna(r.approval_probability) else f'{r.approval_probability:.0f}%'}</span></div>",unsafe_allow_html=True)

with tabs[2]:
    labels=[f"{r.ticker} — {r.company} — {r.pdufa_date.strftime('%b %d, %Y') if pd.notna(r.pdufa_date) else 'Date unknown'}" for _,r in df.sort_values("pdufa_date").iterrows()]
    pick=st.selectbox("Open candidate",labels)
    r=df.sort_values("pdufa_date").iloc[labels.index(pick)]
    prob=f"{r.approval_probability:.0f}%" if pd.notna(r.approval_probability) else "PENDING"
    st.markdown(f"## {r.ticker} · {r.company}")
    st.markdown(f"<span class='pill'>{r.get('application_type','FDA')}</span><span class='pill'>{r.signal}</span><span class='pill'>{r.confidence} CONFIDENCE</span>",unsafe_allow_html=True)
    p1,p2,p3=st.columns(3); p1.metric("FDA Approval Probability",prob); p2.metric("PDUFA",r.pdufa_date.strftime("%b %d, %Y")); p3.metric("Evidence Cutoff",str(r.evidence_cutoff))
    if pd.notna(r.approval_probability): st.progress(float(r.approval_probability)/100)
    else: st.info("Validated model score has not been loaded for this candidate; no probability is being invented.")
    s1,s2,s3,s4=st.columns(4)
    for col,title,key in [(s1,"Science","science_score"),(s2,"Regulatory","regulatory_score"),(s3,"Safety","safety_score"),(s4,"CMC","cmc_score")]:
        v=r.get(key); col.metric(title,"Pending" if pd.isna(v) else f"{v:.0f}/100")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("### Science & Efficacy")
        st.write(r.get("science_summary") or "Research feed pending.")
        st.markdown("### FDA / Regulatory")
        st.write(r.get("regulatory_summary") or "Research feed pending.")
    with c2:
        st.markdown("### Safety / CMC")
        st.write(r.get("safety_summary","Research feed pending.") or "Research feed pending.")
        st.write(r.get("cmc_summary","Research feed pending.") or "Research feed pending.")
        st.markdown("### Trading Intelligence")
        st.write(r.get("trading_summary") or "Market feed pending.")
    st.markdown("### Evidence & Traceability")
    st.write(r.get("evidence_summary") or "Evidence feed pending.")

with tabs[3]:
    show=df.sort_values("pdufa_date").copy()
    show["PDUFA"]=show.pdufa_date.dt.strftime("%Y-%m-%d")
    show["FDA %"]=show.approval_probability
    st.dataframe(show[["ticker","company","PDUFA","signal","FDA %","confidence"]].rename(columns={"ticker":"Ticker","company":"Company","signal":"Status","confidence":"Confidence"}),use_container_width=True,hide_index=True,height=650)

with tabs[4]:
    st.markdown("### System status")
    st.success("WEB APP: DEPLOYED")
    st.success(f"CALENDAR FEED: {len(df)} saved PDUFA event records loaded")
    st.info("MODEL/DEEP-RESEARCH FEED: awaiting automated export from the Colab/Drive Level-17 system")
    st.markdown("""<div class="card"><b>Data integrity rule</b><br>The web layer does not write into historical research files. Calendar, science, regulatory, CMC, safety and trading outputs are presentation copies. Missing model outputs display as PENDING rather than fabricated values.</div>""",unsafe_allow_html=True)

st.divider()
st.caption("FDA probabilities are model estimates, not FDA determinations. Regulatory probability and trading attractiveness are kept separate.")
