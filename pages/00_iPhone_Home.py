import streamlit as st

st.set_page_config(page_title="PDUFA Mobile", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp{background:#dff5e1;color:#111}
.block-container{max-width:760px;padding:.8rem .7rem 5rem}
[data-testid="stSidebar"]{display:none}
.mobile-hero{background:#fff;border:2px solid #000;border-radius:18px;padding:18px;margin:6px 0 16px}
.mobile-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.mobile-tile{display:flex;min-height:86px;align-items:center;justify-content:center;text-align:center;
background:#fff;border:2px solid #000;border-radius:16px;padding:12px;font-size:17px;font-weight:800}
.mobile-tile,.mobile-tile:link,.mobile-tile:visited{color:#111!important;text-decoration:none!important}
.mobile-tile:active{background:#ff8a00;color:#fff!important}
.install{background:#fff;border:2px solid #000;border-radius:14px;padding:14px;margin-top:14px}
@media(max-width:430px){.block-container{padding:.55rem .55rem 4rem}.mobile-tile{min-height:78px;font-size:16px}}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="mobile-hero"><h2 style="margin:0">🧬 PDUFA Command Center</h2>
<div style="margin-top:6px">iPhone launcher</div></div>""", unsafe_allow_html=True)

base = "/"
items = [
    ("🧬 PDUFA PIPELINE", base),
    ("🎯 Decision", base),
    ("📋 All PDUFA", base),
    ("💰 Market Cap", base),
    ("📅 Calendar", base),
    ("🧠 Prediction Engine", base),
    ("🔎 Scans", base),
    ("🔄 Recheck", base),
    ("🏛️ FDA Engine", base),
    ("📝 Plan", base),
]
html = '<div class="mobile-grid">' + ''.join(
    f'<a class="mobile-tile" href="{url}" target="_self">{label}</a>' for label,url in items
) + '</div>'
st.markdown(html, unsafe_allow_html=True)

st.markdown("""<div class="install"><b>Add to iPhone Home Screen</b><br>
Open this page in Safari → Share → <b>Add to Home Screen</b>. Name it <b>PDUFA</b>.
It will launch from your Home Screen like an app while keeping the existing Streamlit system intact.</div>""", unsafe_allow_html=True)

st.caption("Mobile shell only. The existing prediction engine and data remain unchanged.")
