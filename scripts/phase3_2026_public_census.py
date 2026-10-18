#!/usr/bin/env python3
"""2026 positive Phase 3 publicly listed issuer census; fail closed on unverified claims.
Registry postings are NOT evidence that a primary endpoint succeeded.
"""
import csv,json,re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
D=Path(__file__).resolve().parents[1]/"data"
OUT=D/"phase3_2026_public_census.csv"
STATUS=D/"phase3_2026_public_census_status.json"
def read(name):
 p=D/name
 if not p.exists(): return []
 with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
rows=read("phase3_announcements.csv")
registry=read("company_registry.csv")
listed={r.get("ticker","").upper().strip() for r in registry if r.get("ticker")}
accepted=[];review=[];reasons=Counter()
for r in rows:
 ticker=r.get("ticker","").upper().strip()
 date=r.get("phase3_results_posted_at","")[:10]
 source=r.get("phase3_results_source","").strip()
 source_type=r.get("source_type","").strip()
 outcome=(r.get("phase3_result","")+" "+r.get("phase3_status","")+" "+r.get("verification_status","")).upper()
 if not date.startswith("2026-"):reasons["outside_2026_or_undated"]+=1;continue
 if not ticker or ticker not in listed:reasons["no_confirmed_registry_ticker"]+=1;continue
 if not source:reasons["missing_source"]+=1;continue
 item={k:r.get(k,"") for k in ["ticker","company","drug","indication","nct_id","phase3_results_posted_at","phase3_result","phase3_status","verification_status","phase3_results_source","source_type"]}
 # A registry posting is not a dated issuer announcement and does not prove endpoint success.
 if source_type!="ISSUER_TOPLINE_RELEASE":
  reasons["registry_posting_not_issuer_readout"]+=1;review.append(item);continue
 if re.search(r"\b(NEGATIVE|FAILED|MISSED|NOT MET|MIXED|INCONCLUSIVE)\b",outcome):
  reasons["nonpositive_or_mixed"]+=1;review.append(item);continue
 if not re.search(r"\b(PRIMARY_MET_VERIFIED|PRIMARY ENDPOINT MET|MET PRIMARY ENDPOINT|POSITIVE VERIFIED)\b",outcome):
  reasons["issuer_outcome_requires_manual_verification"]+=1;review.append(item);continue
 accepted.append(item)
accepted.sort(key=lambda r:(r["ticker"],r["nct_id"],r["phase3_results_posted_at"]))
cols=["ticker","company","drug","indication","nct_id","phase3_results_posted_at","phase3_result","phase3_status","verification_status","phase3_results_source","source_type"]
with OUT.open("w",encoding="utf-8",newline="") as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(accepted)
summary={"generated_at":datetime.now(timezone.utc).isoformat(),"scope":"2026 issuer-announced positive Phase 3, publicly listed, no market cap limit","source_records":len(rows),"company_registry_records":len(registry),"strict_verified_issuer_positive_company_count":len({r["ticker"] for r in accepted}),"strict_verified_issuer_positive_trial_records":len(accepted),"review_records":len(review),"excluded_or_review_reasons":dict(reasons),"complete_market_census":False,"limitations":"Registry results do not establish positive efficacy or issuer announcement dates; missing issuer-release coverage and listing verification mean the verified count is a floor, not an exhaustive market census."}
STATUS.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
