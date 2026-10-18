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
# Presentation-only sections, used by both GEM and GEM JR. A criterion may
# appear in exactly one section; selected keys and the underlying scan are
# unchanged. PDUFA source verification stays with the regulatory checks,
# while the optional 30-90-day TRADING window is grouped with market timing.
TRADING_CRITERION_KEYS=(
 "cash_runway","dilution","price_base","market_quote","pdufa_window",
 "hedge_funds","insiders"
)
TRIAL_CRITERIA={key:label for key,label in CRITERIA.items()
                if key not in TRADING_CRITERION_KEYS}
TRADING_CRITERIA={key:CRITERIA[key] for key in TRADING_CRITERION_KEYS}
assert set(TRIAL_CRITERIA).isdisjoint(TRADING_CRITERIA)
assert set(TRIAL_CRITERIA)|set(TRADING_CRITERIA)==set(CRITERIA)

def read_rows(root="data"):
 p=Path(root)
 with (p/"phase3_all_years_300m_10b_trials.csv").open(encoding="utf-8-sig",newline="") as f: census=list(csv.DictReader(f))
 with (p/"phase3_730_full_assessment.csv").open(encoding="utf-8-sig",newline="") as f: assessment=list(csv.DictReader(f))
 indexed={(r["ticker"].upper(),r["nct_id"]):r for r in assessment}
 events={}
 ep=p/"pdufa_candidates.csv"
 if ep.exists():
  with ep.open(encoding="utf-8-sig",newline="") as f:
   for e in csv.DictReader(f):
    k=(e.get("ticker","").upper(),e.get("nct_id",""))
    if k[0] and k[1]:
     events.setdefault(k,[]).append(e)
 finance={}
 fp=p/"second_financing_status.csv"
 if fp.exists():
  with fp.open(encoding="utf-8-sig",newline="") as f:
   finance={e.get("event_key",""):e for e in csv.DictReader(f)}
 rows=[]
 for r in census:
  k=(r["ticker"].upper(),r["nct_id"])
  matches=events.get(k,[])
  event=matches[0] if len(matches)==1 else {}
  funding=finance.get(event.get("event_key",""),{})
  rows.append({**r,**{("evidence_"+key):value for key,value in indexed.get(k,{}).items()},
   **{("event_"+key):value for key,value in event.items()},
   **{("finance_"+key):value for key,value in funding.items()},
   "exact_event_unique":len(matches)==1})
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
 if key=="phase3_verified":
  if not row.get("exact_event_unique"):return None
  status=row.get("event_phase3_status","").upper()
  if status in {"PRIMARY_MET_VERIFIED","VERIFIED_SUCCESS"} and row.get("event_trial_evidence_url","").startswith("https://"):return True
  return None
 if key=="financing_verified":
  if not row.get("exact_event_unique"):return None
  if (row.get("finance_second_financing_audit_status")=="VERIFIED_SECOND_POST_PHASE3_FINANCING"
      and row.get("finance_second_financing_source","").startswith("https://")):return True
  return None
 if key=="pdufa_source":
  if not row.get("exact_event_unique"):return None
  if row.get("event_pdufa_confirmation","").startswith("VERIFIED") and row.get("event_pdufa_evidence_url","").startswith("https://"):return True
  return None
 if key=="pdufa_window":
  if not row.get("exact_event_unique"):return None
  from datetime import date
  if not (row.get("event_pdufa_confirmation","").startswith("VERIFIED") and row.get("event_pdufa_evidence_url","").startswith("https://")):return None
  try:days=(date.fromisoformat(row["event_pdufa_date"])-date.today()).days
  except (ValueError,KeyError):return None
  return 30<=days<=90
 if key=="cash_runway":
  if not row.get("exact_event_unique"):return None
  # A cash balance without quarterly burn and a dated SEC source is not a runway.
  return None
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
