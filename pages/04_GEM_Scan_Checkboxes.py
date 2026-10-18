"""Independent interactive checklists driving real 730-row GEM JR/GEM scans."""
import csv,io,json
from pathlib import Path
import streamlit as st
from gem_730_requirement_scan import CRITERIA,read_rows,scan
st.title("GEM JR / GEM — Selectable scan requirements")
st.caption("Each selected checkbox is enforced against all census trials. Unchecked = not required. Missing verification does not pass an enabled requirement.")
try:rows=read_rows()
except (OSError,ValueError,csv.Error) as e:
 st.error(f"Census/evidence unavailable: {e}");st.stop()
st.metric("Unique Phase 3 trials to evaluate",len(rows))
selected={}
for tier in ("GEM JR","GEM"):
 with st.expander(tier+" — select requirements",expanded=True):
  selected[tier]=[key for key,label in CRITERIA.items() if st.checkbox(label,key=tier+"_"+key,value=False)]
if st.button("RUN BOTH SCANS — ALL TRIALS",type="primary"):
 st.session_state["gem_730_selected"]=selected
if "gem_730_selected" in st.session_state:
 config=st.session_state["gem_730_selected"]
 results={}
 for tier in ("GEM JR","GEM"):
  passed,details,reasons=scan(rows,config[tier])
  results[tier]={"count":len(passed),"details":details,"reasons":reasons}
 a,b=st.columns(2)
 a.metric("GEM JR passing",results["GEM JR"]["count"])
 b.metric("GEM passing",results["GEM"]["count"])
 st.caption("Counts are independent; a trial may pass both. No filters = all trials pass. This is evidence screening, not a trade signal.")
 for tier in ("GEM JR","GEM"):
  with st.expander(tier+" — all trial outcomes",expanded=False):
   st.write("Selected requirements:",", ".join(CRITERIA[k] for k in config[tier]) or "None")
   st.dataframe(results[tier]["details"],use_container_width=True,hide_index=True)
   if results[tier]["reasons"]:st.json(results[tier]["reasons"])
   buf=io.StringIO()
   writer=csv.DictWriter(buf,fieldnames=list(results[tier]["details"][0]))
   writer.writeheader();writer.writerows(results[tier]["details"])
   st.download_button("Download "+tier+" complete scan",buf.getvalue(),file_name=tier.lower().replace(" ","_")+"_730_scan.csv",mime="text/csv")
 st.download_button("Download both scan configurations",json.dumps({"selected":config,"counts":{tier:results[tier]["count"] for tier in results}},indent=2),file_name="gem_730_scan_config.json",mime="application/json")
