"""Native stage-specific scan checklists on GEM JR and GEM tabs."""
import csv,io
import streamlit as st
from gem_730_requirement_scan import CRITERIA,read_rows,scan

def render_stage_scan(stage):
 if stage not in ("GEM JR","GEM"):raise ValueError("Unknown GEM stage")
 with st.expander(stage+" — REQUIREMENTS CHECKLIST & SCAN",expanded=False):
  st.caption("Select requirements, then click SCAN "+stage+". Every checkbox affects the scan count. Unverified evidence cannot pass a selected requirement.")
  selected=[key for key,label in CRITERIA.items() if st.checkbox(label,key="stage_scan_"+stage+"_"+key,value=False)]
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
