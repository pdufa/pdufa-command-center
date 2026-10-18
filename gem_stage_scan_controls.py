"""Native stage-specific scan checklists on GEM JR and GEM tabs."""
import csv,io
import streamlit as st
from gem_730_requirement_scan import CRITERIA,TRIAL_CRITERIA,TRADING_CRITERIA,read_rows,scan

def render_stage_scan(stage):
 if stage not in ("GEM JR","GEM"):raise ValueError("Unknown GEM stage")
 with st.expander(stage+" — REQUIREMENTS CHECKLIST & SCAN",expanded=False):
  st.caption("Select requirements, then click SCAN "+stage+". Every checkbox affects the scan count. Unverified evidence cannot pass a selected requirement.")
  selected=[]
  with st.expander("TRIAL / CLINICAL / REGULATORY CHECKBOXES",expanded=True):
   st.caption("Clinical trials, exact-program evidence, financing verification, and source checks.")
   for key,label in TRIAL_CRITERIA.items():
    if st.checkbox(label,key="stage_scan_"+stage+"_"+key,value=False):
     selected.append(key)
  with st.expander("TRADING",expanded=False):
   st.caption("Optional market, financing-risk, timing and accumulation requirements. "
              "Selected Trading checkboxes combine with the clinical checks in ONE scan; "
              "an unverified item cannot pass.")
   for key,label in TRADING_CRITERIA.items():
    if st.checkbox(label,key="stage_scan_"+stage+"_"+key,value=False):
     selected.append(key)
  if st.button("SCAN "+stage+" — ALL 730 TRIALS",key="stage_scan_button_"+stage,type="primary"):
   try:
    rows=read_rows()
    passed,details,reasons=scan(rows,selected)
    st.session_state["stage_scan_result_"+stage]={"total":len(rows),"count":len(passed),"details":details,"reasons":reasons,"selected":list(selected)}
   except (OSError,ValueError,csv.Error) as e:
    st.error("Scan could not run: "+str(e))
  result=st.session_state.get("stage_scan_result_"+stage)
  if result:
   st.metric(stage+" passed",str(result["count"])+" / "+str(result["total"]))
   st.caption("Results from last button click. No selection = no requirement filters. This is a saved-evidence scan, not a live collector.")
   st.write("Applied requirements:",", ".join(CRITERIA[k] for k in result["selected"]) or "None")
   if result["reasons"]:st.json(result["reasons"])
   st.dataframe(result["details"],use_container_width=True,hide_index=True)
   buf=io.StringIO()
   writer=csv.DictWriter(buf,fieldnames=list(result["details"][0]))
   writer.writeheader();writer.writerows(result["details"])
   st.download_button("Download "+stage+" scan results",buf.getvalue(),file_name=stage.lower().replace(" ","_")+"_scan.csv",mime="text/csv",key="stage_scan_export_"+stage)
