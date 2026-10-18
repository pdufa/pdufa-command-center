"""User-selected GEM JR/GEM requirements over the complete census.
Missing source evidence NEVER passes an enabled requirement.
"""
import csv
from pathlib import Path
from collections import Counter
CRITERIA={
 "phase3_active_or_completed":"Phase 3 active or completed",
 "registry_results_record":"Registry results record found",
 "issuer_positive_source":"Positive issuer Phase 3 source linked",
 "phase3_verified":"Exact-program Phase 3 verified",
 "financing_verified":"Second financing closed",
 "clinical_quality":"Clinical endpoints / safety attested",
 "clinical_conflict":"No clinical/regulatory conflict",
 "cash_runway":"SEC cash runway >=12 months",
 "dilution":"No unresolved dilution",
 "price_base":"Price base / volume verified",
 "market_quote":"Current market activity verified",
 "pdufa_source":"FDA/PDUFA date source verified",
 "pdufa_window":"PDUFA within 30-90 days",
 "hedge_funds":"Specialist fund accumulation",
 "insiders":"Insider open-market purchases",
 "sec_fresh":"Current SEC verification",
 "clinical_fresh":"Current clinical feed"
}
def read_rows(root="data"):
 p=Path(root)
 with (p/"phase3_all_years_300m_10b_trials.csv").open(encoding="utf-8-sig",newline="") as f: census=list(csv.DictReader(f))
 with (p/"phase3_730_full_assessment.csv").open(encoding="utf-8-sig",newline="") as f: assessment=list(csv.DictReader(f))
 indexed={(r["ticker"].upper(),r["nct_id"]):r for r in assessment}
 rows=[]
 for r in census:
  k=(r["ticker"].upper(),r["nct_id"])
  rows.append({**r,**{("evidence_"+key):value for key,value in indexed.get(k,{}).items()}})
 return rows
def evidence(row,key):
 status=row.get("status","").upper()
 if key=="phase3_active_or_completed":
  return status in {"RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION","COMPLETED"}
 if key=="registry_results_record":
  try:return int(row.get("evidence_registry_result_record_count","0"))>0
  except (ValueError,TypeError):return False
 if key=="issuer_positive_source":
  return bool(row.get("evidence_issuer_positive_source","").startswith("https://"))
 # The census and assessment do not establish these other requirements.
 # Missing evidence is unknown, not false clinical outcome.
 return None
def scan(rows,selected):
 unknown=set(selected)-set(CRITERIA)
 if unknown:raise ValueError(f"Unknown requirements: {sorted(unknown)}")
 passed=[];details=[];reason_counts=Counter()
 for r in rows:
  failed=[];unverified=[]
  for key in selected:
   result=evidence(r,key)
   if result is False:failed.append(key)
   if result is None:unverified.append(key)
  for key in failed:reason_counts["NOT_MET: "+key]+=1
  for key in unverified:reason_counts["UNVERIFIED: "+key]+=1
  item={**r,"scan_result":"PASS" if not(failed or unverified) else "NOT_PASSED","not_met":"; ".join(failed),"unverified":"; ".join(unverified)}
  details.append(item)
  if item["scan_result"]=="PASS":passed.append(item)
 return passed,details,dict(reason_counts)
