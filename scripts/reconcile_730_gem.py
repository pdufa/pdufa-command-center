#!/usr/bin/env python3
"""Reconcile 730 census trials against existing GEM JR/GEM membership by exact NCT ID.
No inference from ticker-only matching. No invented qualifications.
"""
import csv,json
from pathlib import Path
from collections import Counter
D=Path(__file__).resolve().parents[1]/"data"
with (D/"phase3_all_years_300m_10b_trials.csv").open(newline="",encoding="utf-8") as f: trials=list(csv.DictReader(f))
membership=json.loads((D/"gem_stage_membership.json").read_text())
bykey={}
for tier in ("GEM","GEM_JR"):
 for entry in membership["stages"][tier]["entries"].values():
  if entry.get("status")!="ACTIVE":continue
  nct=entry.get("nct_id","");ticker=entry.get("ticker","")
  if nct and ticker:bykey[(ticker,nct)]=tier
rows=[]
for trial in trials:
 tier=bykey.get((trial["ticker"],trial["nct_id"]),"PIPELINE_UNMATCHED")
 rows.append({**trial,"current_gem_stage":tier,"match_basis":"EXACT_TICKER_NCT" if tier!="PIPELINE_UNMATCHED" else "NO_EXISTING_GEM_STAGE_MATCH"})
with (D/"phase3_730_existing_gem_reconciliation.csv").open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["nct_id","ticker","company","status","source_url","current_gem_stage","match_basis"]);w.writeheader();w.writerows(rows)
counts=Counter(x["current_gem_stage"] for x in rows)
status={"census_trials":len(trials),"matched_existing_gem":counts["GEM"],"matched_existing_gem_jr":counts["GEM_JR"],"unmatched_pipeline":counts["PIPELINE_UNMATCHED"],"existing_active_gem":sum(x.get("status")=="ACTIVE" for x in membership["stages"]["GEM"]["entries"].values()),"existing_active_gem_jr":sum(x.get("status")=="ACTIVE" for x in membership["stages"]["GEM_JR"]["entries"].values()),"method":"exact ticker and NCT intersection with existing GEM stage membership; does not requalify trials","note":"This is the actual 730-to-existing-GEM overlap, NOT a fresh 730-trial clinical/financial qualification scan."}
(D/"phase3_730_existing_gem_reconciliation_status.json").write_text(json.dumps(status,indent=2)+"\n")
print(json.dumps(status,indent=2))
