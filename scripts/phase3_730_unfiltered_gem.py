#!/usr/bin/env python3
"""Unrestricted GEM JR and GEM research scan over the complete Phase 3 census.
No candidate is excluded by clinical, FDA, financial, technical or legacy membership gates.
Labels mean scan coverage only, not evidence of trial success or trading readiness.
"""
import csv,json
from pathlib import Path
from datetime import datetime,timezone
D=Path(__file__).resolve().parents[1]/"data"
with (D/"phase3_all_years_300m_10b_trials.csv").open(newline="",encoding="utf-8") as f:
 trials=list(csv.DictReader(f))
keys=[(r["ticker"].strip().upper(),r["nct_id"].strip()) for r in trials]
if len(trials)!=730 or len(set(keys))!=730:
 raise RuntimeError("Expected 730 distinct ticker/NCT census rows; refusing to publish stale or duplicated output")
fields=["tier","ticker","nct_id","company","trial_status","trial_url","eligibility_gates","review_status"]
out=[]
for tier in ("GEM JR","GEM"):
 for r in trials:
  out.append({"tier":tier,"ticker":r["ticker"],"nct_id":r["nct_id"],"company":r["company"],"trial_status":r["status"],"trial_url":r["source_url"],"eligibility_gates":"NONE","review_status":"UNFILTERED_RESEARCH_QUEUE"})
with (D/"phase3_730_unfiltered_gem_queues.csv").open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
summary={"generated_at":datetime.now(timezone.utc).isoformat(),"unique_census_trials":len(trials),"gem_jr_unfiltered_review_queue":len(trials),"gem_unfiltered_review_queue":len(trials),"distinct_qualified_gem_jr":None,"distinct_qualified_gem":None,"filters_applied":[],"note":"Each of 730 trials appears in BOTH unrestricted research queues. This is scan coverage, not clinical qualification, verified positive outcome, FDA approval probability, or a trading recommendation. Legacy GEM membership remains unchanged."}
(D/"phase3_730_unfiltered_gem_status.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
